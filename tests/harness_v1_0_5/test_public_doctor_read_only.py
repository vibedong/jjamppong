import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_installer(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "install-harness.ps1"),
            "-TargetPath",
            str(target),
            "-SourcePath",
            str(ROOT),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def run_doctor(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "harness.ps1"), "doctor", *extra],
        cwd=root,
        capture_output=True,
        text=True,
    )


def file_snapshot(root: Path) -> dict[str, tuple[int, int]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            snapshot[rel] = (path.stat().st_size, path.stat().st_mtime_ns)
    return snapshot


class PublicDoctorReadOnlyTests(unittest.TestCase):
    def test_public_doctor_passes_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "installed"
            target.mkdir()
            installed = run_installer(target)
            self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
            before = file_snapshot(target)
            completed = run_doctor(target)
            after = file_snapshot(target)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["overall_status"], "pass")
            self.assertEqual(payload["public_command"], ".\\harness.ps1 doctor")
            self.assertTrue(payload["read_only"])
            self.assertEqual(before, after)

    def test_installed_mode_allows_user_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "with-user-files"
            target.mkdir()
            installed = run_installer(target)
            self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
            (target / "app.py").write_text("print('user product file')\n", encoding="utf-8")
            (target / "docs").mkdir()
            (target / "docs/NOTES.md").write_text("# user docs\n", encoding="utf-8")
            completed = run_doctor(target)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_release_candidate_mode_rejects_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "candidate"
            target.mkdir()
            installed = run_installer(target)
            self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
            (target / "tests").mkdir()
            (target / "tests/extra.py").write_text("# not runtime\n", encoding="utf-8")
            completed = run_doctor(target, "-Mode", "release_candidate")
            self.assertNotEqual(completed.returncode, 0)
            payload = json.loads(completed.stdout)
            self.assertIn("tests/extra.py", payload["release_surface_violations"])

    def test_release_candidate_mode_ignores_git_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "git-worktree-candidate"
            target.mkdir()
            coverage = json.loads((ROOT / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json").read_text(encoding="utf-8"))
            for rel in coverage["runtime_paths"]:
                src = ROOT / rel
                dst = target / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            (target / ".git").write_text("gitdir: ../.git/worktrees/git-worktree-candidate\n", encoding="utf-8")
            completed = run_doctor(target, "-Mode", "release_candidate")
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
