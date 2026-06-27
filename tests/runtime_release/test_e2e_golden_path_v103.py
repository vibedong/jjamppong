import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class InstalledWorkflowTests(unittest.TestCase):
    def install(self, target):
        return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Install", "-TargetPath", str(target), "-SourcePath", str(ROOT)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_install_starts_at_r01_and_forbids_product_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            result = self.install(target)
            self.assertEqual(result.returncode, 0, result.stderr)
            status = (target / ".harness/current/status/STATUS_KO.md").read_text(encoding="utf-8")
            self.assertIn("Stage set version: harness-stage-set-v1.0.3", status)
            self.assertIn("Current stage: R01 Product Goal", status)
            self.assertIn("Implementation Entry Gate: closed", status)
            read_set = json.loads((target / ".harness/manifests/CURRENT_READ_SET.json").read_text(encoding="utf-8"))
            self.assertEqual(read_set["stage"], "R01")
            self.assertEqual(read_set["stage_set_version"], "harness-stage-set-v1.0.3")
            self.assertFalse((target / "src").exists())

    def test_runtime_docs_explain_github_link_install_update(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://github.com/vibedong/jjamppong/releases/latest 하네스 설치해줘", readme)
        self.assertIn("https://github.com/vibedong/jjamppong/releases/latest 하네스 업데이트해줘", readme)
        rules = (ROOT / ".harness/runtime/WORKFLOW_RULES_KO.md").read_text(encoding="utf-8")
        self.assertIn("제품 코드", rules)
        self.assertIn("R09 Implementation Entry", rules)

    def test_e2e_scenario_creates_r01_to_r09_without_product_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            install = self.install(target)
            self.assertEqual(install.returncode, 0, install.stderr)
            result = subprocess.run(["python", str(target / "tools/harness-validator/run-e2e-scenario.py"), str(target), "--scenario", "repair-shop-planning-r01-r09"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["overall_status"], "pass")
            for key in ("schema_version", "command", "overall_status", "blocker_count", "blockers", "warnings", "exit_code", "checked_at_utc", "korean_summary", "scenario_id", "transcript_path", "stage_transitions", "created_artifacts", "token_quality_events", "implementation_started"):
                self.assertIn(key, payload)
            self.assertIn("implementation_start_possible", payload["korean_summary"])
            self.assertEqual(payload["implementation_started"], False)
            self.assertEqual(payload["stage_transitions"][-1]["stage"], "R09")
            self.assertEqual(payload["user_input"], "나는 소규모 제조/수리 업체용 작업 접수·진행 상태 관리 웹앱을 만들고 싶어. 고객이 작업을 접수하고, 직원이 상태를 바꾸고, 메모를 남기고, 완료 기록을 볼 수 있으면 돼. Harness 기준으로 처음부터 진행해줘.")
            self.assertEqual(len(payload["stage_transitions"]), 9)
            self.assertEqual(len(payload["read_set_changes"]), 9)
            self.assertTrue(payload["implementation_blocked_before_gate"])
            self.assertFalse((target / "src").exists())
            self.assertTrue((target / ".harness/evidence/external-skills").is_dir())
            self.assertTrue((target / ".harness/evidence/reviews").is_dir())
            self.assertTrue((target / ".harness/evidence/token-quality").is_dir())
