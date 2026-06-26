import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from harness_validator.fib_cand_001 import (  # noqa: E402
    FIB_CAND_001_WORK_UNITS,
    write_fib_cand_001_artifacts,
    verify_fib_cand_001,
)
from harness_validator.project_file_application import (  # noqa: E402
    atomic_reflect_bundle,
    get_collision_report,
    get_file_inventory,
    get_status_summary_ko,
    prepare_git_checkpoint,
    preview_file_changes,
    record_file_collision,
    sha256_text,
    validate_state,
    write_temp_bundle,
)


class FibCand001Tests(unittest.TestCase):
    def test_writes_exact_contributor_and_primary_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = write_fib_cand_001_artifacts(root)

            self.assertEqual(result["batch_id"], "FIB-CAND-001")
            self.assertEqual(result["work_unit_count"], 7)
            self.assertEqual(
                [item["work_unit_id"] for item in FIB_CAND_001_WORK_UNITS],
                ["WU-688", "WU-689", "WU-690", "WU-691", "WU-692", "WU-693", "WU-001"],
            )
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertLess(len((root / "AGENTS.md").read_text(encoding="utf-8").splitlines()), 40)

            for work_unit in FIB_CAND_001_WORK_UNITS:
                work_unit_id = work_unit["work_unit_id"]
                contract_path = root / ".harness" / "artifacts" / "work-units" / work_unit_id / work_unit["contract_file"]
                test_path = root / ".harness" / "evidence" / "work-units" / work_unit_id / "test-results.jsonl"
                self.assertTrue(contract_path.exists(), work_unit_id)
                self.assertTrue(test_path.exists(), work_unit_id)
                self.assertIn("pass", test_path.read_text(encoding="utf-8"))

            for work_unit_id in ["WU-688", "WU-689", "WU-690", "WU-691", "WU-692", "WU-693"]:
                handoff = next(item for item in FIB_CAND_001_WORK_UNITS if item["work_unit_id"] == work_unit_id)
                handoff_path = root / ".harness" / "evidence" / "work-units" / work_unit_id / handoff["evidence_file"]
                payload = json.loads(handoff_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["verification_result"], "pass")
                self.assertEqual(payload["required_dependency_edge_id"], handoff["required_dependency_edge_id"])
                self.assertEqual(payload["handoff_evidence_id"], handoff["handoff_evidence_id"])
                for identity_field in [
                    "artifact_revision_identity",
                    "canonical_content_hash",
                    "dependency_snapshot_hash",
                    "acceptance_hash",
                    "contribution_rows_hash",
                    "dependency_edge_rows_hash",
                    "producer_consumer_rows_hash",
                    "test_target_rows_hash",
                ]:
                    self.assertEqual(payload[identity_field], handoff[identity_field])
                self.assertRegex(payload["canonical_sha256"], r"^[0-9a-f]{64}$")

            completion = json.loads(
                (root / ".harness" / "evidence" / "work-units" / "WU-001" / "completion-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(completion["verification_result"], "pass")
            self.assertEqual(len(completion["consumed_handoff_evidence"]), 6)
            self.assertEqual(completion["consumed_same_work_unit_pfa_rows"], ["CONTRIB-WU-0831", "CONTRIB-WU-0835"])
            self.assertEqual(completion["same_work_unit_pfa_rows"], ["CONTRIB-WU-0831", "CONTRIB-WU-0835"])

            wu001_tests = [
                json.loads(line)
                for line in (
                    root / ".harness" / "evidence" / "work-units" / "WU-001" / "test-results.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            evidence_types = {row["test_target_id"]: row["evidence_type"] for row in wu001_tests}
            self.assertEqual(evidence_types["TT-WU-007"], "rollback_evidence_record")
            self.assertEqual(evidence_types["TT-WU-062"], "review_or_approval_check_record")
            self.assertEqual(evidence_types["TT-WU-082"], "rollback_evidence_record")
            self.assertEqual(evidence_types["TT-WU-083"], "doctor_report")
            self.assertEqual(evidence_types["TT-WU-084"], "import_evidence_record")
            self.assertEqual(evidence_types["TT-WU-085"], "projection_snapshot")

    def test_project_file_application_preview_apply_inventory_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "AGENTS.md"
            existing.write_text("existing\n", encoding="utf-8")

            changes = {
                "AGENTS.md": "new router\n",
                ".harness/current/status/STATUS_KO.md": "# 상태\n",
            }
            preview = preview_file_changes(root, changes)
            self.assertEqual(preview["changes"]["AGENTS.md"]["operation"], "modify")
            self.assertEqual(preview["changes"][".harness/current/status/STATUS_KO.md"]["operation"], "create")

            collision = record_file_collision(root, "AGENTS.md", "existing AGENTS.md requires creator review")
            self.assertEqual(collision["path"], "AGENTS.md")
            self.assertEqual(get_collision_report(root)["collision_count"], 1)

            bundle = write_temp_bundle(root, changes)
            apply_result = atomic_reflect_bundle(root, bundle["bundle_id"])
            self.assertEqual(apply_result["reflected"], True)
            self.assertEqual(existing.read_text(encoding="utf-8"), "new router\n")

            inventory = get_file_inventory(root)
            self.assertIn("AGENTS.md", {item["path"] for item in inventory["files"]})
            self.assertEqual(prepare_git_checkpoint(root)["git_available"], False)

            rollback_result = atomic_reflect_bundle(root, bundle["bundle_id"], rollback=True)
            self.assertEqual(rollback_result["rolled_back"], True)
            self.assertEqual(existing.read_text(encoding="utf-8"), "existing\n")

    def test_rejects_unsafe_paths_before_preview_or_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for unsafe in ["/tmp/outside.txt", "\\tmp\\outside.txt", "C:outside.txt", "../outside.txt", "a\\b.txt"]:
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(ValueError):
                        preview_file_changes(root, {unsafe: "bad\n"})

    def test_atomic_reflect_bundle_rolls_back_when_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keep = root / "keep.txt"
            keep.write_text("before\n", encoding="utf-8")
            blocked_parent = root / "blocked"
            blocked_parent.write_text("not a directory\n", encoding="utf-8")
            bundle = write_temp_bundle(root, {"keep.txt": "after\n", "blocked/file.txt": "cannot write\n"})

            with self.assertRaises(OSError):
                atomic_reflect_bundle(root, bundle["bundle_id"])

            self.assertEqual(keep.read_text(encoding="utf-8"), "before\n")

    def test_atomic_reflect_bundle_rejects_unsafe_bundle_id_and_restores_created_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = write_temp_bundle(root, {"new/dir/file.txt": "created\n"})

            with self.assertRaises(ValueError):
                atomic_reflect_bundle(root, "../../../../outside")

            atomic_reflect_bundle(root, bundle["bundle_id"])
            self.assertTrue((root / "new" / "dir" / "file.txt").exists())

            rollback = atomic_reflect_bundle(root, bundle["bundle_id"], rollback=True)
            self.assertEqual(rollback["partial_write_rolled_back"], True)
            self.assertFalse((root / "new").exists())

    def test_validate_state_and_korean_status_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fib_cand_001_artifacts(root)

            validation = validate_state(root)
            self.assertEqual(validation["validation_passed"], True)
            self.assertEqual(validation["batch_local_blockers"]["batch_missing_completion_evidence"], 0)
            self.assertEqual(validation["batch_local_blockers"]["batch_missing_test_target_evidence"], 0)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 0)

            status = get_status_summary_ko(root)
            self.assertIn("FIB-CAND-001", status["summary_ko"])
            self.assertIn("통과", status["summary_ko"])

            verify = verify_fib_cand_001(root)
            self.assertEqual(verify["overall_status"], "pass")

    def test_validate_state_rejects_corrupted_evidence_and_hashes_are_recomputable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fib_cand_001_artifacts(root)

            evidence_path = root / ".harness" / "evidence" / "work-units" / "WU-688" / "contrib_wu_0829-handoff.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            stated = evidence.pop("canonical_sha256")
            self.assertEqual(stated, sha256_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))))

            evidence["owner"] = "WRONG"
            evidence["canonical_sha256"] = stated
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("WU-688", " ".join(validation["content_errors"]))

    def test_validate_state_rejects_tampered_identity_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fib_cand_001_artifacts(root)

            for rel_path in [
                ".harness/artifacts/work-units/WU-688/contributor-contract.json",
                ".harness/evidence/work-units/WU-688/contrib_wu_0829-handoff.json",
            ]:
                path = root / rel_path
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["dependency_snapshot_hash"] = "0" * 64
                payload.pop("canonical_sha256", None)
                payload["canonical_sha256"] = sha256_text(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                )
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8",
                )

            validation = validate_state(root)
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("approved target", " ".join(validation["content_errors"]))

    def test_validate_state_requires_declared_batch_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fib_cand_001_artifacts(root)

            (root / ".harness" / "evidence" / "release-trust" / "FIB_CAND_001_RELEASE_TRUST_ROOT.json").unlink()
            validation = validate_state(root)

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("declared artifact missing", " ".join(validation["content_errors"]))

    def test_validate_state_counts_out_of_scope_git_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            write_fib_cand_001_artifacts(root)
            self.assertEqual(validate_state(root)["batch_local_blockers"]["batch_out_of_scope_file_change"], 0)

            outside = root / "unexpected.txt"
            outside.write_text("outside\n", encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_out_of_scope_file_change"], 1)
            self.assertIn("unexpected.txt", validation["out_of_scope_file_changes"])

    def test_validate_state_counts_renamed_out_of_scope_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            write_fib_cand_001_artifacts(root)
            (root / "unexpected.txt").write_text("outside\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True, text=True)

            target = root / ".harness" / "current" / "source_identity" / "renamed.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "mv", "unexpected.txt", target.relative_to(root).as_posix()], cwd=root, check=True)

            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_out_of_scope_file_change"], 1)
            self.assertIn("unexpected.txt", validation["out_of_scope_file_changes"])

    def test_public_helper_state_paths_do_not_poison_batch_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            write_fib_cand_001_artifacts(root)

            write_temp_bundle(root, {"AGENTS.md": "new router\n"})
            record_file_collision(root, "AGENTS.md", "test collision")

            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_out_of_scope_file_change"], 0)

    def test_secret_scan_ignores_policy_words_and_flags_real_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = root / "_organized_harness_design" / "approved" / "policy.md"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "API key, password, authentication token, and recovery code must not be stored.\n",
                encoding="utf-8",
            )
            write_fib_cand_001_artifacts(root)
            self.assertEqual(validate_state(root)["batch_local_blockers"]["batch_secret_scan_finding"], 0)

            leak = root / ".harness" / "current" / "source_identity" / "leak.env"
            leak.write_text("API" + "_KEY=" + "sk-test-value\n", encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 1)
            self.assertEqual(validation["secret_findings"][0]["path"], ".harness/current/source_identity/leak.env")

            leak.unlink()
            json_leak = root / ".harness" / "current" / "source_identity" / "leak.json"
            json_leak.write_text('{"api' + '_key":"sk-test-value"}\n', encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 1)
            self.assertEqual(validation["secret_findings"][0]["path"], ".harness/current/source_identity/leak.json")

            json_leak.unlink()
            prefixed_leak = root / ".harness" / "current" / "source_identity" / "prefixed.env"
            prefixed_leak.write_text("OPENAI" + "_API_KEY=" + "sk-test-value\n", encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 1)
            self.assertEqual(validation["secret_findings"][0]["path"], ".harness/current/source_identity/prefixed.env")

            prefixed_leak.unlink()
            aws_leak = root / ".harness" / "current" / "source_identity" / "aws.env"
            aws_leak.write_text("AWS" + "_SECRET_ACCESS_KEY=" + "aws-secret-value\n", encoding="utf-8")
            validation = validate_state(root)
            self.assertEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 1)
            self.assertEqual(validation["secret_findings"][0]["path"], ".harness/current/source_identity/aws.env")


if __name__ == "__main__":
    unittest.main()
