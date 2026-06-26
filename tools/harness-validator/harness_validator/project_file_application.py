from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


SECRET_ASSIGNMENT_PATTERNS = (
    re.compile(
        r"(?i)[\"']?(?P<key>[a-z0-9_.-]+(?:[_-][a-z0-9_.-]+)*)[\"']?\s*[:=]\s*"
        r"[\"']?(?P<value>[^\"'\s,}]{8,})"
    ),
)


FIB_CAND_001_EXPECTED = {
    "WU-688": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0829-handoff.json",
        "kind": "contributor_slice",
        "owner": "DV",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0829",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0829",
        "handoff_evidence_id": "handoff_bs_u05_ac1_dv_to_wu_001",
    },
    "WU-689": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0830-handoff.json",
        "kind": "contributor_slice",
        "owner": "GHA",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0830",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0830",
        "handoff_evidence_id": "handoff_bs_u05_ac1_gha_to_wu_001",
    },
    "WU-690": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0832-handoff.json",
        "kind": "contributor_slice",
        "owner": "USP",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0832",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0832",
        "handoff_evidence_id": "handoff_bs_u05_ac1_usp_to_wu_001",
    },
    "WU-691": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0833-handoff.json",
        "kind": "contributor_slice",
        "owner": "DV",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0833",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0833",
        "handoff_evidence_id": "handoff_bs_u05_ac2_dv_to_wu_001",
    },
    "WU-692": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0834-handoff.json",
        "kind": "contributor_slice",
        "owner": "GHA",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0834",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0834",
        "handoff_evidence_id": "handoff_bs_u05_ac2_gha_to_wu_001",
    },
    "WU-693": {
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0836-handoff.json",
        "kind": "contributor_slice",
        "owner": "USP",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0836",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0836",
        "handoff_evidence_id": "handoff_bs_u05_ac2_usp_to_wu_001",
    },
    "WU-001": {
        "contract_file": "implementation-contract.json",
        "evidence_file": "completion-evidence.json",
        "kind": "primary_integration",
        "owner": "PFA",
    },
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


WU001_EVIDENCE_TYPES = {
    "TT-WU-007": "rollback_evidence_record",
    "TT-WU-013": "deterministic_test_result",
    "TT-WU-014": "deterministic_test_result",
    "TT-WU-029": "deterministic_test_result",
    "TT-WU-038": "deterministic_test_result",
    "TT-WU-040": "deterministic_test_result",
    "TT-WU-044": "deterministic_test_result",
    "TT-WU-048": "deterministic_test_result",
    "TT-WU-049": "deterministic_test_result",
    "TT-WU-055": "deterministic_test_result",
    "TT-WU-062": "review_or_approval_check_record",
    "TT-WU-066": "deterministic_test_result",
    "TT-WU-069": "deterministic_test_result",
    "TT-WU-072": "deterministic_test_result",
    "TT-WU-076": "deterministic_test_result",
    "TT-WU-082": "rollback_evidence_record",
    "TT-WU-083": "doctor_report",
    "TT-WU-084": "import_evidence_record",
    "TT-WU-085": "projection_snapshot",
}


ALLOWED_BATCH_PATHS = (
    "AGENTS.md",
    ".harness/artifacts/work-units/WU-001/",
    ".harness/artifacts/work-units/WU-688/",
    ".harness/artifacts/work-units/WU-689/",
    ".harness/artifacts/work-units/WU-690/",
    ".harness/artifacts/work-units/WU-691/",
    ".harness/artifacts/work-units/WU-692/",
    ".harness/artifacts/work-units/WU-693/",
    ".harness/current/checkpoints/",
    ".harness/current/git-status/",
    ".harness/current/navigation/",
    ".harness/current/source_identity/",
    ".harness/current/temp-bundles/",
    ".harness/current/status/",
    ".harness/definitions/schemas/",
    ".harness/evidence/collisions/",
    ".harness/evidence/git/",
    ".harness/evidence/release-trust/",
    ".harness/evidence/status-projection/",
    ".harness/evidence/validation/",
    ".harness/evidence/work-units/WU-001/",
    ".harness/evidence/work-units/WU-688/",
    ".harness/evidence/work-units/WU-689/",
    ".harness/evidence/work-units/WU-690/",
    ".harness/evidence/work-units/WU-691/",
    ".harness/evidence/work-units/WU-692/",
    ".harness/evidence/work-units/WU-693/",
    ".harness/manifests/",
    "tools/harness-validator/",
)


