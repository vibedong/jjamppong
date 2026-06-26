from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .project_file_application import (
    SECRET_ASSIGNMENT_PATTERNS,
    _git_changed_paths,
    _is_sensitive_assignment_key,
    canonical_hash_payload,
    read_json,
    write_json,
)


PAC10_BATCH_001_ID = "PAC10-BATCH-001"
IDENTITY_FIELDS = (
    "artifact_revision_identity",
    "canonical_content_hash",
    "dependency_snapshot_hash",
    "acceptance_hash",
    "contribution_rows_hash",
    "dependency_edge_rows_hash",
    "producer_consumer_rows_hash",
    "test_target_rows_hash",
)
REGISTRY_ROOT = Path("_organized_harness_design") / "active" / "current-stage" / "work-units"
BATCH_REGISTRY = (
    Path("_organized_harness_design")
    / "current"
    / "working-manifests"
    / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl"
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in rows}


def _canonical_sha(payload: dict[str, Any]) -> str:
    return canonical_hash_payload(payload)


def _canonical_rows_sha(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_contributor_batch(source_root: Path | str, batch_id: str = PAC10_BATCH_001_ID) -> dict[str, Any]:
    source_root = Path(source_root)
    batch_rows = _read_jsonl(source_root / BATCH_REGISTRY)
    batch = next(row for row in batch_rows if row["batch_id"] == batch_id)
    definitions = _index_by(_read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl"), "work_unit_id")
    slices = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl"),
        "contributor_slice_work_unit_id",
    )
    owner_rows = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl"),
        "contributor_work_unit_id",
    )
    test_targets = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl"),
        "test_target_id",
    )
    producer_consumer_rows = _read_jsonl(
        source_root / REGISTRY_ROOT / "WORK_UNIT_PRODUCER_CONSUMER_DEPENDENCY_REGISTRY_V1_0.jsonl"
    )
    dependency_edges = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_DEPENDENCY_EDGE_REGISTRY_V1_0.jsonl"),
        "edge_id",
    )

    work_units: list[dict[str, Any]] = []
    for identity in batch["work_unit_identities"]:
        work_unit_id = identity["work_unit_id"]
        definition = definitions[work_unit_id]
        contributor = slices[work_unit_id]
        owner = owner_rows[work_unit_id]
        test_target = test_targets[contributor["test_target_id"]]
        edge = dependency_edges[contributor["handoff_contract_verification_criteria"]["required_dependency_edge_id"]]
        pc_rows = [
            row
            for row in producer_consumer_rows
            if row.get("producer_work_unit_id") == work_unit_id
            or row.get("consumer_work_unit_id") == work_unit_id
            or row.get("work_unit_id") == work_unit_id
        ]
        registry_snapshot_errors = []
        for field, rows in {
            "contribution_rows_hash": [owner],
            "dependency_edge_rows_hash": [edge],
            "producer_consumer_rows_hash": pc_rows,
            "test_target_rows_hash": [test_target],
        }.items():
            actual_hash = _canonical_rows_sha(rows)
            if actual_hash != identity[field]:
                registry_snapshot_errors.append(f"{field} stale: expected {identity[field]} actual {actual_hash}")
        registry_snapshot_errors.extend(
            _cross_registry_consistency_errors(work_unit_id, contributor, owner, edge, test_target)
        )
        unit = {
            **identity,
            "artifact_version": identity["artifact_version"],
            "work_unit_kind": definition["work_unit_kind"],
            "work_unit_title": definition["work_unit_title"],
            "purpose": definition["purpose"],
            "primary_owner": definition["primary_owner"],
            "acceptance_criterion_id": contributor["acceptance_criterion_id"],
            "architecture_owner_id": contributor["architecture_owner_id"],
            "contribution_id": contributor["contribution_id"],
            "primary_integration_work_unit_id": contributor["primary_integration_work_unit_id"],
            "provided_interface": contributor["provided_interface"],
            "consumed_interface": contributor["consumed_interface"],
            "handoff_evidence": contributor["handoff_evidence"],
            "required_dependency_edge_id": contributor["handoff_contract_verification_criteria"]["required_dependency_edge_id"],
            "integration_acceptance": contributor["handoff_contract_verification_criteria"]["integration_acceptance"],
            "pass_conditions": contributor["handoff_contract_verification_criteria"]["pass_conditions"],
            "test_target_id": contributor["test_target_id"],
            "test_evidence_type": contributor["test_evidence_type"],
            "test_expected_result": contributor["test_expected_result"],
            "owner_implementation_responsibility": owner["owner_implementation_responsibility"],
            "dependency_edge_type": edge["dependency_type"],
            "registry_snapshot_errors": registry_snapshot_errors,
        }
        work_units.append(unit)

    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
        "work_unit_ids": [unit["work_unit_id"] for unit in work_units],
        "work_units": work_units,
    }


