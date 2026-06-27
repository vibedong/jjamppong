import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .jsonio import dumps_canonical_json, load_json, write_canonical_json


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe(value):
    return str(value).replace("/", "_").replace("\\", "_")


def write_jsonl(path, rows):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(dumps_canonical_json(row) for row in rows), encoding="utf-8", newline="\n")


def file_hash(path):
    target = Path(path)
    if not target.is_file():
        return None
    return hashlib.sha256(target.read_bytes()).hexdigest()


def read_registry(root):
    path = Path(root) / ".harness/current/work-units/WORK_UNITS_REGISTRY.jsonl"
    if not path.is_file():
        return {}
    rows = [load_json_line for load_json_line in (line.strip() for line in path.read_text(encoding="utf-8").splitlines()) if load_json_line]
    import json
    return {row["work_unit_id"]: row for row in (json.loads(line) for line in rows)}


def write_work_unit_registry(root, rows):
    path = Path(root) / ".harness/current/work-units/WORK_UNITS_REGISTRY.jsonl"
    write_jsonl(path, rows)
    return path


def work_unit_identity_hash(work_unit):
    payload = {
        "work_unit_id": work_unit["work_unit_id"],
        "artifact_id": work_unit["artifact_id"],
        "version": work_unit["version"],
        "artifact_revision_identity": work_unit["artifact_revision_identity"],
        "canonical_content_hash": work_unit["canonical_content_hash"],
        "dependency_snapshot_hash": work_unit["dependency_snapshot_hash"],
        "acceptance_hash": work_unit["acceptance_hash"],
        "registry_snapshot_hashes": work_unit.get("registry_snapshot_hashes", {}),
    }
    return hashlib.sha256(dumps_canonical_json(payload).encode("utf-8")).hexdigest()


def write_work_unit_approval(root, work_unit, approved_by):
    path = Path(root) / ".harness/approvals/work-units" / f"WORK_UNIT_APPROVAL_{safe(work_unit['work_unit_id'])}.json"
    payload = {
        "schema_version": "1.0",
        "approval_record_id": f"WU-APPROVAL-{safe(work_unit['work_unit_id'])}",
        "approval_type": "work_unit",
        "work_unit_id": work_unit["work_unit_id"],
        "artifact_id": work_unit["artifact_id"],
        "version": work_unit["version"],
        "artifact_revision_identity": work_unit["artifact_revision_identity"],
        "canonical_content_hash": work_unit["canonical_content_hash"],
        "dependency_snapshot_hash": work_unit["dependency_snapshot_hash"],
        "acceptance_hash": work_unit["acceptance_hash"],
        "registry_snapshot_hashes": work_unit.get("registry_snapshot_hashes", {}),
        "approval_target_hash": work_unit_identity_hash(work_unit),
        "approval_status": "approved",
        "approved_by": approved_by,
        "approved_at_utc": utc_now(),
        "approval_statement_hash": hashlib.sha256(dumps_canonical_json(work_unit).encode("utf-8")).hexdigest(),
        "revocation_reason": None,
        "supersedes_approval_record_id": None,
    }
    write_canonical_json(path, payload)
    return path


def write_batch_manifest(root, batch_id, work_unit_ids, work_unit_identity_hashes):
    path = Path(root) / ".harness/current/batches" / f"BATCH_MANIFEST_{safe(batch_id)}.json"
    payload = {
        "schema_version": "1.0",
        "batch_id": batch_id,
        "work_unit_ids": work_unit_ids,
        "dependency_closure_order": work_unit_ids,
        "parallelism_limit": 1,
        "risk_level": "low",
        "work_unit_identity_hashes": work_unit_identity_hashes,
        "dependency_closure_hash": hashlib.sha256(dumps_canonical_json(work_unit_ids).encode("utf-8")).hexdigest(),
        "batch_hash": hashlib.sha256(dumps_canonical_json({"batch_id": batch_id, "work_unit_ids": work_unit_ids, "work_unit_identity_hashes": work_unit_identity_hashes}).encode("utf-8")).hexdigest(),
        "approval_status": "candidate",
        "stale_status": "fresh",
        "ready_to_start": False,
        "created_at_utc": utc_now(),
    }
    write_canonical_json(path, payload)
    return payload


def write_batch_approval(root, batch, approved_by):
    path = Path(root) / ".harness/approvals/batches" / f"BATCH_APPROVAL_{safe(batch['batch_id'])}.json"
    payload = {
        "schema_version": "1.0",
        "approval_record_id": f"BATCH-APPROVAL-{safe(batch['batch_id'])}",
        "approval_type": "batch",
        "batch_id": batch["batch_id"],
        "batch_hash": batch["batch_hash"],
        "work_unit_ids": batch["work_unit_ids"],
        "work_unit_identity_hashes": batch["work_unit_identity_hashes"],
        "dependency_closure_hash": batch["dependency_closure_hash"],
        "bootstrap_prerequisite_status": "pass",
        "approval_status": "approved",
        "approved_by": approved_by,
        "approved_at_utc": utc_now(),
        "approval_statement_hash": hashlib.sha256(dumps_canonical_json(batch).encode("utf-8")).hexdigest(),
        "revocation_reason": None,
        "supersedes_approval_record_id": None,
    }
    write_canonical_json(path, payload)
    return path