EXPECTED_WORK_UNIT_IDENTITIES = {
    "WU-688": {
        "artifact_id": "work_unit.wu-688",
        "version": "1.0.2",
        "artifact_revision_identity": "3753833d187fd38a75698b10bb419a6ff4f1c932dccbfab8a42ac0e15f53710c",
        "canonical_content_hash": "04b8ce2ecc47cbd0cc9bb9b0638c35e57581aa86906b85ebdee30e2d5e945651",
        "dependency_snapshot_hash": "0480791a749a84d672590357d4aa268062058a3c717fe53ce951bf6487ed5718",
        "acceptance_hash": "4d40669553baad8b2785b930d2d427373f825fe5d26fe3a6414e3c659c1c4df6",
        "contribution_rows_hash": "d42bee01bf3a3730a7b92c5ab446c9d90d30b5e95be53cf7d843b645bb553d04",
        "dependency_edge_rows_hash": "dea4c9825742cb3ad8fd32386306c3d0c7951d5b6d561866a28363ecc6b35465",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "e346f04d6bd5425a55ebf95e1ef2cb24377bee4bf1c70cd75566e53a985e4be7",
        "provided_interface": "owner:DV/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
    },
    "WU-689": {
        "artifact_id": "work_unit.wu-689",
        "version": "1.0.2",
        "artifact_revision_identity": "14e21148d3c3e12823c5feb0e8d736056c01c67f59c418d67086f10ecfce32ce",
        "canonical_content_hash": "1c3afca7166150ca014bdaee83156080b3b7bb9281c98eb62990052b787e6594",
        "dependency_snapshot_hash": "f47002fcd43525929150327e1c7d3fff396b4c0942cbc3a9169fbf5d3afa390e",
        "acceptance_hash": "f8daa0bb91efbe50c2c99c69cf9d82558dbdf29ca5ac5849eb3aa47d7f40daf4",
        "contribution_rows_hash": "8882a21e889888e8b5925a59042aba89a5409b7e248a21601885613cc8cd50a4",
        "dependency_edge_rows_hash": "116e8caa0ff3ee7c3da3fde48e80c4a0c08aa1bea8e8ad163671d498b99d18d4",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "16ebc13f0e44001753a75ac39dfd312e8134144f3957f50259e79dcd6cd722cf",
        "provided_interface": "owner:GHA/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
    },
    "WU-690": {
        "artifact_id": "work_unit.wu-690",
        "version": "1.0.2",
        "artifact_revision_identity": "bca9fa67fa7813f9173bab7832f876cd383b4dabef3e5f2e6eb5a70bd2651a67",
        "canonical_content_hash": "9b305b442671e186124cace05c064e9a3a02f4c0827f95613e76002913a6261c",
        "dependency_snapshot_hash": "b83e501b050b55ce0f23456a879816771d1b39da7d2eef1cf5f7cc26753c7835",
        "acceptance_hash": "3fd500ae0822e0587dace52a0f8f44e064a0fa41e3c2a72273b3005e56b41cf4",
        "contribution_rows_hash": "6dcaf06a1375fc72b4bb4989cc562999d8f34f98c59b119fd423f8f644865b2c",
        "dependency_edge_rows_hash": "e41e39a5738f7f670ebf8a90a87e732036668101c4b8eb131d0db354c5a6503b",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "44c43ae52219b3fd10f9cd6b0ceb00f2e7768e543cb50e5627e43115596770f9",
        "provided_interface": "owner:USP/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
    },
    "WU-691": {
        "artifact_id": "work_unit.wu-691",
        "version": "1.0.2",
        "artifact_revision_identity": "1e0426bdad67dfa8bef7274fe22672d9f8be78cca15824548f31fdf54893ddbe",
        "canonical_content_hash": "6ddc1a1f942b36445f7f8da25d1222c08d21a3bc26d6ea446236899183c040aa",
        "dependency_snapshot_hash": "97b1bf340885d59f5668f74da98b9a3f8d6d1bee353f57616255adf3efef633e",
        "acceptance_hash": "d3f62839a9e023e4a6d4202d9ed22b6d42272ff058a2228ef11c386cc9b612ac",
        "contribution_rows_hash": "e1422a80854d7d6847def95bb64380ac335876619e9ed442437ad8f324a72952",
        "dependency_edge_rows_hash": "022d0d890a38cde9e03e529d4d0897d48fdbb3079670437e914eb3f7000aaa17",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "07880404d14e79aa21350e3353ac0717948f9af423c30dcaeabfdb3395ad1f52",
        "provided_interface": "owner:DV/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
    },
    "WU-692": {
        "artifact_id": "work_unit.wu-692",
        "version": "1.0.2",
        "artifact_revision_identity": "1ca7ea9752ad18ba293d9e084fd938ca886390cbe5011d8facc5755860e5c2ad",
        "canonical_content_hash": "5e57dd9773cb58b2eb5a8090a8c843d5ca804b2c6d1084b9117c0a0f0d2076da",
        "dependency_snapshot_hash": "79124749d9ad45f999abeb1ad98ba89355a4a74b8f3bc45a75489f4e16f7b0a5",
        "acceptance_hash": "32b41263f5155d4fbb025f4c64a1946a32c5b0f86ac09bb26218c9bd88d43998",
        "contribution_rows_hash": "bb768c8af10aefa4b374eb58d3a7e491a8887c86686581bffdb5a5fdc75e2b1b",
        "dependency_edge_rows_hash": "29b0bb993e230f4cfcc8180fe7903f2ce7f1cb24c4c8400ebba15b7d828b8450",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "162019c26bdaa9341f993e439fd5c3f994aa22234f2f2f7d0c87eb014b7f32f8",
        "provided_interface": "owner:GHA/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
    },
    "WU-693": {
        "artifact_id": "work_unit.wu-693",
        "version": "1.0.2",
        "artifact_revision_identity": "b9cf5bf69da401a9238fe744a1e40f032e19638dbd5e3bf3a9fdda1c3c07c06f",
        "canonical_content_hash": "7d0994a7fe9293a7379c10602f65e44cac41b8ed00a1edc6d4ca574c45f54745",
        "dependency_snapshot_hash": "fc6013718a30b81afb05d7fd4c6bd7ecfc26364bfd1c339ef681cf46e7fce7ee",
        "acceptance_hash": "08b01b1aff704ea8a09f146480111aa307a038833c9a565e5c68bbceb754b6f8",
        "contribution_rows_hash": "f193cebe1ba8e2c834d094a3960e36e8254637c3c5ae45159e89c833daee0f38",
        "dependency_edge_rows_hash": "8c1b90400e7a03862f17c84c7d2dc28f0698a84758aa45eabc7e99c17b2ed55c",
        "producer_consumer_rows_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "test_target_rows_hash": "d815c407554b7728401e18ec8adf2069cee192cfaa9bb8c8397673047a5b7577",
        "provided_interface": "owner:USP/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
    },
    "WU-001": {
        "artifact_id": "work_unit.wu-001",
        "version": "1.0.2",
        "artifact_revision_identity": "747b9b020e52baf5dce7ab40d0f6c7ae73b78cfaaa4bb30111e21929cb5cad50",
        "canonical_content_hash": "c82a0cf4f815fc509bdb7fa71c10a74eb91c3846d410cad0d3579e03a130054a",
        "dependency_snapshot_hash": "cb25ce8d9c4c572e494ee68c69971841b8d512225d1407435a46a3172a7d2b31",
        "acceptance_hash": "2567d66915ff92d0ee10ea09408496eea84162b23686b3df4431a4e9686c2908",
        "contribution_rows_hash": "c25323b6acb2954c6c270fb4ab0bbcdfb1973b4a826b14ab9189bda06da38b79",
        "dependency_edge_rows_hash": "8b52c58bb01875b2b96140d2f1eb8a0b65904848b9c52b337e9b54adfce1d102",
        "producer_consumer_rows_hash": "8c83936bc17f97a9171ec18715825a65f9ebcbf35310d85e3035fabffe63ecb6",
        "test_target_rows_hash": "77b4cb2a51b68925f2655e22da4e3a55ca7ce33a086848f4d706713377e6f13f",
    },
}