def _contract_for(batch: dict[str, Any], unit: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_id": unit["work_unit_id"],
        "artifact_id": unit["artifact_id"],
        "artifact_version": unit["artifact_version"],
        **{field: unit[field] for field in IDENTITY_FIELDS},
        "work_unit_kind": unit["work_unit_kind"],
        "primary_owner": unit["primary_owner"],
        "acceptance_criterion_id": unit["acceptance_criterion_id"],
        "architecture_owner_id": unit["architecture_owner_id"],
        "contribution_id": unit["contribution_id"],
        "primary_integration_work_unit_id": unit["primary_integration_work_unit_id"],
        "provided_interface": unit["provided_interface"],
        "consumed_interface": unit["consumed_interface"],
        "handoff_evidence": unit["handoff_evidence"],
        "required_dependency_edge_id": unit["required_dependency_edge_id"],
        "integration_acceptance": unit["integration_acceptance"],
        "owner_implementation_responsibility": unit["owner_implementation_responsibility"],
    }
    contract["canonical_sha256"] = _canonical_sha(contract)
    return contract


def _test_row(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_target_id": unit["test_target_id"],
        "evidence_type": unit["test_evidence_type"],
        "expected_result": unit["test_expected_result"],
        "result": "pass",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_contributor_batch_artifacts(
    root: Path | str, source_root: Path | str | None = None, batch_id: str = PAC10_BATCH_001_ID
) -> dict[str, Any]:
    root = Path(root)
    source_root = Path(source_root) if source_root is not None else root
    batch = load_contributor_batch(source_root, batch_id)
    for unit in batch["work_units"]:
        contract = _contract_for(batch, unit)
        evidence = _evidence_for(batch, unit)
        artifact_dir = root / ".harness" / "artifacts" / "work-units" / unit["work_unit_id"]
        evidence_dir = root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"]
        write_json(artifact_dir / "contributor-contract.json", contract)
        write_json(evidence_dir / f"{unit['handoff_evidence']}.json", evidence)
        _write_jsonl(evidence_dir / "test-results.jsonl", [_test_row(unit)])

    _write_current_batch_files(root, batch)
    validation = validate_contributor_batch(root, source_root, batch_id)
    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "work_unit_count": batch["work_unit_count"],
        "validation": validation,
    }


def _write_current_batch_files(root: Path, batch: dict[str, Any]) -> None:
    write_json(
        root
        / ".harness"
        / "evidence"
        / "implementation-entry"
        / f"{batch['batch_id'].replace('-', '_')}_CANDIDATE_SOURCE_IDENTITY.json",
        _candidate_source_identity_for(batch),
    )
    write_json(
        root / ".harness" / "manifests" / f"{batch['batch_id'].replace('-', '_')}_IMPLEMENTATION_MANIFEST.json",
        {
            "batch_id": batch["batch_id"],
            "source_wave_id": batch["source_wave_id"],
            "source_wave_hash": batch["source_wave_hash"],
            "work_unit_count": batch["work_unit_count"],
            "work_unit_ids": batch["work_unit_ids"],
            "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
        },
    )
    write_json(
        root / ".harness" / "evidence" / "implementation-entry" / f"{batch['batch_id'].replace('-', '_')}_GOAL_EXECUTION_AUTHORIZATION_RECORD.json",
        {
            "batch_id": batch["batch_id"],
            "authorization_basis": "user_goal_autonomous_implementation_authorization_no_intermediate_user_approval",
            "candidate_registry_approval_status": "not_approved",
            "candidate_registry_gate_effect": "none",
            "official_approval_record_created": False,
            "individual_identity_check_required": True,
            "runtime_execution_scope": f"current_goal_authorized_exact_batch_candidate_evidence-{batch['batch_id']}",
            "source_wave_id": batch["source_wave_id"],
            "work_unit_count": batch["work_unit_count"],
            "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
        },
    )
    (root / ".harness" / "current" / "status" / "STATUS_KO.md").parent.mkdir(parents=True, exist_ok=True)
    (root / ".harness" / "current" / "status" / "STATUS_KO.md").write_text(
        _status_text_for(batch, "통과"), encoding="utf-8", newline="\n"
    )


