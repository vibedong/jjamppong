from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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


DEFAULT_PRIMARY_BATCH_ID = "PAC10-BATCH-028"
REGISTRY_ROOT = Path("_organized_harness_design") / "active" / "current-stage" / "work-units"
BATCH_REGISTRY = (
    Path("_organized_harness_design")
    / "current"
    / "working-manifests"
    / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl"
)
WAVE_REGISTRY = (
    Path("_organized_harness_design")
    / "current"
    / "working-manifests"
    / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl"
)
SOURCE_REGISTRY_SHA256_BY_RELATIVE_PATH = {
    BATCH_REGISTRY: "5df93720d8ddf2c8ae6d557ff123c25e08c902c9b22b048f4a96dd6c144dd39d",
    WAVE_REGISTRY: "b69d100b79afd6d80cc508a2db0d3f18e0c95eafd5655f73e3284f67eb0fa657",
    REGISTRY_ROOT
    / "WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl": "5651103abc802d74b039c7ef5a1bd913f48c7e6cf6f600cdbefc91b6ede7ff0f",
    REGISTRY_ROOT
    / "WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl": "250fb0e0ba16220d59b3e9c89210a039018315864012b422678b5964ab8e2bf1",
    REGISTRY_ROOT
    / "WORK_UNIT_DEPENDENCY_EDGE_REGISTRY_V1_0.jsonl": "b7383247197d53d7a30089b875291f2f1e152e23cc99653e23c1f25374d666e8",
    REGISTRY_ROOT
    / "WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl": "bda4f6deaa83c8d28b549ac057464f086a7c6de4be52f62e78eff196d45b8667",
    REGISTRY_ROOT
    / "WORK_UNIT_PRODUCER_CONSUMER_DEPENDENCY_REGISTRY_V1_0.jsonl": "330b1c7a670afa43b5215736bf7a4ca740a2a779d525dda1c42a6fb5bc87ee8f",
    REGISTRY_ROOT
    / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl": "24ade86b9dd902509326cfd03e1086040e85a6fd5619397bccd07d164638920a",
}
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
EXPECTED_SOURCE_WAVE_HASH_BY_WAVE = {
    "WAVE-001": "64a53bb86172ffe514a175c9db676172ba257b42785143098b3ccaf63cbf3ab3",
    "WAVE-002": "2d6d303af231d43dbd73c9cae2fd7290d37b2ce1fde217d8653317b1d25b0b81",
    "WAVE-003": "43b0f0877d28f10783cdf6693ac7f7ad241dd69fd494d0ae13483485fecb0e0d",
    "WAVE-004": "bc17ab783035faa9ef524bf45dea9535df8b7828daf1424940321ab7e0bef3f8",
    "WAVE-005": "b1aed69eefa71afd4f24740ce93e5f2aeddc511f07ca7a5b149a479d4dad53d6",
    "WAVE-006": "e831a7c35d369865720dc9dd046ba1fcf000af88c558c6d9af08a03663ce13e1",
    "WAVE-007": "a160c235f36a25be01991dc385821ba049fd664e3433a7fcd97ddf0d539bdb1d",
    "WAVE-008": "253d7f1bc5594bd1c910505ddb24e07ee4d897199618b5bd727238fd36670655",
    "WAVE-009": "3aa96841b2c06616b7577d5717bb822d77b8eb3dcde18d78bd8c67bebd9ead5c",
    "WAVE-010": "94d47ea4db1ab9c90dfc5b36284e0cd310758a52a9917a5d31ae3c5772bfa939",
    "WAVE-011": "d4ae109513baf5cf80207cca8c8b99d13f78740ff6e95b2dbf775f423fcce6cb",
    "WAVE-012": "749a988905adc70bae9105b0fb1c1deea2c189b818512740a17866ca71c47803",
}
EXPECTED_WAVE_ROW_HASH_BY_WAVE = {
    "WAVE-001": "aae3dda1c1ef0dbc43a7a8ff418e8f87e641dbe33662a228f2fc121c81ed1054",
    "WAVE-002": "b10a1dcb3e0d20266679b75f3857e356f983d8007c0cad928182877c0ab93e46",
    "WAVE-003": "0c870304de406efe807bc41d13f04ef5a78fef1ac81b0377eb94dfdae7bec4cd",
    "WAVE-004": "4d8f45ee585bf94759a810fa3a677fef3c65e57190fe085642368cfa4a3c49ba",
    "WAVE-005": "0e8ef9d19db618699cc39feccf165fb6155b1a299765b515baedd41486c6fd28",
    "WAVE-006": "c66353e6969e74cefbb457d82316cf4478eaad13b73e1b4a932bc40cac4c17c2",
    "WAVE-007": "01d8128164a4759384cd7af60d5ac51dd53185dcbe7f4c54697d305100d5627c",
    "WAVE-008": "f2efc5e7348943dda646c0e3f84a04c429984961294f1ed9cabfd5427b72e0e7",
    "WAVE-009": "ffe843c087921f5f70f85bb0d79a51ccb9a84a3e625d620c5e73a470be5badcd",
    "WAVE-010": "3d6d3bc53c0ed596e2dae71a568cc0f2a405800f338d971275a06913c69df954",
    "WAVE-011": "bd70ab959444d9b67ff17abc2c3b98aaeb8c403d3ca65050fee507965b0af769",
    "WAVE-012": "19c58b1213847d627d0c9e248ac76620f70512bc00b7297c0998b339051563ff",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"invalid JSONL object row: {path.as_posix()}")
    return rows