for _work_unit_id, _identity in EXPECTED_WORK_UNIT_IDENTITIES.items():
    FIB_CAND_001_EXPECTED[_work_unit_id].update(_identity)


REQUIRED_GENERATED_FILES = (
    "AGENTS.md",
    ".harness/current/checkpoints/fib-cand-001-start.json",
    ".harness/current/git-status/status.json",
    ".harness/current/navigation/START_HERE.md",
    ".harness/current/source_identity/SOURCE_IDENTITY.json",
    ".harness/current/status/STATUS_KO.md",
    ".harness/definitions/schemas/handoff-contract.schema.json",
    ".harness/evidence/release-trust/FIB_CAND_001_RELEASE_TRUST_ROOT.json",
    ".harness/manifests/CURRENT_READ_SET.json",
    ".harness/manifests/FIB_CAND_001_IMPLEMENTATION_MANIFEST.json",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(value) + "\n", encoding="utf-8", newline="\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical_json(value) + "\n")


def canonical_hash_payload(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("canonical_sha256", None)
    return sha256_text(_canonical_json(payload))


def _safe_relative_path(raw_path: str) -> Path:
    if not raw_path or "\\" in raw_path or ":" in raw_path:
        raise ValueError(f"unsafe project-relative path: {raw_path}")
    candidate = PurePosixPath(raw_path)
    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        raise ValueError(f"unsafe project-relative path: {raw_path}")
    return Path(*candidate.parts)


def _safe_bundle_id(bundle_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{16}", bundle_id):
        raise ValueError(f"unsafe bundle id: {bundle_id}")
    return bundle_id


def _path_for(root: Path, raw_path: str) -> Path:
    root_resolved = root.resolve(strict=False)
    target = (root_resolved / _safe_relative_path(raw_path)).resolve(strict=False)
    if os.path.commonpath([str(root_resolved), str(target)]) != str(root_resolved):
        raise ValueError(f"unsafe project-relative path escapes root: {raw_path}")
    return target


def get_file_inventory(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        files.append({"path": rel, "size": len(data), "sha256": sha256_bytes(data)})
    return {"root": str(root), "file_count": len(files), "files": files}


def preview_file_changes(root: Path | str, changes: dict[str, str]) -> dict[str, Any]:
    root = Path(root)
    preview: dict[str, Any] = {}
    for rel_path, content in sorted(changes.items()):
        target = _path_for(root, rel_path)
        if target.exists():
            old_hash = sha256_bytes(target.read_bytes())
            operation = "modify"
        else:
            old_hash = None
            operation = "create"
        preview[rel_path] = {
            "operation": operation,
            "old_sha256": old_hash,
            "new_sha256": sha256_text(content),
        }
    return {"changes": preview, "change_count": len(preview), "file_changes_previewed": True}


def record_file_collision(root: Path | str, rel_path: str, reason: str) -> dict[str, Any]:
    root = Path(root)
    target = _path_for(root, rel_path)
    record = {
        "path": rel_path,
        "reason": reason,
        "existing_sha256": sha256_bytes(target.read_bytes()) if target.exists() else None,
    }
    append_jsonl(root / ".harness" / "evidence" / "collisions" / "collisions.jsonl", record)
    return record


def get_collision_report(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    path = root / ".harness" / "evidence" / "collisions" / "collisions.jsonl"
    if not path.exists():
        return {"collision_count": 0, "collisions": []}
    collisions = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"collision_count": len(collisions), "collisions": collisions}


def write_temp_bundle(root: Path | str, changes: dict[str, str]) -> dict[str, Any]:
    root = Path(root)
    preview = preview_file_changes(root, changes)
    bundle_id = sha256_text(_canonical_json(preview))[:16]
    bundle_dir = root / ".harness" / "current" / "temp-bundles" / bundle_id
    write_json(bundle_dir / "bundle.json", {"bundle_id": bundle_id, "changes": changes, "preview": preview})
    return {"bundle_id": bundle_id, "path": str(bundle_dir / "bundle.json"), "temp_bundle_written": True}


def atomic_reflect_bundle(root: Path | str, bundle_id: str, rollback: bool = False) -> dict[str, Any]:
    root = Path(root)
    bundle_id = _safe_bundle_id(bundle_id)
    bundle_dir = root / ".harness" / "current" / "temp-bundles" / bundle_id
    bundle_path = bundle_dir / "bundle.json"
    backup_path = bundle_dir / "backup.json"
    if rollback:
        backup = read_json(backup_path)
        for rel_path, item in backup["files"].items():
            target = _path_for(root, rel_path)
            if item["existed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(item["content"], encoding="utf-8")
            elif target.exists():
                target.unlink()
        _remove_created_parent_dirs(root, backup.get("created_parent_dirs", []))
        return {"bundle_id": bundle_id, "rolled_back": True, "partial_write_rolled_back": True}

    bundle = read_json(bundle_path)
    backup: dict[str, Any] = {"bundle_id": bundle_id, "files": {}, "created_parent_dirs": []}
    targets: list[tuple[str, Path, str]] = []
    created_parent_dirs: set[str] = set()
    for rel_path, content in sorted(bundle["changes"].items()):
        target = _path_for(root, rel_path)
        targets.append((rel_path, target, content))
        created_parent_dirs.update(_missing_parent_dirs(root, target))
        backup["files"][rel_path] = {
            "existed": target.exists(),
            "content": target.read_text(encoding="utf-8") if target.exists() else None,
        }
    backup["created_parent_dirs"] = sorted(created_parent_dirs, key=lambda item: item.count("/"), reverse=True)
    write_json(backup_path, backup)
    try:
        for _rel_path, target, content in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
    except OSError:
        for rel_path, item in backup["files"].items():
            target = _path_for(root, rel_path)
            if item["existed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(item["content"], encoding="utf-8", newline="\n")
            elif target.exists():
                target.unlink()
        _remove_created_parent_dirs(root, backup["created_parent_dirs"])
        raise
    return {"bundle_id": bundle_id, "reflected": True, "bundle_atomically_reflected": True}


def _missing_parent_dirs(root: Path, target: Path) -> list[str]:
    root_resolved = root.resolve(strict=False)
    parent = target.parent.resolve(strict=False)
    missing: list[str] = []
    while os.path.commonpath([str(root_resolved), str(parent)]) == str(root_resolved) and parent != root_resolved:
        if not parent.exists():
            missing.append(parent.relative_to(root_resolved).as_posix())
        parent = parent.parent
    return missing


def _remove_created_parent_dirs(root: Path, rel_dirs: list[str]) -> None:
    for rel_dir in sorted(rel_dirs, key=lambda item: item.count("/"), reverse=True):
        target = _path_for(root, rel_dir)
        if target.exists() and target.is_dir():
            try:
                target.rmdir()
            except OSError:
                pass


def prepare_git_checkpoint(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    if not (root / ".git").exists():
        return {"git_available": False, "prepare_git_checkpoint": "not_a_git_checkout"}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return {"git_available": False, "prepare_git_checkpoint": "git_unavailable"}
    record = {"git_available": True, "head": commit}
    write_json(root / ".harness" / "current" / "checkpoints" / "latest.json", record)
    return record


def _secret_scan(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(root).parts:
            continue
        if not _is_allowed_batch_path(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            for pattern in SECRET_ASSIGNMENT_PATTERNS:
                match = pattern.search(line)
                if match and _is_sensitive_assignment_key(match.group("key")):
                    findings.append({"path": rel, "marker": "secret_assignment"})
                    break
            else:
                continue
            break
    return findings


def _is_sensitive_assignment_key(raw_key: str) -> bool:
    key = raw_key.lower().replace("-", "_")
    if key in {"secret_findings", "batch_secret_scan_finding"} or key.endswith("_findings"):
        return False
    sensitive_terms = (
        "api_key",
        "apikey",
        "password",
        "auth_token",
        "authentication_token",
        "recovery_code",
        "client_secret",
        "secret_access_key",
        "access_key",
        "access_token",
        "github_token",
        "token",
        "secret",
    )
    return any(term in key for term in sensitive_terms)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_canonical_hash(payload: dict[str, Any]) -> bool:
    stated = payload.get("canonical_sha256")
    return isinstance(stated, str) and stated == canonical_hash_payload(payload)


def _validate_artifact_content(root: Path) -> list[str]:
    errors: list[str] = []
    consumed_handoffs: list[str] = []
    for work_unit_id, expected in FIB_CAND_001_EXPECTED.items():
        artifact_dir = root / ".harness" / "artifacts" / "work-units" / work_unit_id
        evidence_dir = root / ".harness" / "evidence" / "work-units" / work_unit_id
        contract_path = artifact_dir / expected["contract_file"]
        evidence_path = evidence_dir / expected["evidence_file"]
        test_path = evidence_dir / "test-results.jsonl"
        if not contract_path.exists() or not evidence_path.exists() or not test_path.exists():
            errors.append(f"{work_unit_id}: required artifact/evidence/test file missing")
            continue
        try:
            contract = read_json(contract_path)
            evidence = read_json(evidence_path)
            tests = _read_jsonl(test_path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{work_unit_id}: invalid JSON evidence: {exc}")
            continue

        for field in ("work_unit_id", "kind", "owner"):
            if contract.get(field) != (work_unit_id if field == "work_unit_id" else expected[field]):
                errors.append(f"{work_unit_id}: contract field {field} mismatch")
            if evidence.get(field) != (work_unit_id if field == "work_unit_id" else expected[field]):
                errors.append(f"{work_unit_id}: evidence field {field} mismatch")
        for field in ("batch_id", "artifact_id", "version"):
            expected_value = "FIB-CAND-001" if field == "batch_id" else expected[field]
            if contract.get(field) != expected_value:
                errors.append(f"{work_unit_id}: contract field {field} mismatch")
            if evidence.get(field) != expected_value:
                errors.append(f"{work_unit_id}: evidence field {field} mismatch")
        if not _validate_canonical_hash(contract):
            errors.append(f"{work_unit_id}: contract canonical_sha256 mismatch")
        if not _validate_canonical_hash(evidence):
            errors.append(f"{work_unit_id}: evidence canonical_sha256 mismatch")
        for identity_field in IDENTITY_FIELDS:
            if not re.fullmatch(r"[0-9a-f]{64}", str(contract.get(identity_field, ""))):
                errors.append(f"{work_unit_id}: contract missing identity field {identity_field}")
            if contract.get(identity_field) != expected[identity_field]:
                errors.append(f"{work_unit_id}: contract identity field {identity_field} does not match approved target")
            if evidence.get(identity_field) != contract.get(identity_field):
                errors.append(f"{work_unit_id}: evidence identity field {identity_field} mismatch")
        if not tests or any(row.get("result") != "pass" for row in tests):
            errors.append(f"{work_unit_id}: test results missing pass row")

        if expected["kind"] == "contributor_slice":
            for field in (
                "acceptance_criterion_id",
                "contribution_id",
                "required_dependency_edge_id",
                "handoff_evidence_id",
            ):
                if contract.get(field) != expected[field]:
                    errors.append(f"{work_unit_id}: contract field {field} mismatch")
                if evidence.get(field) != expected[field]:
                    errors.append(f"{work_unit_id}: evidence field {field} mismatch")
            for field in ("provided_interface", "consumed_interface"):
                if contract.get(field) != expected[field]:
                    errors.append(f"{work_unit_id}: contract field {field} mismatch")
                if evidence.get(field) != expected[field]:
                    errors.append(f"{work_unit_id}: evidence field {field} mismatch")
            if evidence.get("verification_result") != "pass":
                errors.append(f"{work_unit_id}: contributor verification did not pass")
            for row in tests:
                if row.get("evidence_type") != "handoff_contract_verification_result":
                    errors.append(f"{work_unit_id}: contributor evidence type mismatch")
                expected_result = row.get("expected_result", "")
                for term in ("provided interface", "consumed interface", "dependency edge", "hashed handoff evidence"):
                    if term not in expected_result:
                        errors.append(f"{work_unit_id}: contributor expected result omits {term}")
            consumed_handoffs.append(expected["handoff_evidence_id"])

    primary_path = root / ".harness" / "evidence" / "work-units" / "WU-001" / "completion-evidence.json"
    if primary_path.exists():
        primary = read_json(primary_path)
        actual_handoffs = sorted(primary.get("consumed_handoff_evidence", []))
        if actual_handoffs != sorted(consumed_handoffs):
            errors.append("WU-001: consumed handoff evidence set mismatch")
        if primary.get("consumed_same_work_unit_pfa_rows") != ["CONTRIB-WU-0831", "CONTRIB-WU-0835"]:
            errors.append("WU-001: same-work-unit PFA rows missing")
        if primary.get("rollback_evidence", {}).get("prior_state_restore") != "verified_by_atomic_reflect_bundle_test":
            errors.append("WU-001: rollback evidence missing")
        if primary.get("verification_result") != "pass":
            errors.append("WU-001: verification did not pass")
        test_path = root / ".harness" / "evidence" / "work-units" / "WU-001" / "test-results.jsonl"
        if test_path.exists():
            test_rows = _read_jsonl(test_path)
            actual_types = {row.get("test_target_id"): row.get("evidence_type") for row in test_rows}
            if actual_types != WU001_EVIDENCE_TYPES:
                errors.append("WU-001: test target evidence type set mismatch")
    source_identity = root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json"
    if source_identity.exists():
        source = read_json(source_identity)
        if source.get("batch_id") != "FIB-CAND-001":
            errors.append("source identity: batch_id mismatch")
        if source.get("batch_hash") != "0c455e8c55886e22322995c6466ea990e9fc3342b82b5ea5c76433527b2038a3":
            errors.append("source identity: batch_hash mismatch")
        if source.get("implementation_entry_gate") != "open_for_exact_batch_FIB-CAND-001":
            errors.append("source identity: gate mismatch")
        if source.get("ready_count") != 7 or source.get("total_work_units") != 739:
            errors.append("source identity: ready count mismatch")
        if source.get("ready_work_unit_ids") != list(FIB_CAND_001_EXPECTED.keys()):
            errors.append("source identity: ready Work Unit set mismatch")
        if source.get("bootstrap_entry_audit_blocker_count") != 0:
            errors.append("source identity: bootstrap blocker count mismatch")
    else:
        errors.append("source identity: required file missing")
    _validate_declared_artifacts(root, errors)
    return errors


def _validate_declared_artifacts(root: Path, errors: list[str]) -> None:
    for rel_path in REQUIRED_GENERATED_FILES:
        if not (root / rel_path).exists():
            errors.append(f"declared artifact missing: {rel_path}")
    read_set = root / ".harness" / "manifests" / "CURRENT_READ_SET.json"
    if read_set.exists():
        payload = read_json(read_set)
        if payload.get("batch_id") != "FIB-CAND-001" or payload.get("stage") != "implementation":
            errors.append("CURRENT_READ_SET: batch or stage mismatch")
    manifest = root / ".harness" / "manifests" / "FIB_CAND_001_IMPLEMENTATION_MANIFEST.json"
    if manifest.exists():
        payload = read_json(manifest)
        if payload.get("batch_hash") != "0c455e8c55886e22322995c6466ea990e9fc3342b82b5ea5c76433527b2038a3":
            errors.append("FIB_CAND_001_IMPLEMENTATION_MANIFEST: batch hash mismatch")
        if payload.get("work_unit_ids") != list(FIB_CAND_001_EXPECTED.keys()):
            errors.append("FIB_CAND_001_IMPLEMENTATION_MANIFEST: Work Unit set mismatch")
    trust = root / ".harness" / "evidence" / "release-trust" / "FIB_CAND_001_RELEASE_TRUST_ROOT.json"
    if trust.exists():
        payload = read_json(trust)
        if payload.get("batch_id") != "FIB-CAND-001" or payload.get("batch_hash") != "0c455e8c55886e22322995c6466ea990e9fc3342b82b5ea5c76433527b2038a3":
            errors.append("FIB_CAND_001_RELEASE_TRUST_ROOT: identity mismatch")


def _git_changed_paths(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    paths: list[str] = []
    try:
        for args in (["git", "diff", "--name-status", "-M"], ["git", "diff", "--cached", "--name-status", "-M"]):
            output = subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL)
            paths.extend(_parse_git_name_status(output))
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, stderr=subprocess.DEVNULL
        )
        paths.extend(line.replace("\\", "/").strip('"') for line in untracked.splitlines() if line.strip())
    except (OSError, subprocess.CalledProcessError):
        return []
    return sorted(set(paths))


def _parse_git_name_status(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            paths.append(parts[1].replace("\\", "/").strip('"'))
            paths.append(parts[2].replace("\\", "/").strip('"'))
        elif len(parts) >= 2:
            paths.append(parts[1].replace("\\", "/").strip('"'))
    return paths


def _out_of_scope_file_changes(root: Path) -> list[str]:
    out: list[str] = []
    for rel in _git_changed_paths(root):
        if not _is_allowed_batch_path(rel):
            out.append(rel)
    return out


def _is_allowed_batch_path(rel: str) -> bool:
    return any(rel == allowed.rstrip("/") or rel.startswith(allowed) for allowed in ALLOWED_BATCH_PATHS)


def validate_state(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    required = [
        ".harness/evidence/work-units/WU-001/completion-evidence.json",
        ".harness/evidence/work-units/WU-001/test-results.jsonl",
    ]
    required.extend(
        [
            f".harness/evidence/work-units/{work_unit_id}/test-results.jsonl"
            for work_unit_id in ["WU-688", "WU-689", "WU-690", "WU-691", "WU-692", "WU-693"]
        ]
    )
    missing = [path for path in required if not (root / path).exists()]
    secret_findings = _secret_scan(root)
    content_errors = _validate_artifact_content(root) if not missing else []
    out_of_scope_file_changes = _out_of_scope_file_changes(root)
    rollback_missing = any("rollback evidence missing" in error for error in content_errors)
    blockers = {
        "batch_unresolved_must_fix": 1 if content_errors else 0,
        "batch_creator_decision_needed": 0,
        "batch_backtrack_needed": 0,
        "batch_review_conflict": 0,
        "batch_stale_dependency_snapshot": 0,
        "batch_missing_completion_evidence": 1 if missing else 0,
        "batch_missing_test_target_evidence": 1 if any(path.endswith("test-results.jsonl") for path in missing) else 0,
        "batch_secret_scan_finding": len(secret_findings),
        "batch_out_of_scope_file_change": len(out_of_scope_file_changes),
        "batch_rollback_evidence_missing": 1 if rollback_missing else 0,
    }
    validation_passed = all(value == 0 for value in blockers.values())
    result = {
        "validation_passed": validation_passed,
        "validation_passed_event": "validation_passed" if validation_passed else "validation_failed",
        "batch_local_blockers": blockers,
        "missing": missing,
        "secret_findings": secret_findings,
        "content_errors": content_errors,
        "out_of_scope_file_changes": out_of_scope_file_changes,
    }
    write_json(root / ".harness" / "evidence" / "validation" / "latest-validation.json", result)
    return result


def get_status_summary_ko(root: Path | str) -> dict[str, Any]:
    validation = validate_state(root)
    status = "통과" if validation["validation_passed"] else "실패"
    summary = f"FIB-CAND-001 구현 검증 상태: {status}. 대상 Work Unit 7개."
    path = Path(root) / ".harness" / "current" / "status" / "STATUS_KO.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Harness 상태\n\n{summary}\n", encoding="utf-8", newline="\n")
    return {"summary_ko": summary, "status_projection_refreshed": True}
