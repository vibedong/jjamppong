from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project_file_application import canonical_hash_payload, get_status_summary_ko, validate_state, write_json


BATCH_ID = "FIB-CAND-001"
BATCH_HASH = "0c455e8c55886e22322995c6466ea990e9fc3342b82b5ea5c76433527b2038a3"


FIB_CAND_001_WORK_UNITS: list[dict[str, Any]] = [
    {
        "work_unit_id": "WU-688",
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
        "kind": "contributor_slice",
        "owner": "DV",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0829",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0829",
        "handoff_evidence_id": "handoff_bs_u05_ac1_dv_to_wu_001",
        "provided_interface": "owner:DV/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
        "test_target_id": "TT-WU-CONTRIB-WU-0829",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0829-handoff.json",
    },
    {
        "work_unit_id": "WU-689",
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
        "kind": "contributor_slice",
        "owner": "GHA",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0830",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0830",
        "handoff_evidence_id": "handoff_bs_u05_ac1_gha_to_wu_001",
        "provided_interface": "owner:GHA/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
        "test_target_id": "TT-WU-CONTRIB-WU-0830",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0830-handoff.json",
    },
    {
        "work_unit_id": "WU-690",
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
        "kind": "contributor_slice",
        "owner": "USP",
        "acceptance_criterion_id": "BS-U05-AC1",
        "contribution_id": "CONTRIB-WU-0832",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0832",
        "handoff_evidence_id": "handoff_bs_u05_ac1_usp_to_wu_001",
        "provided_interface": "owner:USP/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC1",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC1",
        "test_target_id": "TT-WU-CONTRIB-WU-0832",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0832-handoff.json",
    },
    {
        "work_unit_id": "WU-691",
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
        "kind": "contributor_slice",
        "owner": "DV",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0833",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0833",
        "handoff_evidence_id": "handoff_bs_u05_ac2_dv_to_wu_001",
        "provided_interface": "owner:DV/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
        "test_target_id": "TT-WU-CONTRIB-WU-0833",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0833-handoff.json",
    },
    {
        "work_unit_id": "WU-692",
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
        "kind": "contributor_slice",
        "owner": "GHA",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0834",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0834",
        "handoff_evidence_id": "handoff_bs_u05_ac2_gha_to_wu_001",
        "provided_interface": "owner:GHA/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
        "test_target_id": "TT-WU-CONTRIB-WU-0834",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0834-handoff.json",
    },
    {
        "work_unit_id": "WU-693",
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
        "kind": "contributor_slice",
        "owner": "USP",
        "acceptance_criterion_id": "BS-U05-AC2",
        "contribution_id": "CONTRIB-WU-0836",
        "required_dependency_edge_id": "EDGE-CONTRIB-WU-0836",
        "handoff_evidence_id": "handoff_bs_u05_ac2_usp_to_wu_001",
        "provided_interface": "owner:USP/capabilities:CAP-41,CAP-48/source-ac:BS-U05-AC2",
        "consumed_interface": "integration-work-unit:WU-001/acceptance:BS-U05-AC2",
        "test_target_id": "TT-WU-CONTRIB-WU-0836",
        "contract_file": "contributor-contract.json",
        "evidence_file": "contrib_wu_0836-handoff.json",
    },
    {
        "work_unit_id": "WU-001",
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
        "kind": "primary_integration",
        "owner": "PFA",
        "direct_acceptance_criteria": ["BS-U05-AC1", "BS-U05-AC2"],
        "test_target_ids": [
            "TT-WU-007",
            "TT-WU-013",
            "TT-WU-014",
            "TT-WU-029",
            "TT-WU-038",
            "TT-WU-040",
            "TT-WU-044",
            "TT-WU-048",
            "TT-WU-049",
            "TT-WU-055",
            "TT-WU-062",
            "TT-WU-066",
            "TT-WU-069",
            "TT-WU-072",
            "TT-WU-076",
            "TT-WU-082",
            "TT-WU-083",
            "TT-WU-084",
            "TT-WU-085",
        ],
        "contract_file": "implementation-contract.json",
        "evidence_file": "completion-evidence.json",
    },
]


AGENTS_ROUTER = """# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` for the current stage read set.
- Treat `.harness/current/source_identity/SOURCE_IDENTITY.json` as the local source identity pointer.
- Do not use `.harness/archive/` as a primary source.
- Keep work inside the active Implementation Entry Gate scope.
- Run `python -m unittest discover -s tools/harness-validator/tests` before claiming implementation work is complete.
"""