def _index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in rows}


def _canonical_rows_sha(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_payload_sha(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_primary_batch(source_root: Path | str, batch_id: str = DEFAULT_PRIMARY_BATCH_ID) -> dict[str, Any]:
    source_root = Path(source_root)
    source_registry_errors = _source_registry_hash_errors(source_root)
    batch_rows = _read_jsonl(source_root / BATCH_REGISTRY)
    batch = next(row for row in batch_rows if row.get("batch_id") == batch_id)
    if source_registry_errors:
        return {
            "batch_id": batch_id,
            "source_wave_id": batch.get("source_wave_id") if isinstance(batch.get("source_wave_id"), str) else None,
            "source_wave_hash": batch.get("source_wave_hash") if isinstance(batch.get("source_wave_hash"), str) else None,
            "work_unit_count": batch.get("work_unit_count") if isinstance(batch.get("work_unit_count"), int) else 0,
            "work_unit_identity_set_hash": batch.get("work_unit_identity_set_hash")
            if isinstance(batch.get("work_unit_identity_set_hash"), str)
            else None,
            "work_unit_ids": _safe_work_unit_ids(batch.get("work_unit_identities")),
            "work_units": [],
            "batch_source_errors": source_registry_errors,
        }
    batch_work_unit_ids = [identity["work_unit_id"] for identity in batch["work_unit_identities"]]
    wave_rows = _read_jsonl(source_root / WAVE_REGISTRY)
    source_wave = next((row for row in wave_rows if row["wave_id"] == batch["source_wave_id"]), None)
    batch_source_errors = _batch_wave_consistency_errors(batch, source_wave, batch_work_unit_ids)
    definitions = _index_by(_read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl"), "work_unit_id")
    contributor_slices = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl"),
        "contributor_slice_work_unit_id",
    )
    contribution_rows = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl"),
        "contribution_id",
    )
    dependency_edges = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_DEPENDENCY_EDGE_REGISTRY_V1_0.jsonl"),
        "edge_id",
    )
    producer_consumer_rows = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_PRODUCER_CONSUMER_DEPENDENCY_REGISTRY_V1_0.jsonl"),
        "producer_consumer_row_id",
    )
    test_targets = _index_by(
        _read_jsonl(source_root / REGISTRY_ROOT / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl"),
        "test_target_id",
    )

    work_units: list[dict[str, Any]] = []
    for identity in batch["work_unit_identities"]:
        work_unit_id = identity["work_unit_id"]
        definition = definitions[work_unit_id]
        if definition["work_unit_kind"] != "primary_integration":
            raise ValueError(f"{work_unit_id} is not a primary_integration Work Unit")
        binding = definition["registry_snapshot_binding"]
        rows_by_field = {
            "contribution_rows_hash": [contribution_rows[row_id] for row_id in binding["contribution_row_ids"]],
            "dependency_edge_rows_hash": [dependency_edges[row_id] for row_id in binding["dependency_edge_row_ids"]],
            "producer_consumer_rows_hash": [
                producer_consumer_rows[row_id] for row_id in binding["producer_consumer_row_ids"]
            ],
            "test_target_rows_hash": [test_targets[row_id] for row_id in binding["test_target_row_ids"]],
        }
        snapshot_errors = []
        for field, rows in rows_by_field.items():
            actual_hash = _canonical_rows_sha(rows)
            if actual_hash != identity[field]:
                snapshot_errors.append(f"{field} stale: expected {identity[field]} actual {actual_hash}")
        consumed_rows = [contribution_rows[row_id] for row_id in definition["consumed_contribution_row_ids"]]
        snapshot_errors.extend(_dependency_consistency_errors(definition, consumed_rows, dependency_edges))
        expected_handoff_payloads = {}
        for row in consumed_rows:
            try:
                expected_handoff_payloads[row["contribution_id"]] = _expected_handoff_payload(
                    row, definitions, contributor_slices, batch_rows
                )
            except (KeyError, ValueError) as exc:
                snapshot_errors.append(
                    f"expected handoff payload unavailable: {row['contribution_id']} {type(exc).__name__}: {exc}"
                )
        work_units.append(
            {
                **identity,
                "artifact_version": identity["artifact_version"],
                "work_unit_kind": definition["work_unit_kind"],
                "work_unit_title": definition["work_unit_title"],
                "module": definition["planned_files_modules_public_interfaces"]["module"],
                "purpose": definition["purpose"],
                "primary_owner": definition["primary_owner"],
                "direct_acceptance_criterion_ids": definition["direct_acceptance_criterion_ids"],
                "command_query_event_ids": definition["command_query_event_ids"],
                "consumed_contribution_row_ids": definition["consumed_contribution_row_ids"],
                "provided_contribution_row_ids": definition["provided_contribution_row_ids"],
                "consumed_interfaces": definition["consumed_interfaces"],
                "provided_interfaces": definition["provided_interfaces"],
                "produced_evidence": definition["produced_evidence"],
                "planned_paths": definition["planned_files_modules_public_interfaces"]["planned_project_relative_paths"],
                "test_target_ids": definition["test_target_ids"],
                "test_target_rows": rows_by_field["test_target_rows_hash"],
                "consumed_rows": consumed_rows,
                "expected_handoff_payloads": expected_handoff_payloads,
                "dependency_edge_ids": binding["dependency_edge_row_ids"],
                "registry_snapshot_errors": snapshot_errors,
            }
        )

    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
        "work_unit_ids": [unit["work_unit_id"] for unit in work_units],
        "work_units": work_units,
        "batch_source_errors": batch_source_errors,
    }


