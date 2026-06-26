import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from harness_validator.final_release import (  # noqa: E402
    build_release_candidate,
    validate_release_candidate,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


class FinalReleaseTests(unittest.TestCase):
    def _seed_minimal_project(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        _write_jsonl(
            root
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "technical-architecture"
            / "TECHNICAL_ARCHITECTURE_ACCEPTANCE_CRITERION_TRACE_REGISTRY_V1_2.jsonl",
            [{"registry_id": "AC-1"}, {"registry_id": "AC-2"}],
        )
        _write_json(
            root
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "technical-architecture"
            / "TECHNICAL_ARCHITECTURE_COMMAND_QUERY_EVENT_CATALOG_V1_2.json",
            {"entries": [{"id": "cmd_one"}, {"id": "query_two"}]},
        )
        _write_jsonl(
            root
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "work-units"
            / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl",
            [{"test_target_id": "TT-1"}, {"test_target_id": "TT-2"}],
        )
        _write_jsonl(
            root / "_organized_harness_design" / "manifests" / "WORK_UNIT_APPROVAL_TARGET_LIST_V1_0.jsonl",
            [{"work_unit_id": "WU-001"}, {"work_unit_id": "WU-002"}],
        )
        _write_json(
            root / ".harness" / "evidence" / "work-units" / "WU-001" / "completion-evidence.json",
            {
                "work_unit_id": "WU-001",
                "completion_result": "pass",
                "direct_acceptance_criterion_ids": ["AC-1"],
                "command_query_event_ids": ["cmd_one"],
                "provided_interfaces": ["query_two"],
                "test_target_ids": ["TT-1"],
            },
        )
        _write_json(
            root / ".harness" / "evidence" / "work-units" / "WU-002" / "handoff_ac2.json",
            {
                "work_unit_id": "WU-002",
                "verification_result": "pass",
                "acceptance_criterion_id": "AC-2",
            },
        )
        _write_jsonl(
            root / ".harness" / "evidence" / "work-units" / "WU-001" / "test-results.jsonl",
            [{"test_target_id": "TT-1", "result": "pass", "evidence_type": "deterministic_test_result"}],
        )
        _write_jsonl(
            root / ".harness" / "evidence" / "work-units" / "WU-002" / "test-results.jsonl",
            [{"test_target_id": "TT-2", "result": "pass", "evidence_type": "handoff_contract_verification_result"}],
        )
        (root / "AGENTS.md").write_text("Harness test fixture\n", encoding="utf-8")
        (root / "README.md").write_text("# Harness test README\n", encoding="utf-8")
        (root / "install-harness.ps1").write_text("Write-Output 'install fixture'\n", encoding="utf-8")
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "BRANCH_STRUCTURE_KO.md").write_text("# Branch fixture\n", encoding="utf-8")

    def test_release_candidate_passes_with_full_coverage_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_minimal_project(root)

            result = build_release_candidate(root, root, "harness-v1.0.0-rc.test")

            self.assertEqual(result["validation_passed"], True)
            self.assertEqual(result["coverage"]["acceptance_criteria"]["missing_count"], 0)
            self.assertEqual(result["coverage"]["command_query_event"]["missing_count"], 0)
            self.assertEqual(result["coverage"]["test_targets"]["missing_count"], 0)
            self.assertEqual(result["classification_scan_findings"], [])
            self.assertRegex(result["release_candidate_manifest_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                sorted(result["release_closure_checks"]),
                [f"REL-CLOSE-{number:02d}" for number in range(1, 9)],
            )
            self.assertEqual(result["release_closure_checks"]["REL-CLOSE-07"]["status"], "not_applicable_for_release_candidate")
            self.assertTrue(
                (root / ".harness" / "evidence" / "release-candidate" / "RELEASE_CANDIDATE_MANIFEST_V1_0.json").exists()
            )

    def test_release_candidate_fails_when_test_target_evidence_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_minimal_project(root)
            (root / ".harness" / "evidence" / "work-units" / "WU-002" / "test-results.jsonl").unlink()

            result = validate_release_candidate(root, root, "harness-v1.0.0-rc.test")

            self.assertEqual(result["validation_passed"], False)
            self.assertEqual(result["final_release_blockers"]["missing_test_target_evidence"], 1)
            self.assertEqual(result["coverage"]["test_targets"]["missing_count"], 1)

    def test_release_candidate_fails_when_completion_evidence_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_minimal_project(root)
            completion = root / ".harness" / "evidence" / "work-units" / "WU-001" / "completion-evidence.json"
            payload = json.loads(completion.read_text(encoding="utf-8"))
            payload["completion_result"] = "fail"
            payload.pop("verification_result", None)
            _write_json(completion, payload)

            result = validate_release_candidate(root, root, "harness-v1.0.0-rc.test")

            self.assertEqual(result["validation_passed"], False)
            self.assertEqual(result["final_release_blockers"]["missing_completion_evidence"], 1)

    def test_release_candidate_fails_when_handoff_evidence_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_minimal_project(root)
            handoff = root / ".harness" / "evidence" / "work-units" / "WU-002" / "handoff_ac2.json"
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            payload["verification_result"] = "fail"
            _write_json(handoff, payload)

            result = validate_release_candidate(root, root, "harness-v1.0.0-rc.test")

            self.assertEqual(result["validation_passed"], False)
            self.assertEqual(result["final_release_blockers"]["missing_completion_evidence"], 1)

    def test_release_candidate_fails_on_root_duplicate_and_secret_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_minimal_project(root)
            shutil.copy2(root / "AGENTS.md", root / "GPT_PRO_REVIEW_RESULT_WORK_UNITS_V1_0.md")
            (root / ".harness" / "evidence" / "work-units" / "WU-001" / "secret.txt").write_text(
                "api_" + "key = sk_test_123456789\n", encoding="utf-8"
            )

            result = validate_release_candidate(root, root, "harness-v1.0.0-rc.test")

            self.assertEqual(result["validation_passed"], False)
            self.assertEqual(result["final_release_blockers"]["duplicate_scan_finding"], 1)
            self.assertEqual(result["final_release_blockers"]["secret_scan_finding"], 1)


if __name__ == "__main__":
    unittest.main()