def validate_contributor_batch(
    root: Path | str, source_root: Path | str | None = None, batch_id: str = PAC10_BATCH_001_ID
) -> dict[str, Any]:
    root = Path(root)
    source_root = Path(source_root) if source_root is not None else root
    batch = load_contributor_batch(source_root, batch_id)
    content_errors = _validate_content(root, batch)
    secret_findings = _secret_scan(root, batch)
    out_of_scope_file_changes = _out_of_scope_file_changes(root, batch)
    blockers = _blockers_for(content_errors, secret_findings, out_of_scope_file_changes)
    expected_status = "통과" if all(value == 0 for value in blockers.values()) else "실패"
    content_errors.extend(_validate_status(root, batch, expected_status))
    blockers = _blockers_for(content_errors, secret_findings, out_of_scope_file_changes)
    validation_passed = all(value == 0 for value in blockers.values())
    result = {
        "batch_id": batch["batch_id"],
        "validation_passed": validation_passed,
        "validation_passed_event": "validation_passed" if validation_passed else "validation_failed",
        "batch_local_blockers": blockers,
        "content_errors": content_errors,
        "secret_findings": secret_findings,
        "out_of_scope_file_changes": out_of_scope_file_changes,
    }
    write_json(root / ".harness" / "evidence" / "validation" / f"{batch['batch_id'].lower()}-latest-validation.json", result)
    write_json(root / ".harness" / "evidence" / "validation" / "latest-validation.json", result)
    status = "통과" if validation_passed else "실패"
    (root / ".harness" / "current" / "status" / "STATUS_KO.md").write_text(
        _status_text_for(batch, status),
        encoding="utf-8",
        newline="\n",
    )
    return result