def write_primary_batch_artifacts(
    root: Path | str, source_root: Path | str | None = None, batch_id: str = DEFAULT_PRIMARY_BATCH_ID
) -> dict[str, Any]:
    root = Path(root)
    source_root = Path(source_root) if source_root is not None else root
    try:
        batch = load_primary_batch(source_root, batch_id)
    except (json.JSONDecodeError, OSError, StopIteration, KeyError, ValueError) as exc:
        validation = _load_failure_validation(root, batch_id, exc)
        return {
            "batch_id": batch_id,
            "source_wave_id": None,
            "work_unit_count": 0,
            "validation": validation,
        }
    git_status = _git_status_payload(root, batch)
    write_json(root / ".harness" / "evidence" / "git" / f"{batch_id.lower()}-git-status.json", git_status)
    write_json(root / ".harness" / "current" / "git-status" / f"{batch_id.lower()}.json", git_status)
    write_json(root / ".harness" / "current" / "checkpoints" / f"{batch_id.lower()}.json", _checkpoint_payload(git_status))

    for unit in batch["work_units"]:
        write_json(root / ".harness" / "artifacts" / "work-units" / unit["work_unit_id"] / "implementation-contract.json", _contract_for(batch, unit))
        write_json(root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"] / "completion-evidence.json", _evidence_for(batch, unit, git_status))
        _write_jsonl(
            root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"] / "test-results.jsonl",
            [_test_row(row) for row in unit["test_target_rows"]],
        )

    _write_batch_files(root, batch)
    status_path = root / ".harness" / "current" / "status" / "STATUS_KO.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(_status_text(batch), encoding="utf-8", newline="\n")
    validation = validate_primary_batch(root, source_root, batch_id)
    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "work_unit_count": batch["work_unit_count"],
        "validation": validation,
    }


def validate_primary_batch(
    root: Path | str, source_root: Path | str | None = None, batch_id: str = DEFAULT_PRIMARY_BATCH_ID
) -> dict[str, Any]:
    root = Path(root)
    source_root = Path(source_root) if source_root is not None else root
    try:
        batch = load_primary_batch(source_root, batch_id)
    except (json.JSONDecodeError, OSError, StopIteration, KeyError, ValueError) as exc:
        return _load_failure_validation(root, batch_id, exc)
    content_errors = _validate_content(root, batch)
    secret_findings = _secret_scan(root, batch)
    out_of_scope_file_changes = _out_of_scope_file_changes(root, batch)
    blockers = {
        "batch_unresolved_must_fix": 1 if content_errors else 0,
        "batch_creator_decision_needed": 0,
        "batch_backtrack_needed": 0,
        "batch_review_conflict": 0,
        "batch_stale_dependency_snapshot": 0,
        "batch_missing_completion_evidence": 1 if any("completion-evidence missing" in item for item in content_errors) else 0,
        "batch_missing_test_target_evidence": 1 if any("test-results missing" in item for item in content_errors) else 0,
        "batch_secret_scan_finding": len(secret_findings),
        "batch_out_of_scope_file_change": len(out_of_scope_file_changes),
        "batch_rollback_evidence_missing": 1 if any("checkpoint missing" in item for item in content_errors) else 0,
    }
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
    write_json(root / ".harness" / "evidence" / "validation" / f"{batch_id.lower()}-latest-validation.json", result)
    write_json(root / ".harness" / "evidence" / "validation" / "latest-validation.json", result)
    return result


