import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from harness_validator.contributor_batch import (  # noqa: E402
    PAC10_BATCH_001_ID,
    load_contributor_batch,
    main,
    validate_contributor_batch,
    write_contributor_batch_artifacts,
)


def _sha(payload):
    import hashlib

    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class ContributorBatchTests(unittest.TestCase):
    def test_loads_exact_pac10_batch_001_identity(self):
        root = Path(__file__).resolve().parents[3]
        batch = load_contributor_batch(root, PAC10_BATCH_001_ID)

        self.assertEqual(batch["batch_id"], "PAC10-BATCH-001")
        self.assertEqual(batch["source_wave_id"], "WAVE-001")
        self.assertEqual(batch["work_unit_count"], 25)
        self.assertEqual(batch["work_unit_ids"][0], "WU-107")
        self.assertEqual(batch["work_unit_ids"][-1], "WU-131")
        self.assertTrue(all(unit["work_unit_kind"] == "contributor_slice" for unit in batch["work_units"]))

    def test_cli_accepts_next_contributor_batch_id(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exit_code = main(
                [
                    "--root",
                    str(root),
                    "--source-root",
                    str(source_root),
                    "--batch-id",
                    "PAC10-BATCH-002",
                ]
            )

            self.assertEqual(exit_code, 0)
            manifest = json.loads(
                (root / ".harness" / "manifests" / "PAC10_BATCH_002_IMPLEMENTATION_MANIFEST.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["batch_id"], "PAC10-BATCH-002")
            self.assertEqual(manifest["work_unit_count"], 25)
            self.assertEqual(manifest["work_unit_ids"][0], "WU-132")
            self.assertEqual(manifest["work_unit_ids"][-1], "WU-156")
            self.assertTrue(
                (
                    root
                    / ".harness"
                    / "evidence"
                    / "implementation-entry"
                    / "PAC10_BATCH_002_CANDIDATE_SOURCE_IDENTITY.json"
                ).exists()
            )

    def test_writes_contract_handoff_and_test_evidence_for_all_units(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], True)
            self.assertEqual(validation["batch_local_blockers"]["batch_missing_completion_evidence"], 0)
            self.assertEqual(validation["batch_local_blockers"]["batch_missing_test_target_evidence"], 0)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 0)
            self.assertEqual(validation["batch_local_blockers"]["batch_out_of_scope_file_change"], 0)

            for work_unit_id in ["WU-107", "WU-108", "WU-131"]:
                contract_path = root / ".harness" / "artifacts" / "work-units" / work_unit_id / "contributor-contract.json"
                evidence_dir = root / ".harness" / "evidence" / "work-units" / work_unit_id
                test_path = evidence_dir / "test-results.jsonl"
                self.assertTrue(contract_path.exists(), work_unit_id)
                self.assertTrue(test_path.exists(), work_unit_id)
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                self.assertEqual(contract["work_unit_kind"], "contributor_slice")
                self.assertEqual(contract["batch_id"], "PAC10-BATCH-001")
                self.assertRegex(contract["canonical_sha256"], r"^[0-9a-f]{64}$")
                evidence_path = evidence_dir / f"{contract['handoff_evidence']}.json"
                self.assertTrue(evidence_path.exists(), work_unit_id)

            self.assertFalse((root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json").exists())
            candidate_identity = json.loads(
                (
                    root
                    / ".harness"
                    / "evidence"
                    / "implementation-entry"
                    / "PAC10_BATCH_001_CANDIDATE_SOURCE_IDENTITY.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(candidate_identity["implementation_entry_gate"], "not_widened_by_candidate_registry")
            self.assertEqual(candidate_identity["candidate_registry_approval_status"], "not_approved")
            self.assertEqual(candidate_identity["candidate_registry_gate_effect"], "none")
            self.assertEqual(candidate_identity["official_approval_record_created"], False)
            self.assertEqual(candidate_identity["official_ready_count"], 7)
            self.assertEqual(candidate_identity["runtime_selected_work_unit_count"], 25)

    def test_does_not_overwrite_existing_official_source_identity(self):
        source_root = Path(__file__).resolve().parents[3]
        official_source_identity = {
            "batch_hash": "0c455e8c55886e22322995c6466ea990e9fc3342b82b5ea5c76433527b2038a3",
            "batch_id": "FIB-CAND-001",
            "bootstrap_entry_audit_blocker_count": 0,
            "implementation_entry_gate": "open_for_exact_batch_FIB-CAND-001",
            "ready_count": 7,
            "ready_work_unit_ids": ["WU-688", "WU-689", "WU-690", "WU-691", "WU-692", "WU-693", "WU-001"],
            "total_work_units": 739,
            "work_unit_ids": ["WU-688", "WU-689", "WU-690", "WU-691", "WU-692", "WU-693", "WU-001"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_identity_path = root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json"
            source_identity_path.parent.mkdir(parents=True)
            source_identity_path.write_text(
                json.dumps(official_source_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            self.assertEqual(
                json.loads(source_identity_path.read_text(encoding="utf-8")),
                official_source_identity,
            )

    def test_rejects_pac10_shaped_official_source_identity(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_identity_path = root / ".harness" / "current" / "source_identity" / "SOURCE_IDENTITY.json"
            source_identity_path.parent.mkdir(parents=True)
            source_identity_path.write_text(
                json.dumps(
                    {
                        "batch_id": "PAC10-BATCH-001",
                        "implementation_entry_gate": "open_for_exact_batch_PAC10-BATCH-001",
                        "ready_count": 25,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("official source identity", " ".join(validation["content_errors"]))

    def test_rejects_tampered_identity_and_missing_declared_artifact(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            contract_path = root / ".harness" / "artifacts" / "work-units" / "WU-107" / "contributor-contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["dependency_snapshot_hash"] = "0" * 64
            contract.pop("canonical_sha256", None)
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("contract payload", " ".join(validation["content_errors"]))

            contract_path.unlink()
            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("missing", " ".join(validation["content_errors"]))

    def test_rejects_recomputed_hash_payload_tampering(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            evidence_path = root / ".harness" / "evidence" / "work-units" / "WU-107" / "handoff_bs_a01_ac1_pfa_to_wu_006.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["primary_owner"] = "WRONG"
            evidence["pass_conditions"] = ["changed"]
            evidence.pop("canonical_sha256", None)
            evidence["canonical_sha256"] = _sha(evidence)
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("evidence payload", " ".join(validation["content_errors"]))

    def test_rejects_tampered_declared_current_artifacts(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            manifest_path = root / ".harness" / "manifests" / "PAC10_BATCH_001_IMPLEMENTATION_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["work_unit_count"] = 24
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("manifest: payload mismatch", validation["content_errors"])

    def test_rejects_tampered_status_text(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            status_path = root / ".harness" / "current" / "status" / "STATUS_KO.md"
            status_path.write_text(
                "# Harness 상태\n\nPAC10-BATCH-001 WRONG STATUS 공식 Gate는 candidate registry로 확장하지 않음. 대상 Work Unit 25개.\n",
                encoding="utf-8",
                newline="\n",
            )

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("status: candidate/gate boundary text mismatch", validation["content_errors"])

    def test_rejects_wrong_allowed_status_substitution(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)

            status_path = root / ".harness" / "current" / "status" / "STATUS_KO.md"
            status_path.write_text(
                "# Harness 상태\n\nPAC10-BATCH-001 contributor batch 후보 evidence 검증 상태: 실패. 공식 Gate는 candidate registry로 확장하지 않음. 대상 Work Unit 25개.\n",
                encoding="utf-8",
                newline="\n",
            )

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("status: candidate/gate boundary text mismatch", validation["content_errors"])

    def test_rejects_pac10_approval_record_file(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)
            forbidden = (
                root
                / ".harness"
                / "evidence"
                / "implementation-entry"
                / "PAC10_BATCH_001_APPROVAL_RECORD.json"
            )
            forbidden.write_text('{"approval_status":"approved"}\n', encoding="utf-8", newline="\n")

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("official approval record forbidden", " ".join(validation["content_errors"]))

    def test_rejects_pac10_approval_record_content_under_different_name(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)
            forbidden = (
                root
                / ".harness"
                / "evidence"
                / "implementation-entry"
                / "FIRST_IMPLEMENTATION_BATCH_APPROVAL_RECORD_V1_0.md"
            )
            forbidden.write_text(
                "approval_status: approved\nbatch_id: PAC10-BATCH-001\n",
                encoding="utf-8",
                newline="\n",
            )

            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("official approval record forbidden", " ".join(validation["content_errors"]))

    def test_rejects_registry_snapshot_drift(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            source_copy = Path(tmp) / "source"
            for rel_path in [
                "_organized_harness_design/current/working-manifests/IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_DEPENDENCY_EDGE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_PRODUCER_CONSUMER_DEPENDENCY_REGISTRY_V1_0.jsonl",
            ]:
                target = source_copy / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_root / rel_path, target)
            root = Path(tmp) / "target"
            root.mkdir()

            registry = (
                source_copy
                / "_organized_harness_design"
                / "active"
                / "current-stage"
                / "work-units"
                / "WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl"
            )
            lines = registry.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if '"contributor_work_unit_id":"WU-107"' in line:
                    row = json.loads(line)
                    row["provided_interface"] = "changed"
                    lines[index] = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    break
            registry.write_text("\n".join(lines) + "\n", encoding="utf-8")

            write_contributor_batch_artifacts(root, source_copy, PAC10_BATCH_001_ID)
            validation = validate_contributor_batch(root, source_copy, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("contribution_rows_hash stale", " ".join(validation["content_errors"]))

    def test_rejects_contributor_slice_registry_drift_against_cross_registry_rows(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            source_copy = Path(tmp) / "source"
            for rel_path in [
                "_organized_harness_design/current/working-manifests/IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_OWNER_CONTRIBUTION_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_DEPENDENCY_EDGE_REGISTRY_V1_0.jsonl",
                "_organized_harness_design/active/current-stage/work-units/WORK_UNIT_PRODUCER_CONSUMER_DEPENDENCY_REGISTRY_V1_0.jsonl",
            ]:
                target = source_copy / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_root / rel_path, target)
            root = Path(tmp) / "target"
            root.mkdir()

            registry = (
                source_copy
                / "_organized_harness_design"
                / "active"
                / "current-stage"
                / "work-units"
                / "WORK_UNIT_CONTRIBUTOR_SLICE_REGISTRY_V1_0.jsonl"
            )
            lines = registry.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if '"contributor_slice_work_unit_id":"WU-107"' in line:
                    row = json.loads(line)
                    row["provided_interface"] = "STALE-MUTATED-PROVIDED-INTERFACE"
                    row["handoff_contract_verification_criteria"]["provided_interface"] = (
                        "STALE-MUTATED-PROVIDED-INTERFACE"
                    )
                    lines[index] = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    break
            registry.write_text("\n".join(lines) + "\n", encoding="utf-8")

            write_contributor_batch_artifacts(root, source_copy, PAC10_BATCH_001_ID)
            validation = validate_contributor_batch(root, source_copy, PAC10_BATCH_001_ID)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("disagrees with contributor slice", " ".join(validation["content_errors"]))

    def test_git_scope_detects_unrelated_files(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            write_contributor_batch_artifacts(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(
                validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)["batch_local_blockers"][
                    "batch_out_of_scope_file_change"
                ],
                0,
            )

            (root / "unexpected.txt").write_text("outside\n", encoding="utf-8")
            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertEqual(validation["batch_local_blockers"]["batch_out_of_scope_file_change"], 1)
            self.assertIn("unexpected.txt", validation["out_of_scope_file_changes"])

            pycache = root / "tools" / "harness-validator" / "__pycache__"
            pycache.mkdir(parents=True)
            (pycache / "x.pyc").write_bytes(b"bytecode")
            validation = validate_contributor_batch(root, source_root, PAC10_BATCH_001_ID)
            self.assertIn("tools/harness-validator/__pycache__/x.pyc", validation["out_of_scope_file_changes"])


if __name__ == "__main__":
    unittest.main()