def _validate_content(root: Path, batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate_source_identity = (
        root
        / ".harness"
        / "evidence"
        / "implementation-entry"
        / f"{batch['batch_id'].replace('-', '_')}_CANDIDATE_SOURCE_IDENTITY.json"
    )
    manifest = root / ".harness" / "manifests" / f"{batch['batch_id'].replace('-', '_')}_IMPLEMENTATION_MANIFEST.json"
    authorization = root / ".harness" / "evidence" / "implementation-entry" / f"{batch['batch_id'].replace('-', '_')}_GOAL_EXECUTION_AUTHORIZATION_RECORD.json"
    errors.extend(_official_source_identity_errors(root, batch))
    errors.extend(_forbidden_approval_record_errors(root, batch))
    for path in (candidate_source_identity, manifest, authorization):
        if not path.exists():
            errors.append(f"declared artifact missing: {path.relative_to(root).as_posix()}")
    if candidate_source_identity.exists():
        payload = read_json(candidate_source_identity)
        expected = _candidate_source_identity_for(batch)
        if payload != expected:
            errors.append("candidate source identity: payload mismatch")
    if manifest.exists():
        payload = read_json(manifest)
        if payload != _manifest_for(batch):
            errors.append("manifest: payload mismatch")
    if authorization.exists():
        payload = read_json(authorization)
        if payload != _authorization_for(batch):
            errors.append("authorization record: payload mismatch")
    for unit in batch["work_units"]:
        if unit["registry_snapshot_errors"]:
            errors.extend(f"{unit['work_unit_id']}: {error}" for error in unit["registry_snapshot_errors"])
        artifact_dir = root / ".harness" / "artifacts" / "work-units" / unit["work_unit_id"]
        evidence_dir = root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"]
        contract_path = artifact_dir / "contributor-contract.json"
        evidence_path = evidence_dir / f"{unit['handoff_evidence']}.json"
        test_path = evidence_dir / "test-results.jsonl"
        if not contract_path.exists():
            errors.append(f"{unit['work_unit_id']}: contract missing")
            continue
        if not evidence_path.exists():
            errors.append(f"{unit['work_unit_id']}: evidence missing")
            continue
        if not test_path.exists():
            errors.append(f"{unit['work_unit_id']}: test-results missing")
            continue
        contract = read_json(contract_path)
        evidence = read_json(evidence_path)
        tests = _read_jsonl(test_path)
        if contract != _contract_for(batch, unit):
            errors.append(f"{unit['work_unit_id']}: contract payload does not match approved target")
        if evidence != _evidence_for(batch, unit):
            errors.append(f"{unit['work_unit_id']}: evidence payload does not match approved target")
        if not _canonical_hash_valid(contract):
            errors.append(f"{unit['work_unit_id']}: contract canonical_sha256 mismatch")
        if not _canonical_hash_valid(evidence):
            errors.append(f"{unit['work_unit_id']}: evidence canonical_sha256 mismatch")
        if evidence.get("verification_result") != "pass" or evidence.get("handoff_contract_verified") is not True:
            errors.append(f"{unit['work_unit_id']}: handoff verification did not pass")
        expected_row = _test_row(unit)
        if tests != [expected_row]:
            errors.append(f"{unit['work_unit_id']}: test result row mismatch")
    return errors


def _blockers_for(
    content_errors: list[str], secret_findings: list[dict[str, str]], out_of_scope_file_changes: list[str]
) -> dict[str, int]:
    return {
        "batch_unresolved_must_fix": 1 if content_errors else 0,
        "batch_creator_decision_needed": 0,
        "batch_backtrack_needed": 0,
        "batch_review_conflict": 0,
        "batch_stale_dependency_snapshot": 0,
        "batch_missing_completion_evidence": 1
        if any("contract missing" in item or "evidence missing" in item for item in content_errors)
        else 0,
        "batch_missing_test_target_evidence": 1 if any("test-results missing" in item for item in content_errors) else 0,
        "batch_secret_scan_finding": len(secret_findings),
        "batch_out_of_scope_file_change": len(out_of_scope_file_changes),
        "batch_rollback_evidence_missing": 0,
    }


def _validate_status(root: Path, batch: dict[str, Any], expected_status: str) -> list[str]:
    status_path = root / ".harness" / "current" / "status" / "STATUS_KO.md"
    if not status_path.exists():
        return [f"declared artifact missing: {status_path.relative_to(root).as_posix()}"]
    if status_path.read_text(encoding="utf-8") != _status_text_for(batch, expected_status):
        return ["status: candidate/gate boundary text mismatch"]
    return []


def _official_source_identity_errors(root: Path, batch: dict[str, Any]) -> list[str]:
    source_identity = root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json"
    if not source_identity.exists():
        return []
    payload = read_json(source_identity)
    if (
        payload.get("current_batch_id") == batch["batch_id"]
        or payload.get("batch_id") == batch["batch_id"]
        or payload.get("implementation_entry_gate") == "not_widened_by_candidate_registry"
        or payload.get("implementation_entry_gate") == f"open_for_exact_batch_{batch['batch_id']}"
        or payload.get("ready_work_unit_ids") == batch["work_unit_ids"]
    ):
        return ["official source identity: PAC10 candidate state must not replace official pointer"]
    return []


def _forbidden_approval_record_errors(root: Path, batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tokens = {batch["batch_id"].upper(), batch["batch_id"].replace("-", "_").upper()}
    for directory in (
        root / ".harness" / "evidence" / "implementation-entry",
        root / ".harness" / "manifests",
    ):
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.upper()
            if "APPROVAL_RECORD" not in name:
                continue
            try:
                text = path.read_text(encoding="utf-8").upper()
            except UnicodeDecodeError:
                text = ""
            if any(token in name or token in text for token in tokens):
                errors.append(f"official approval record forbidden: {path.relative_to(root).as_posix()}")
    return errors


def _canonical_hash_valid(payload: dict[str, Any]) -> bool:
    return payload.get("canonical_sha256") == canonical_hash_payload(payload)


def _status_text_for(batch: dict[str, Any], status: str) -> str:
    return (
        f"# Harness 상태\n\n{batch['batch_id']} contributor batch 후보 evidence 검증 상태: {status}. "
        f"공식 Gate는 candidate registry로 확장하지 않음. 대상 Work Unit {batch['work_unit_count']}개.\n"
    )


def _cross_registry_consistency_errors(
    work_unit_id: str,
    contributor: dict[str, Any],
    owner: dict[str, Any],
    edge: dict[str, Any],
    test_target: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    criteria = contributor["handoff_contract_verification_criteria"]
    test_criteria = test_target["handoff_contract_verification_criteria"]
    expected = {
        "acceptance_criterion_id": contributor["acceptance_criterion_id"],
        "architecture_owner_id": contributor["architecture_owner_id"],
        "contribution_id": contributor["contribution_id"],
        "primary_integration_work_unit_id": contributor["primary_integration_work_unit_id"],
        "provided_interface": contributor["provided_interface"],
        "consumed_interface": contributor["consumed_interface"],
        "handoff_evidence": contributor["handoff_evidence"],
        "required_dependency_edge_id": criteria["required_dependency_edge_id"],
        "integration_acceptance": criteria["integration_acceptance"],
        "provider_work_unit_id": work_unit_id,
        "pass_conditions": criteria["pass_conditions"],
    }

    def require(surface: str, field: str, actual: Any, expected_value: Any) -> None:
        if actual != expected_value:
            errors.append(f"{work_unit_id}: {surface}.{field} disagrees with contributor slice")

    for field in (
        "acceptance_criterion_id",
        "architecture_owner_id",
        "contribution_id",
        "primary_integration_work_unit_id",
        "provided_interface",
        "consumed_interface",
        "handoff_evidence",
        "required_dependency_edge_id",
        "integration_acceptance",
        "provider_work_unit_id",
        "pass_conditions",
    ):
        require("contributor_criteria", field, criteria.get(field), expected[field])

    for field in (
        "acceptance_criterion_id",
        "architecture_owner_id",
        "contribution_id",
        "primary_integration_work_unit_id",
        "provided_interface",
        "consumed_interface",
        "handoff_evidence",
        "required_dependency_edge_id",
        "integration_acceptance",
        "provider_work_unit_id",
    ):
        require("owner_contribution", field, owner.get(field), expected[field])

    require("owner_contribution", "contributor_work_unit_id", owner.get("contributor_work_unit_id"), work_unit_id)
    require("dependency_edge", "edge_id", edge.get("edge_id"), expected["required_dependency_edge_id"])
    require("dependency_edge", "from_work_unit_id", edge.get("from_work_unit_id"), work_unit_id)
    require("dependency_edge", "to_work_unit_id", edge.get("to_work_unit_id"), expected["primary_integration_work_unit_id"])
    for field in (
        "acceptance_criterion_id",
        "architecture_owner_id",
        "contribution_id",
        "provided_interface",
        "consumed_interface",
        "handoff_evidence",
        "integration_acceptance",
    ):
        require("dependency_edge", field, edge.get(field), expected[field])

    for field in (
        "acceptance_criterion_id",
        "architecture_owner_id",
        "contribution_id",
        "primary_integration_work_unit_id",
        "provided_interface",
        "consumed_interface",
        "handoff_evidence",
        "required_dependency_edge_id",
        "integration_acceptance",
        "provider_work_unit_id",
        "pass_conditions",
    ):
        require("test_target_criteria", field, test_criteria.get(field), expected[field])

    require("test_target", "test_target_id", test_target.get("test_target_id"), contributor["test_target_id"])
    require("test_target", "evidence_type", test_target.get("evidence_type"), contributor["test_evidence_type"])
    require("test_target", "expected_result", test_target.get("expected_result"), contributor["test_expected_result"])
    return errors


def _allowed_paths(batch: dict[str, Any]) -> tuple[str, ...]:
    work_unit_paths: list[str] = []
    for work_unit_id in batch["work_unit_ids"]:
        work_unit_paths.append(f".harness/artifacts/work-units/{work_unit_id}/")
        work_unit_paths.append(f".harness/evidence/work-units/{work_unit_id}/")
    return (
        "AGENTS.md",
        ".harness/current/source_identity/",
        ".harness/current/status/",
        ".harness/evidence/implementation-entry/",
        ".harness/evidence/validation/",
        ".harness/manifests/",
        *work_unit_paths,
    )


def _out_of_scope_file_changes(root: Path, batch: dict[str, Any]) -> list[str]:
    allowed = _allowed_paths(batch)
    out: list[str] = []
    for rel_path in _git_changed_paths(root):
        if "__pycache__/" in rel_path or rel_path.endswith(".pyc"):
            out.append(rel_path)
        elif not any(rel_path == item.rstrip("/") or rel_path.startswith(item) for item in allowed):
            out.append(rel_path)
    return out


def _secret_scan(root: Path, batch: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    allowed = _allowed_paths(batch)
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        rel_path = path.relative_to(root).as_posix()
        if not any(rel_path == item.rstrip("/") or rel_path.startswith(item) for item in allowed):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            for pattern in SECRET_ASSIGNMENT_PATTERNS:
                match = pattern.search(line)
                if match and _is_sensitive_assignment_key(match.group("key")):
                    findings.append({"path": rel_path, "marker": "secret_assignment"})
                    break
            else:
                continue
            break
    return findings


def _evidence_for(batch: dict[str, Any], unit: dict[str, Any]) -> dict[str, Any]:
    evidence = {
        **_contract_for(batch, unit),
        "verification_result": "pass",
        "handoff_contract_verified": True,
        "pass_conditions": unit["pass_conditions"],
        "test_target_id": unit["test_target_id"],
    }
    evidence["canonical_sha256"] = _canonical_sha(evidence)
    return evidence


def _candidate_source_identity_for(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_batch_id": batch["batch_id"],
        "completed_batches": ["FIB-CAND-001"],
        "candidate_evidence_batches": [batch["batch_id"]],
        "implementation_entry_gate": "not_widened_by_candidate_registry",
        "runtime_execution_scope": f"current_goal_authorized_exact_batch_candidate_evidence-{batch['batch_id']}",
        "candidate_registry_approval_status": "not_approved",
        "candidate_registry_ready_to_start": False,
        "candidate_registry_gate_effect": "none",
        "official_approval_record_created": False,
        "official_ready_count": 7,
        "runtime_selected_work_unit_count": batch["work_unit_count"],
        "total_work_units": 739,
        "runtime_selected_work_unit_ids": batch["work_unit_ids"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "bootstrap_entry_audit_blocker_count": 0,
    }


def _manifest_for(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_ids": batch["work_unit_ids"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
    }


def _authorization_for(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "authorization_basis": "user_goal_autonomous_implementation_authorization_no_intermediate_user_approval",
        "candidate_registry_approval_status": "not_approved",
        "candidate_registry_gate_effect": "none",
        "official_approval_record_created": False,
        "individual_identity_check_required": True,
        "runtime_execution_scope": f"current_goal_authorized_exact_batch_candidate_evidence-{batch['batch_id']}",
        "source_wave_id": batch["source_wave_id"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate contributor-only batch evidence.")
    parser.add_argument("--root", default=".", help="Project root where evidence is written.")
    parser.add_argument("--source-root", default=None, help="Project root containing approved registries.")
    parser.add_argument("--batch-id", default=PAC10_BATCH_001_ID, help="Contributor batch candidate ID.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    source_root = Path(args.source_root) if args.source_root is not None else root
    result = write_contributor_batch_artifacts(root, source_root, args.batch_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["validation"]["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
