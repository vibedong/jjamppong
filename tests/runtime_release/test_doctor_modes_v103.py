import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness-validator"))
from harness_validator.doctor import validate


class DoctorModesTests(unittest.TestCase):
    def install_project(self, target):
        result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Install", "-TargetPath", str(target), "-SourcePath", str(ROOT)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installed_project_allows_generated_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            self.install_project(target)
            (target / ".harness/artifacts/demo.md").parent.mkdir(parents=True, exist_ok=True)
            (target / ".harness/artifacts/demo.md").write_text("artifact\n", encoding="utf-8")
            result = validate(target, mode="installed-project")
            self.assertEqual(result["overall_status"], "pass", result)
            self.assertEqual(result["exit_code"], 0)

    def test_release_payload_rejects_generated_state_and_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload"
            target.mkdir()
            self.install_project(target)
            (target / ".harness/artifacts/demo.md").parent.mkdir(parents=True, exist_ok=True)
            (target / ".harness/artifacts/demo.md").write_text("artifact\n", encoding="utf-8")
            (target / "tests/runtime_release/example.py").parent.mkdir(parents=True, exist_ok=True)
            (target / "tests/runtime_release/example.py").write_text("x=1\n", encoding="utf-8")
            result = validate(target, mode="release-payload")
            self.assertEqual(result["overall_status"], "fail")
            codes = {b["code"] for b in result["blockers"]}
            self.assertIn("doctor.forbidden_path", codes)

    def test_cli_accepts_mode_and_outputs_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            self.install_project(target)
            result = subprocess.run(["python", str(target / "tools/harness-validator/run-doctor.py"), "--mode", "installed-project", str(target)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["mode"], "installed-project")
            self.assertEqual(payload["exit_code"], 0)
            for key in ("schema_version", "command", "overall_status", "blocker_count", "blockers", "warnings", "exit_code", "checked_at_utc", "korean_summary", "stage", "stage_set_version", "read_set_paths", "state_conflicts", "path_policy_findings"):
                self.assertIn(key, payload)
            self.assertIn("implementation_start_possible", payload["korean_summary"])

    def test_installed_project_detects_workflow_policy_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            self.install_project(target)
            (target / ".harness/manifests/CURRENT_READ_SET.json").write_text('{"paths":["tools/harness-validator","_organized_harness_design/archive"]}\n', encoding="utf-8")
            (target / ".harness/current/planning/PRODUCT_SCOPE.md").parent.mkdir(parents=True, exist_ok=True)
            (target / ".harness/current/planning/PRODUCT_SCOPE.md").write_text("# Product Scope\n\nNo domain trace ids here.\n", encoding="utf-8")
            (target / ".harness/evidence/external-skills").mkdir(parents=True, exist_ok=True)
            (target / ".harness/evidence/external-skills/EXTERNAL_SKILL_RESOLUTION_R02_superpowers.json").write_text('{"skill_family":"superpowers","stage":"R02","used":true}\n', encoding="utf-8")
            (target / ".harness/current/gate").mkdir(parents=True, exist_ok=True)
            (target / ".harness/current/gate/GATE_STATE.json").write_text('{"gate_status":"open_for_exact_batch","open_work_unit_ids":[],"ready_to_start_counts":{"ready":0,"total":739}}\n', encoding="utf-8")
            result = validate(target, mode="installed-project")
            codes = {b["code"] for b in result["blockers"]}
            self.assertIn("doctor.read_set_forbidden_path", codes)
            self.assertIn("doctor.domain_trace_missing", codes)
            self.assertIn("doctor.superpowers_timing_violation", codes)
            self.assertIn("doctor.gate_ready_conflict", codes)


if __name__ == "__main__":
    unittest.main()