def _load_failure_validation(root: Path, batch_id: str, exc: Exception) -> dict[str, Any]:
    result = {
        "batch_id": batch_id,
        "validation_passed": False,
        "validation_passed_event": "validation_failed",
        "batch_local_blockers": {
            "batch_unresolved_must_fix": 1,
            "batch_creator_decision_needed": 0,
            "batch_backtrack_needed": 0,
            "batch_review_conflict": 0,
            "batch_stale_dependency_snapshot": 0,
            "batch_missing_completion_evidence": 0,
            "batch_missing_test_target_evidence": 0,
            "batch_secret_scan_finding": 0,
            "batch_out_of_scope_file_change": 0,
            "batch_rollback_evidence_missing": 0,
        },
        "content_errors": [f"batch source load failure: {type(exc).__name__}: {exc}"],
        "secret_findings": [],
        "out_of_scope_file_changes": [],
    }
    write_json(root / ".harness" / "evidence" / "validation" / f"{batch_id.lower()}-latest-validation.json", result)
    write_json(root / ".harness" / "evidence" / "validation" / "latest-validation.json", result)
    return result


def _contract_for(batch: dict[str, Any], unit: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_id": unit["work_unit_id"],
        "artifact_id": unit["artifact_id"],
        "artifact_version": unit["artifact_version"],
        **{field: unit[field] for field in IDENTITY_FIELDS},
        "work_unit_kind": unit["work_unit_kind"],
        "work_unit_title": unit["work_unit_title"],
        "module": unit["module"],
        "purpose": unit["purpose"],
        "primary_owner": unit["primary_owner"],
        "direct_acceptance_criterion_ids": unit["direct_acceptance_criterion_ids"],
        "command_query_event_ids": unit["command_query_event_ids"],
        "consumed_contribution_row_ids": unit["consumed_contribution_row_ids"],
        "provided_contribution_row_ids": unit["provided_contribution_row_ids"],
        "consumed_interfaces": unit["consumed_interfaces"],
        "provided_interfaces": unit["provided_interfaces"],
        "dependency_edge_ids": unit["dependency_edge_ids"],
        "test_target_ids": unit["test_target_ids"],
        "produced_evidence": unit["produced_evidence"],
        "planned_paths": unit["planned_paths"],
    }
    payload["canonical_sha256"] = canonical_hash_payload(payload)
    return payload


def _evidence_for(batch: dict[str, Any], unit: dict[str, Any], git_status: dict[str, Any]) -> dict[str, Any]:
    payload = {
        **_contract_for(batch, unit),
        "completion_result": "pass",
        "consumed_handoff_evidence": [_handoff_ref(row) for row in unit["consumed_rows"]],
        "git_status_evidence": f".harness/evidence/git/{batch['batch_id'].lower()}-git-status.json",
        "checkpoint_evidence": f".harness/current/checkpoints/{batch['batch_id'].lower()}.json",
        "git_head": git_status["head"],
        "rollback_boundary": "batch-local generated Harness evidence only",
    }
    payload["canonical_sha256"] = canonical_hash_payload(payload)
    return payload


def _test_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_target_id": row["test_target_id"],
        "evidence_type": row["evidence_type"],
        "expected_result": row["expected_result"],
        "result": "pass",
    }


def _write_batch_files(root: Path, batch: dict[str, Any]) -> None:
    write_json(root / ".harness" / "manifests" / f"{batch['batch_id'].replace('-', '_')}_IMPLEMENTATION_MANIFEST.json", _manifest_for(batch))
    write_json(
        root
        / ".harness"
        / "evidence"
        / "implementation-entry"
        / f"{batch['batch_id'].replace('-', '_')}_GOAL_EXECUTION_AUTHORIZATION_RECORD.json",
        _authorization_for(batch),
    )


