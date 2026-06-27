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
