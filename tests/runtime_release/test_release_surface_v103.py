import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("_organized_harness_design", "GPT_PRO", "HARNESS_1_0_RUNTIME_SIMULATION_AUDIT")


class ReleaseSurfaceTests(unittest.TestCase):
    def test_source_tree_has_no_forbidden_runtime_markers_outside_tests_and_docs(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith("tests/") or rel.startswith("docs/"):
                continue
            for marker in FORBIDDEN:
                self.assertNotIn(marker, rel)

    def test_installer_normalizes_github_shorthand(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Preview", "-TargetPath", str(target), "-SourcePath", str(ROOT), "-ReleaseUrl", "github.com/vibedong/jjamppong/releases/latest"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("harness-v1.0.4", result.stdout)

    def test_update_accepts_github_shorthand_without_state_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            install = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Install", "-TargetPath", str(target), "-SourcePath", str(ROOT), "-ReleaseUrl", "github.com/vibedong/jjamppong/releases/latest"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(install.returncode, 0, install.stderr)
            status = target / ".harness/current/status/STATUS_KO.md"
            before = status.read_text(encoding="utf-8")
            update = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Update", "-TargetPath", str(target), "-SourcePath", str(ROOT), "-ReleaseUrl", "github.com/vibedong/jjamppong/releases/latest"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertIn("already_up_to_date", update.stdout)
            self.assertEqual(status.read_text(encoding="utf-8"), before)

    def test_installer_does_not_copy_python_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install-harness.ps1"), "-Mode", "Install", "-TargetPath", str(target), "-SourcePath", str(ROOT)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            for path in target.rglob("*"):
                rel = path.relative_to(target).as_posix()
                self.assertNotIn("__pycache__", rel)
                self.assertFalse(rel.endswith(".pyc"), rel)