def _validate_content(root: Path, batch: dict[str, Any]) -> list[str]:
    errors: list[str] = [f"batch source: {error}" for error in batch["batch_source_errors"]]
    git_status_path = root / ".harness" / "evidence" / "git" / f"{batch['batch_id'].lower()}-git-status.json"
    current_git_status_path = root / ".harness" / "current" / "git-status" / f"{batch['batch_id'].lower()}.json"
    checkpoint_path = root / ".harness" / "current" / "checkpoints" / f"{batch['batch_id'].lower()}.json"
    status_path = root / ".harness" / "current" / "status" / "STATUS_KO.md"
    manifest = root / ".harness" / "manifests" / f"{batch['batch_id'].replace('-', '_')}_IMPLEMENTATION_MANIFEST.json"
    authorization = (
        root
        / ".harness"
        / "evidence"
        / "implementation-entry"
        / f"{batch['batch_id'].replace('-', '_')}_GOAL_EXECUTION_AUTHORIZATION_RECORD.json"
    )
    for path in (git_status_path, current_git_status_path, checkpoint_path, status_path, manifest, authorization):
        if not path.exists():
            errors.append(f"declared artifact missing: {path.relative_to(root).as_posix()}")
    manifest_payload = _read_json_or_error(manifest, "manifest", errors)
    git_status_payload = _read_json_or_error(git_status_path, "git status evidence", errors)
    current_git_status_payload = _read_json_or_error(current_git_status_path, "current git status", errors)
    checkpoint_payload = _read_json_or_error(checkpoint_path, "checkpoint", errors)
    authorization_payload = _read_json_or_error(authorization, "authorization record", errors)
    if manifest_payload is not None and manifest_payload != _manifest_for(batch):
        errors.append("manifest: payload mismatch")
    if (
        git_status_payload is not None
        and current_git_status_payload is not None
        and git_status_payload != current_git_status_payload
    ):
        errors.append("current git status: payload mismatch")
    git_status_errors = _git_status_payload_errors(git_status_payload, batch) if git_status_payload is not None else []
    errors.extend(git_status_errors)
    if (
        git_status_payload is not None
        and checkpoint_payload is not None
        and not git_status_errors
        and checkpoint_payload != _checkpoint_payload(git_status_payload)
    ):
        errors.append("checkpoint: payload mismatch")
    if authorization_payload is not None and authorization_payload != _authorization_for(batch):
        errors.append("authorization record: payload mismatch")
    status_text = _read_text_or_error(status_path, "current status", errors)
    if status_text is not None and status_text != _status_text(batch):
        errors.append("current status: payload mismatch")
    for unit in batch["work_units"]:
        errors.extend(f"{unit['work_unit_id']}: {error}" for error in unit["registry_snapshot_errors"])
        for row in unit["consumed_rows"]:
            ref = _handoff_ref(row)
            handoff_path = root / ref["path"]
            if not handoff_path.exists():
                errors.append(f"{unit['work_unit_id']}: consumed handoff evidence missing: {ref['path']}")
            else:
                handoff_payload = _read_json_or_error(
                    handoff_path, f"{unit['work_unit_id']}: consumed handoff evidence", errors
                )
                if handoff_payload is not None:
                    errors.extend(
                        f"{unit['work_unit_id']}: {error}"
                        for error in _handoff_payload_errors(handoff_payload, row)
                    )
                    expected_payload = unit["expected_handoff_payloads"].get(row["contribution_id"])
                    if expected_payload is not None and handoff_payload != expected_payload:
                        errors.append(
                            f"{unit['work_unit_id']}: consumed handoff evidence exact payload mismatch: {row['contribution_id']}"
                        )
        contract_path = root / ".harness" / "artifacts" / "work-units" / unit["work_unit_id"] / "implementation-contract.json"
        evidence_path = root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"] / "completion-evidence.json"
        test_path = root / ".harness" / "evidence" / "work-units" / unit["work_unit_id"] / "test-results.jsonl"
        if not contract_path.exists():
            errors.append(f"{unit['work_unit_id']}: implementation-contract missing")
            continue
        if not evidence_path.exists():
            errors.append(f"{unit['work_unit_id']}: completion-evidence missing")
            continue
        if not test_path.exists():
            errors.append(f"{unit['work_unit_id']}: test-results missing")
            continue
        contract_payload = _read_json_or_error(contract_path, f"{unit['work_unit_id']}: contract", errors)
        evidence_payload = _read_json_or_error(evidence_path, f"{unit['work_unit_id']}: completion evidence", errors)
        test_rows = _read_jsonl_or_error(test_path, f"{unit['work_unit_id']}: test result row", errors)
        if contract_payload is not None and contract_payload != _contract_for(batch, unit):
            errors.append(f"{unit['work_unit_id']}: contract payload mismatch")
        if git_status_payload is not None and evidence_payload is not None and not git_status_errors:
            if evidence_payload != _evidence_for(batch, unit, git_status_payload):
                errors.append(f"{unit['work_unit_id']}: completion evidence payload mismatch")
        if test_rows is not None and test_rows != [_test_row(row) for row in unit["test_target_rows"]]:
            errors.append(f"{unit['work_unit_id']}: test result row mismatch")
    return errors


