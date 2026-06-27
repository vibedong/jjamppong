import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness-validator"))
INSTALLER = ROOT / "install-harness.ps1"


class InstallerPreviewMigrationTests(unittest.TestCase):
    def run_installer(self, target, mode="Preview", extra=None):
        args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INSTALLER), "-Mode", mode, "-TargetPath", str(target), "-SourcePath", str(ROOT)]
        if extra:
            args += extra
        return subprocess.run(args, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_preview_is_read_only_and_reports_git_secret_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=str(target), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (target / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            (target / ".env").write_text("API_KEY=abc\n", encoding="utf-8")
            result = self.run_installer(target, "Preview")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["mode"], "Preview")
            self.assertNotEqual(payload["target_git_state"], "not_checked")
            self.assertTrue(any(a["relative_path"] == "AGENTS.md" and a["merge_strategy"] == "harness_block_replace" for a in payload["file_actions"]))
            self.assertTrue(any(b["code"] == "installer.secret_candidate_present" for b in payload["hard_blockers"]))
            self.assertFalse((target / ".harness").exists())

    def test_install_then_update_same_version_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            first = self.run_installer(target, "Install")
            self.assertEqual(first.returncode, 0, first.stderr)
            second = self.run_installer(target, "Update")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already_up_to_date", second.stdout)

    def test_legacy_r06_update_creates_migration_evidence_without_stage_advance(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            first = self.run_installer(target, "Install")
            self.assertEqual(first.returncode, 0, first.stderr)
            status = target / ".harness/current/status/STATUS_KO.md"
            status.write_text("# Harness 상태\n\n- 현재 단계: R06 Development Plan\n", encoding="utf-8")
            read_set = target / ".harness/manifests/CURRENT_READ_SET.json"
            read_set.write_text('{"stage":"R06","paths":[]}\n', encoding="utf-8")
            update = self.run_installer(target, "Update")
            self.assertEqual(update.returncode, 0, update.stderr)
            migration = target / ".harness/evidence/migration/WORKFLOW_STAGE_SET_MIGRATION_NEEDED_V1_0_3.json"
            self.assertTrue(migration.is_file())
            payload = json.loads(migration.read_text(encoding="utf-8"))
            self.assertEqual(payload["from_stage_set_version"], "harness-stage-set-v1.0.2")
            self.assertEqual(payload["to_stage_set_version"], "harness-stage-set-v1.0.3")
            self.assertEqual(payload["detected_stage"], "R06")
            self.assertEqual(payload["required_user_action"], "review_migration")
            self.assertIn("Technical Architecture", status.read_text(encoding="utf-8"))
            self.assertIn("R06 Development Plan", status.read_text(encoding="utf-8"))

    def test_legacy_r07_and_r08_update_create_migration_evidence(self):
        for legacy_stage in ("R07 Work Units", "R08 Implementation Start Approval"):
            with self.subTest(legacy_stage=legacy_stage):
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / "project"
                    target.mkdir()
                    first = self.run_installer(target, "Install")
                    self.assertEqual(first.returncode, 0, first.stderr)
                    status = target / ".harness/current/status/STATUS_KO.md"
                    status.write_text(f"# Harness 상태\n\n- 현재 단계: {legacy_stage}\nImplementation Entry Gate: closed\n", encoding="utf-8")
                    read_set = target / ".harness/manifests/CURRENT_READ_SET.json"
                    read_set.write_text('{"stage":"' + legacy_stage[:3] + '","paths":[]}\n', encoding="utf-8")
                    update = self.run_installer(target, "Update")
                    self.assertEqual(update.returncode, 0, update.stderr)
                    migration = target / ".harness/evidence/migration/WORKFLOW_STAGE_SET_MIGRATION_NEEDED_V1_0_3.json"
                    self.assertTrue(migration.is_file())
                    payload = json.loads(migration.read_text(encoding="utf-8"))
                    self.assertEqual(payload["detected_stage"], legacy_stage[:3])
                    self.assertEqual(payload["required_user_action"], "review_migration")
                    self.assertIn(legacy_stage, status.read_text(encoding="utf-8"))
                    self.assertIn("Implementation Entry Gate: closed", status.read_text(encoding="utf-8"))
                    self.assertIn("Stage set version: harness-stage-set-v1.0.3", status.read_text(encoding="utf-8"))
                    read_set_payload = json.loads(read_set.read_text(encoding="utf-8"))
                    self.assertEqual(read_set_payload["stage_set_version"], "harness-stage-set-v1.0.3")
                    self.assertTrue(read_set_payload["paths"])

    def test_same_version_update_repairs_legacy_stage_set_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            first = self.run_installer(target, "Install")
            self.assertEqual(first.returncode, 0, first.stderr)
            status = target / ".harness/current/status/STATUS_KO.md"
            read_set = target / ".harness/manifests/CURRENT_READ_SET.json"
            status.write_text("# Harness 상태\n\n- 현재 단계: R07 Work Units\nImplementation Entry Gate: closed\n", encoding="utf-8")
            read_set.write_text('{"stage":"R07","paths":[]}\n', encoding="utf-8")
            update = self.run_installer(target, "Update")
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertIn("already_up_to_date", update.stdout)
            self.assertIn("Stage set version: harness-stage-set-v1.0.3", status.read_text(encoding="utf-8"))
            read_set_payload = json.loads(read_set.read_text(encoding="utf-8"))
            self.assertEqual(read_set_payload["stage"], "R07")
            self.assertEqual(read_set_payload["stage_set_version"], "harness-stage-set-v1.0.3")
            doctor = subprocess.run(
                ["python", "tools/harness-validator/run-doctor.py", "--mode", "installed-project", str(target)],
                cwd=str(target),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)

    def test_install_writes_git_baseline_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=str(target), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result = self.run_installer(target, "Install")
            self.assertEqual(result.returncode, 0, result.stderr)
            records = list((target / ".harness/evidence/git").glob("GIT_BASELINE_RECORD_*.json"))
            self.assertEqual(len(records), 1)
            payload = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertIn(payload["baseline_commit_status"], ("created", "skipped_no_git_identity", "skipped_user_declined", "remote_unverified", "verified"))
            self.assertIn("remote_push_verified", payload)

    def test_non_git_install_records_git_init_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            result = self.run_installer(target, "Install")
            self.assertEqual(result.returncode, 0, result.stderr)
            record = next((target / ".harness/evidence/git").glob("GIT_BASELINE_RECORD_*.json"))
            payload = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(payload["baseline_commit_status"], "not_required")
            self.assertEqual(payload["next_required_action"], "run_git_init_or_confirm_non_git")

    def test_install_records_dirty_and_remote_missing_git_baseline_edge_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=str(target), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (target / "existing.txt").write_text("dirty\n", encoding="utf-8")
            result = self.run_installer(target, "Install")
            self.assertEqual(result.returncode, 0, result.stderr)
            record = next((target / ".harness/evidence/git").glob("GIT_BASELINE_RECORD_*.json"))
            payload = json.loads(record.read_text(encoding="utf-8"))
            self.assertIn("existing.txt", payload["dirty_files_before_apply"])
            self.assertFalse(payload["remote_push_verified"])
            self.assertIn(payload["baseline_commit_status"], ("skipped_no_git_identity", "skipped_user_declined", "remote_unverified", "failed"))
            self.assertEqual(payload["next_required_action"], "verify_remote_before_implementation_entry")

    def test_github_shorthand_update_preserves_state_and_writes_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            first = self.run_installer(target, "Install", ["-ReleaseUrl", "github.com/vibedong/jjamppong/releases/latest"])
            self.assertEqual(first.returncode, 0, first.stderr)
            status = target / ".harness/current/status/STATUS_KO.md"
            status.write_text("# Harness 상태\n\n- 현재 단계: R03 Product Scope\n", encoding="utf-8")
            update = self.run_installer(target, "Update", ["-ReleaseUrl", "github.com/vibedong/jjamppong/releases/latest"])
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertIn("R03 Product Scope", status.read_text(encoding="utf-8"))
            identity = target / ".harness/evidence/source-identity/HARNESS_SOURCE_IDENTITY.json"
            self.assertTrue(identity.is_file())
            payload = json.loads(identity.read_text(encoding="utf-8"))
            self.assertEqual(payload["normalized_release_url"], "https://github.com/vibedong/jjamppong/releases/latest")
            self.assertEqual(payload["resolution_mode"], "github_release_url")


if __name__ == "__main__":
    unittest.main()
