import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class HarnessInstallerTests(unittest.TestCase):
    def test_installer_applies_harness_to_empty_project(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mptech"
            target.mkdir()

            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(source_root / "install-harness.ps1"),
                    "-TargetPath",
                    str(target),
                    "-SourcePath",
                    str(source_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertIn("harness:start", (target / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertTrue((target / ".harness" / "current" / "status" / "STATUS_KO.md").exists())
            self.assertNotIn(
                "PAC10",
                (target / ".harness" / "current" / "status" / "STATUS_KO.md").read_text(encoding="utf-8"),
            )
            self.assertTrue((target / "tools" / "harness-validator" / "harness_validator" / "final_release.py").exists())
            self.assertFalse((target / "_organized_harness_design").exists())
            record = json.loads(
                (target / ".harness" / "evidence" / "install" / "INSTALL_RECORD_V1_0.json").read_text(encoding="utf-8")
            )
            self.assertEqual(record["install_result"], "pass")
            self.assertEqual(record["release_tag"], "harness-v1.0.0")

    def test_installer_preserves_existing_agents_md_and_writes_backup(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"
            target.mkdir()
            (target / "AGENTS.md").write_text("# Existing instructions\n\nKeep this.\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(source_root / "install-harness.ps1"),
                    "-TargetPath",
                    str(target),
                    "-SourcePath",
                    str(source_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Keep this.", agents)
            self.assertIn("harness:start", agents)
            backups = list((target / ".harness" / "evidence" / "install" / "backups").glob("AGENTS.md.*.bak"))
            self.assertEqual(len(backups), 1)


if __name__ == "__main__":
    unittest.main()