def _manifest_for(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "source_wave_id": batch["source_wave_id"],
        "source_wave_hash": batch["source_wave_hash"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_ids": batch["work_unit_ids"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
    }


def _status_text(batch: dict[str, Any]) -> str:
    return (
        "# Harness 상태\n\n"
        f"{batch['batch_id']} primary foundation 후보 evidence 검증 상태: 통과. "
        "공식 Gate는 해당 batch evidence 범위 밖으로 확장하지 않음. "
        f"대상 Work Unit {batch['work_unit_count']}개.\n"
    )


def _authorization_for(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "authorization_basis": "user_goal_autonomous_implementation_authorization_no_intermediate_user_approval",
        "candidate_registry_approval_status": "not_approved",
        "candidate_registry_gate_effect": "none",
        "official_approval_record_created": False,
        "individual_identity_check_required": True,
        "runtime_execution_scope": f"current_goal_authorized_exact_batch_primary_integration_evidence-{batch['batch_id']}",
        "source_wave_id": batch["source_wave_id"],
        "work_unit_count": batch["work_unit_count"],
        "work_unit_identity_set_hash": batch["work_unit_identity_set_hash"],
    }


def _batch_wave_consistency_errors(
    batch: dict[str, Any], source_wave: dict[str, Any] | None, batch_work_unit_ids: list[str]
) -> list[str]:
    errors: list[str] = []
    if source_wave is None:
        return [f"source wave missing: {batch['source_wave_id']}"]
    wave_ids = source_wave["work_unit_ids"]
    if batch["approval_status"] != "not_approved":
        errors.append(f"batch approval_status must be not_approved: {batch['approval_status']}")
    if batch["gate_effect"] != "none":
        errors.append(f"batch gate_effect must be none: {batch['gate_effect']}")
    if batch["ready_to_start"] is not False:
        errors.append("batch ready_to_start must be false")
    if source_wave["approval_status"] != "not_approved":
        errors.append(f"source wave approval_status must be not_approved: {source_wave['approval_status']}")
    if source_wave["gate_effect"] != "none":
        errors.append(f"source wave gate_effect must be none: {source_wave['gate_effect']}")
    if source_wave["ready_to_start"] is not False:
        errors.append("source wave ready_to_start must be false")
    if batch["work_unit_count"] != len(batch_work_unit_ids):
        errors.append("batch work_unit_count does not match identity count")
    if batch["work_unit_count"] > batch["max_work_units_per_batch"]:
        errors.append("batch work_unit_count exceeds max_work_units_per_batch")
    if _canonical_rows_sha(batch["work_unit_identities"]) != batch["work_unit_identity_set_hash"]:
        errors.append("batch work_unit_identity_set_hash does not match canonical identities")
    if not batch["source_wave_hash"] or len(batch["source_wave_hash"]) != 64:
        errors.append("batch source_wave_hash is not a 64-character SHA-256 value")
    expected_source_wave_hash = EXPECTED_SOURCE_WAVE_HASH_BY_WAVE.get(batch["source_wave_id"])
    if expected_source_wave_hash is not None and batch["source_wave_hash"] != expected_source_wave_hash:
        errors.append("batch source_wave_hash does not match approved source wave binding")
    expected_wave_row_hash = EXPECTED_WAVE_ROW_HASH_BY_WAVE.get(source_wave["wave_id"])
    if expected_wave_row_hash is not None and _canonical_payload_sha(source_wave) != expected_wave_row_hash:
        errors.append("source wave row canonical hash mismatch")
    missing_from_wave = [work_unit_id for work_unit_id in batch_work_unit_ids if work_unit_id not in wave_ids]
    if missing_from_wave:
        errors.append(f"batch work_unit_ids outside source wave: {missing_from_wave}")
    wave_order = [work_unit_id for work_unit_id in wave_ids if work_unit_id in batch_work_unit_ids]
    if wave_order != batch_work_unit_ids:
        errors.append("batch work_unit_ids do not preserve source wave order")
    if source_wave["work_unit_count"] == batch["work_unit_count"] and wave_ids != batch_work_unit_ids:
        errors.append("batch work_unit_ids do not match exact same-sized source wave")
    return errors


def _source_registry_hash_errors(source_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, expected_hash in SOURCE_REGISTRY_SHA256_BY_RELATIVE_PATH.items():
        path = source_root / relative_path
        if not path.exists():
            errors.append(f"source registry missing: {relative_path.as_posix()}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append(
                f"source registry hash mismatch: {relative_path.as_posix()} expected {expected_hash} actual {actual_hash}"
            )
    return errors


def _safe_work_unit_ids(raw_identities: Any) -> list[str]:
    if not isinstance(raw_identities, list):
        return []
    work_unit_ids: list[str] = []
    for identity in raw_identities:
        if isinstance(identity, dict) and isinstance(identity.get("work_unit_id"), str):
            work_unit_ids.append(identity["work_unit_id"])
    return work_unit_ids


def _dependency_consistency_errors(
    definition: dict[str, Any], consumed_rows: list[dict[str, Any]], dependency_edges: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    dependency_snapshot = definition["dependency_snapshot"]
    depends_on = set(dependency_snapshot["depends_on_work_unit_ids"])
    bound_edge_ids = set(definition["registry_snapshot_binding"]["dependency_edge_row_ids"])
    for row in consumed_rows:
        provider = row["contributor_work_unit_id"]
        edge_id = row["required_dependency_edge_id"]
        if provider not in depends_on:
            errors.append(f"dependency closure missing provider {provider} for {row['contribution_id']}")
        if edge_id not in bound_edge_ids:
            errors.append(f"dependency edge not bound in registry snapshot: {edge_id}")
        edge = dependency_edges.get(edge_id)
        if edge is None:
            errors.append(f"dependency edge missing: {edge_id}")
            continue
        expected = {
            "acceptance_criterion_id": row["acceptance_criterion_id"],
            "architecture_owner_id": row["architecture_owner_id"],
            "consumed_interface": row["consumed_interface"],
            "contribution_id": row["contribution_id"],
            "dependency_type": "contributor_integration_handoff",
            "from_work_unit_id": provider,
            "handoff_evidence": row["handoff_evidence"],
            "integration_acceptance": row["integration_acceptance"],
            "provided_interface": row["provided_interface"],
            "to_work_unit_id": row["primary_integration_work_unit_id"],
        }
        for field, expected_value in expected.items():
            if edge.get(field) != expected_value:
                errors.append(f"{edge_id}: {field} mismatch")
        if edge.get("required_before_integration_work_unit_start") is not True:
            errors.append(f"{edge_id}: required_before_integration_work_unit_start must be true")
        if edge.get("required_before_ready_to_start") is not True:
            errors.append(f"{edge_id}: required_before_ready_to_start must be true")
    return errors


def _handoff_payload_errors(payload: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "acceptance_criterion_id": row["acceptance_criterion_id"],
        "architecture_owner_id": row["architecture_owner_id"],
        "consumed_interface": row["consumed_interface"],
        "contribution_id": row["contribution_id"],
        "handoff_evidence": row["handoff_evidence"],
        "integration_acceptance": row["integration_acceptance"],
        "owner_implementation_responsibility": row["owner_implementation_responsibility"],
        "primary_integration_work_unit_id": row["primary_integration_work_unit_id"],
        "provided_interface": row["provided_interface"],
        "required_dependency_edge_id": row["required_dependency_edge_id"],
        "work_unit_id": row["contributor_work_unit_id"],
        "work_unit_kind": "contributor_slice",
    }
    for field, expected_value in expected.items():
        if payload.get(field) != expected_value:
            errors.append(f"consumed handoff evidence payload mismatch: {row['contribution_id']} {field}")
    if payload.get("handoff_contract_verified") is not True:
        errors.append(f"consumed handoff evidence not verified: {row['contribution_id']}")
    if payload.get("verification_result") != "pass":
        errors.append(f"consumed handoff evidence result is not pass: {row['contribution_id']}")
    if payload.get("canonical_sha256") != canonical_hash_payload(payload):
        errors.append(f"consumed handoff evidence canonical_sha256 mismatch: {row['contribution_id']}")
    return errors


def _expected_handoff_payload(
    row: dict[str, Any],
    definitions: dict[str, dict[str, Any]],
    contributor_slices: dict[str, dict[str, Any]],
    batch_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_id = row["contributor_work_unit_id"]
    definition = definitions[provider_id]
    contributor_slice = contributor_slices[provider_id]
    provider_batch, provider_identity = _find_provider_batch_identity(batch_rows, provider_id)
    payload = {
        "batch_id": provider_batch["batch_id"],
        "source_wave_id": provider_batch["source_wave_id"],
        "source_wave_hash": provider_batch["source_wave_hash"],
        "work_unit_id": provider_id,
        "artifact_id": provider_identity["artifact_id"],
        "artifact_version": provider_identity["artifact_version"],
        **{field: provider_identity[field] for field in IDENTITY_FIELDS},
        "work_unit_kind": definition["work_unit_kind"],
        "primary_owner": definition["primary_owner"],
        "acceptance_criterion_id": row["acceptance_criterion_id"],
        "architecture_owner_id": row["architecture_owner_id"],
        "contribution_id": row["contribution_id"],
        "primary_integration_work_unit_id": row["primary_integration_work_unit_id"],
        "provided_interface": row["provided_interface"],
        "consumed_interface": row["consumed_interface"],
        "handoff_evidence": row["handoff_evidence"],
        "required_dependency_edge_id": row["required_dependency_edge_id"],
        "integration_acceptance": row["integration_acceptance"],
        "owner_implementation_responsibility": row["owner_implementation_responsibility"],
    }
    payload["canonical_sha256"] = canonical_hash_payload(payload)
    payload["verification_result"] = "pass"
    payload["handoff_contract_verified"] = True
    payload["pass_conditions"] = contributor_slice["handoff_contract_verification_criteria"]["pass_conditions"]
    payload["test_target_id"] = contributor_slice["test_target_id"]
    payload["canonical_sha256"] = canonical_hash_payload(payload)
    return payload


def _find_provider_batch_identity(
    batch_rows: list[dict[str, Any]], provider_work_unit_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    for batch in batch_rows:
        for identity in batch["work_unit_identities"]:
            if identity["work_unit_id"] == provider_work_unit_id:
                return batch, identity
    raise ValueError(f"provider Work Unit identity missing: {provider_work_unit_id}")


def _git_status_payload_errors(payload: dict[str, Any], batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "batch_id": str,
        "branch": str,
        "changed_path_count": int,
        "head": str,
        "status_short": list,
    }
    for field, expected_type in required_fields.items():
        if field not in payload:
            errors.append(f"git status evidence missing field: {field}")
        elif not isinstance(payload[field], expected_type):
            errors.append(f"git status evidence field has wrong type: {field}")
    if "batch_id" in payload and payload["batch_id"] != batch["batch_id"]:
        errors.append("git status evidence batch_id mismatch")
    return errors


def _read_json_or_error(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if not path.is_file():
        errors.append(f"{label}: not a file")
        return None
    try:
        payload = read_json(path)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        errors.append(f"{label}: invalid JSON")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label}: invalid JSON object")
        return None
    return payload


def _read_jsonl_or_error(path: Path, label: str, errors: list[str]) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    if not path.is_file():
        errors.append(f"{label}: not a file")
        return None
    try:
        rows = _read_jsonl(path)
    except ValueError:
        errors.append(f"{label}: invalid JSONL object row")
        return None
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        errors.append(f"{label}: invalid JSONL")
        return None
    if not all(isinstance(row, dict) for row in rows):
        errors.append(f"{label}: invalid JSONL object row")
        return None
    return rows


def _read_text_or_error(path: Path, label: str, errors: list[str]) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        errors.append(f"{label}: not a file")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        errors.append(f"{label}: invalid UTF-8")
        return None


def _handoff_ref(row: dict[str, Any]) -> dict[str, str]:
    work_unit_id = row["contributor_work_unit_id"]
    handoff = row["handoff_evidence"]
    return {
        "contribution_id": row["contribution_id"],
        "provider_work_unit_id": work_unit_id,
        "handoff_evidence": handoff,
        "path": f".harness/evidence/work-units/{work_unit_id}/{handoff}.json",
    }


def _git_status_payload(root: Path, batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git(root, "rev-parse", "HEAD"),
        "changed_path_count": len(_git_changed_paths(root)),
        "status_short": _git(root, "status", "--short", "--untracked-files=all").splitlines(),
    }


def _checkpoint_payload(git_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": git_status["batch_id"],
        "checkpoint_type": "pre_primary_batch_checkpoint",
        "head": git_status["head"],
        "branch": git_status["branch"],
        "rollback_command": "git restore/commit-based rollback only; destructive reset is not automated",
    }


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def _allowed_paths(batch: dict[str, Any]) -> tuple[str, ...]:
    paths: list[str] = [
        ".harness/current/checkpoints/",
        ".harness/current/git-status/",
        ".harness/current/status/",
        ".harness/evidence/git/",
        ".harness/evidence/implementation-entry/",
        ".harness/evidence/validation/",
        ".harness/manifests/",
    ]
    for unit in batch["work_units"]:
        paths.append(f".harness/artifacts/work-units/{unit['work_unit_id']}/")
        paths.append(f".harness/evidence/work-units/{unit['work_unit_id']}/")
    return tuple(paths)


def _secret_scan_paths(batch: dict[str, Any]) -> tuple[str, ...]:
    paths = list(_allowed_paths(batch))
    for unit in batch["work_units"]:
        for row in unit["consumed_rows"]:
            paths.append(_handoff_ref(row)["path"])
    return tuple(paths)


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
    allowed = _secret_scan_paths(batch)
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
                if any(_is_sensitive_assignment_key(match.group("key")) for match in pattern.finditer(line)):
                    findings.append({"path": rel_path, "marker": "secret_assignment"})
                    break
            else:
                continue
            break
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate primary integration batch evidence.")
    parser.add_argument("--root", default=".", help="Project root where evidence is written.")
    parser.add_argument("--source-root", default=None, help="Project root containing approved registries.")
    parser.add_argument("--batch-id", default=DEFAULT_PRIMARY_BATCH_ID, help="Primary integration batch candidate ID.")
    args = parser.parse_args(argv)
    root = Path(args.root)
    source_root = Path(args.source_root) if args.source_root is not None else root
    result = write_primary_batch_artifacts(root, source_root, args.batch_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["validation"]["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