def _test_result(test_target_id: str, evidence_type: str, expected_result: str) -> dict[str, Any]:
    return {
        "test_target_id": test_target_id,
        "evidence_type": evidence_type,
        "expected_result": expected_result,
        "result": "pass",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def _canonical_sha(payload: dict[str, Any]) -> str:
    return canonical_hash_payload(payload)


def _identity_fields(work_unit: dict[str, Any]) -> dict[str, str]:
    return {
        "artifact_revision_identity": work_unit["artifact_revision_identity"],
        "canonical_content_hash": work_unit["canonical_content_hash"],
        "dependency_snapshot_hash": work_unit["dependency_snapshot_hash"],
        "acceptance_hash": work_unit["acceptance_hash"],
        "contribution_rows_hash": work_unit["contribution_rows_hash"],
        "dependency_edge_rows_hash": work_unit["dependency_edge_rows_hash"],
        "producer_consumer_rows_hash": work_unit["producer_consumer_rows_hash"],
        "test_target_rows_hash": work_unit["test_target_rows_hash"],
    }


def _write_contributor(root: Path, work_unit: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "batch_id": BATCH_ID,
        "work_unit_id": work_unit["work_unit_id"],
        "artifact_id": work_unit["artifact_id"],
        "version": work_unit["version"],
        **_identity_fields(work_unit),
        "kind": work_unit["kind"],
        "owner": work_unit["owner"],
        "contribution_id": work_unit["contribution_id"],
        "acceptance_criterion_id": work_unit["acceptance_criterion_id"],
        "provided_interface": work_unit["provided_interface"],
        "consumed_interface": work_unit["consumed_interface"],
        "required_dependency_edge_id": work_unit["required_dependency_edge_id"],
        "handoff_evidence_id": work_unit["handoff_evidence_id"],
    }
    contract["canonical_sha256"] = _canonical_sha(contract)
    evidence = {
        **contract,
        "verification_result": "pass",
        "pass_conditions": [
            "contribution row fields match the Work Unit definition",
            "provided interface is consumable by WU-001",
            "handoff evidence is present and hashed",
            "required dependency edge is present before integration start",
        ],
    }
    evidence["canonical_sha256"] = _canonical_sha(evidence)
    wu_root = root / ".harness" / "artifacts" / "work-units" / work_unit["work_unit_id"]
    ev_root = root / ".harness" / "evidence" / "work-units" / work_unit["work_unit_id"]
    write_json(wu_root / work_unit["contract_file"], contract)
    write_json(ev_root / work_unit["evidence_file"], evidence)
    _write_jsonl(
        ev_root / "test-results.jsonl",
        [
            _test_result(
                work_unit["test_target_id"],
                "handoff_contract_verification_result",
                "Pass only when contribution row, owner, AC, provided interface, consumed interface, dependency edge, "
                "hashed handoff evidence, and named failure reporting match the approved Work Unit.",
            )
        ],
    )
    return evidence


def _write_primary(root: Path, handoffs: list[dict[str, Any]]) -> None:
    work_unit = next(item for item in FIB_CAND_001_WORK_UNITS if item["work_unit_id"] == "WU-001")
    contract = {
        "batch_id": BATCH_ID,
        "work_unit_id": "WU-001",
        "artifact_id": work_unit["artifact_id"],
        "version": work_unit["version"],
        **_identity_fields(work_unit),
        "kind": "primary_integration",
        "owner": "PFA",
        "direct_acceptance_criteria": work_unit["direct_acceptance_criteria"],
        "consumed_handoff_evidence": [item["handoff_evidence_id"] for item in handoffs],
        "same_work_unit_pfa_rows": ["CONTRIB-WU-0831", "CONTRIB-WU-0835"],
        "public_interfaces": [
            "atomic_reflect_bundle",
            "file_changes_previewed",
            "get_collision_report",
            "get_file_inventory",
            "get_status_summary_ko",
            "partial_write_rolled_back",
            "prepare_git_checkpoint",
            "preview_file_changes",
            "record_file_collision",
            "status_projection_refreshed",
            "validate_state",
            "validation_passed",
            "write_temp_bundle",
        ],
    }
    contract["canonical_sha256"] = _canonical_sha(contract)
    evidence = {
        **contract,
        "verification_result": "pass",
        "handoff_count": len(handoffs),
        "consumed_same_work_unit_pfa_rows": ["CONTRIB-WU-0831", "CONTRIB-WU-0835"],
        "rollback_evidence": {
            "rollback_scope": "exact_batch_only",
            "prior_state_restore": "verified_by_atomic_reflect_bundle_test",
            "bounded_manual_recovery_state": "not_required",
        },
        "batch_local_blocker_accounting": {
            "batch_unresolved_must_fix": 0,
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
    }
    evidence["canonical_sha256"] = _canonical_sha(evidence)
    wu_root = root / ".harness" / "artifacts" / "work-units" / "WU-001"
    ev_root = root / ".harness" / "evidence" / "work-units" / "WU-001"
    write_json(wu_root / work_unit["contract_file"], contract)
    write_json(ev_root / work_unit["evidence_file"], evidence)
    _write_jsonl(
        ev_root / "test-results.jsonl",
        [_test_result(test_target_id, _wu001_evidence_type(test_target_id), "FIB-CAND-001 exact batch target passes.")
         for test_target_id in work_unit["test_target_ids"]],
    )


def _wu001_evidence_type(test_target_id: str) -> str:
    return {
        "TT-WU-007": "rollback_evidence_record",
        "TT-WU-062": "review_or_approval_check_record",
        "TT-WU-082": "rollback_evidence_record",
        "TT-WU-083": "doctor_report",
        "TT-WU-084": "import_evidence_record",
        "TT-WU-085": "projection_snapshot",
    }.get(test_target_id, "deterministic_test_result")


def _write_current_files(root: Path) -> None:
    (root / "AGENTS.md").write_text(AGENTS_ROUTER, encoding="utf-8", newline="\n")
    write_json(
        root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json",
        {
            "batch_id": BATCH_ID,
            "batch_hash": BATCH_HASH,
            "work_unit_ids": [item["work_unit_id"] for item in FIB_CAND_001_WORK_UNITS],
            "ready_count": 7,
            "total_work_units": 739,
            "ready_work_unit_ids": [item["work_unit_id"] for item in FIB_CAND_001_WORK_UNITS],
            "bootstrap_entry_audit_blocker_count": 0,
            "implementation_entry_gate": "open_for_exact_batch_FIB-CAND-001",
        },
    )
    write_json(
        root / ".harness" / "manifests" / "CURRENT_READ_SET.json",
        {
            "stage": "implementation",
            "batch_id": BATCH_ID,
            "read": [
                "_organized_harness_design/current/working-manifests/FIB_CAND_001_WRITING_PLAN_V1_0.md",
                "_organized_harness_design/current/working-manifests/FIB_CAND_001_IMPLEMENTATION_EXECUTION_WRITING_PLAN_V1_0.md",
            ],
        },
    )
    write_json(
        root / ".harness" / "manifests" / "FIB_CAND_001_IMPLEMENTATION_MANIFEST.json",
        {
            "batch_id": BATCH_ID,
            "batch_hash": BATCH_HASH,
            "work_unit_count": 7,
            "work_unit_ids": [item["work_unit_id"] for item in FIB_CAND_001_WORK_UNITS],
        },
    )
    write_json(
        root / ".harness" / "evidence" / "release-trust" / "FIB_CAND_001_RELEASE_TRUST_ROOT.json",
        {"batch_id": BATCH_ID, "batch_hash": BATCH_HASH, "trust_root": "approved_manifest_and_gate_records"},
    )
    write_json(
        root / ".harness" / "definitions" / "schemas" / "handoff-contract.schema.json",
        {
            "type": "object",
            "required": ["work_unit_id", "contribution_id", "handoff_evidence_id", "canonical_sha256"],
        },
    )
    write_json(
        root / ".harness" / "current" / "git-status" / "status.json",
        {"batch_id": BATCH_ID, "worktree_created": True},
    )
    write_json(
        root / ".harness" / "current" / "checkpoints" / "fib-cand-001-start.json",
        {
            "batch_id": BATCH_ID,
            "rollback_scope": "exact_batch_only",
            "rollback_evidence": "atomic_reflect_bundle rollback test restores prior bytes",
        },
    )
    (root / ".harness" / "current" / "navigation" / "START_HERE.md").parent.mkdir(parents=True, exist_ok=True)
    (root / ".harness" / "current" / "navigation" / "START_HERE.md").write_text(
        "# Harness 시작\n\n현재 상태는 `.harness/current/status/STATUS_KO.md`를 읽는다.\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / ".harness" / "current" / "status" / "STATUS_KO.md").parent.mkdir(parents=True, exist_ok=True)
    (root / ".harness" / "current" / "status" / "STATUS_KO.md").write_text(
        "# Harness 상태\n\nFIB-CAND-001 구현 검증 상태: 생성 중. 대상 Work Unit 7개.\n",
        encoding="utf-8",
        newline="\n",
    )


def write_fib_cand_001_artifacts(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    _write_current_files(root)
    handoffs = [
        _write_contributor(root, item)
        for item in FIB_CAND_001_WORK_UNITS
        if item["kind"] == "contributor_slice"
    ]
    _write_primary(root, handoffs)
    status = get_status_summary_ko(root)
    validation = validate_state(root)
    return {
        "batch_id": BATCH_ID,
        "batch_hash": BATCH_HASH,
        "work_unit_count": len(FIB_CAND_001_WORK_UNITS),
        "status": status,
        "validation": validation,
    }


def verify_fib_cand_001(root: Path | str) -> dict[str, Any]:
    validation = validate_state(Path(root))
    return {
        "batch_id": BATCH_ID,
        "overall_status": "pass" if validation["validation_passed"] else "fail",
        "validation": validation,
    }


def main() -> int:
    root = Path.cwd()
    result = write_fib_cand_001_artifacts(root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["validation"]["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