def gate_open_eligible(root, batch_id):
    root = Path(root)
    blockers = []
    batch_path = root / ".harness/current/batches" / f"BATCH_MANIFEST_{safe(batch_id)}.json"
    approval_path = root / ".harness/approvals/batches" / f"BATCH_APPROVAL_{safe(batch_id)}.json"
    if not batch_path.is_file():
        return {"eligible": False, "blockers": ["bootstrap.missing_batch_manifest"]}
    if not approval_path.is_file():
        return {"eligible": False, "blockers": ["bootstrap.batch_not_approved"]}
    batch = load_json(batch_path)
    batch_approval = load_json(approval_path)
    if batch_approval.get("approval_status") != "approved":
        blockers.append("bootstrap.batch_not_approved")
    if batch_approval.get("batch_hash") != batch.get("batch_hash"):
        blockers.append("bootstrap.batch_identity_hash_mismatch")
    if batch_approval.get("work_unit_identity_hashes") != batch.get("work_unit_identity_hashes"):
        blockers.append("bootstrap.batch_identity_hash_mismatch")
    registry = read_registry(root)
    for work_unit_id in batch["work_unit_ids"]:
        row = registry.get(work_unit_id)
        if row is None:
            blockers.append("bootstrap.missing_work_unit_registry_row")
            continue
        if row.get("approval_status") == "stale" or row.get("stale_status") not in (None, "", "fresh"):
            blockers.append("bootstrap.work_unit_stale")
        if not row.get("canonical_content_hash") or not row.get("dependency_snapshot_hash") or not row.get("acceptance_hash"):
            blockers.append("bootstrap.work_unit_identity_incomplete")
        approval = root / ".harness/approvals/work-units" / f"WORK_UNIT_APPROVAL_{safe(work_unit_id)}.json"
        if not approval.is_file():
            blockers.append("bootstrap.work_unit_not_approved")
        else:
            approval_payload = load_json(approval)
            if approval_payload.get("approval_status") != "approved":
                blockers.append("bootstrap.work_unit_not_approved")
            for key in ("artifact_revision_identity", "canonical_content_hash", "dependency_snapshot_hash", "acceptance_hash"):
                if approval_payload.get(key) != row.get(key):
                    blockers.append("bootstrap.work_unit_identity_mismatch")
            current_identity_hash = work_unit_identity_hash(row)
            if approval_payload.get("approval_target_hash") != current_identity_hash:
                blockers.append("bootstrap.work_unit_identity_mismatch")
            expected_hash = batch.get("work_unit_identity_hashes", {}).get(work_unit_id)
            if expected_hash and approval_payload.get("approval_target_hash") != expected_hash:
                blockers.append("bootstrap.batch_identity_hash_mismatch")
    return {"eligible": not blockers, "blockers": sorted(set(blockers))}


def write_gate_state(root, gate_status, open_batch_id, open_work_unit_ids, blockers):
    path = Path(root) / ".harness/current/gate/GATE_STATE.json"
    payload = {
        "schema_version": "1.0",
        "gate_status": gate_status,
        "open_batch_id": open_batch_id,
        "open_work_unit_ids": open_work_unit_ids,
        "opened_at_utc": utc_now() if gate_status == "open_for_exact_batch" else None,
        "closed_at_utc": utc_now() if gate_status.startswith("closed") else None,
        "last_event_id": None,
        "blockers": blockers,
        "ready_to_start_counts": {"ready": len(open_work_unit_ids) if gate_status == "open_for_exact_batch" else 0, "total": len(read_registry(root))},
        "created_at_utc": utc_now(),
    }
    write_canonical_json(path, payload)
    return path


def append_gate_event(root, event_type, from_gate_status, to_gate_status, batch_id, work_unit_ids, actor, evidence_paths, reason=None):
    root = Path(root)
    path = root / ".harness/current/gate/GATE_EVENTS.jsonl"
    before = file_hash(root / ".harness/current/gate/GATE_STATE.json")
    event = {
        "schema_version": "1.0",
        "event_id": f"GATE-EVENT-{uuid4().hex[:12]}",
        "event_type": event_type,
        "event_at_utc": utc_now(),
        "from_gate_status": from_gate_status,
        "to_gate_status": to_gate_status,
        "batch_id": batch_id,
        "work_unit_ids": work_unit_ids,
        "actor": actor,
        "reason": reason,
        "state_hash_before": before,
        "state_hash_after": before,
        "evidence_paths": evidence_paths,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(dumps_canonical_json(event))
    return event


def write_implementation_source_manifest(root, batch_id, work_unit_ids, base_commit, head_commit, changed_files, test_evidence_paths, review_evidence_paths, out_of_scope_files):
    path = Path(root) / ".harness/current/implementation/IMPLEMENTATION_SOURCE_MANIFEST.json"
    payload = {
        "schema_version": "1.0",
        "batch_id": batch_id,
        "work_unit_ids": work_unit_ids,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "changed_files": changed_files,
        "created_files": changed_files,
        "modified_files": [],
        "deleted_files": [],
        "test_evidence_paths": test_evidence_paths,
        "review_evidence_paths": review_evidence_paths,
        "out_of_scope_files": out_of_scope_files,
        "source_manifest_hash": None,
        "created_at_utc": utc_now(),
    }
    payload["source_manifest_hash"] = hashlib.sha256(dumps_canonical_json({k: v for k, v in payload.items() if k != "source_manifest_hash"}).encode("utf-8")).hexdigest()
    write_canonical_json(path, payload)
    return path


def mark_work_unit_stale(work_unit, stale_status):
    row = dict(work_unit)
    row["approval_status"] = "stale"
    row["stale_status"] = stale_status
    row["ready_to_start"] = False
    return row
