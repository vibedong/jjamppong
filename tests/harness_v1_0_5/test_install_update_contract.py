import hashlib
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_installer(target: Path, *extra: str):
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


def run_installer_from_release(target: Path, github_url: str, zip_path: Path, manifest_path: Path, *extra: str):
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
            "-GitHubUrl",
            github_url,
            "-ReleaseAssetPath",
            str(zip_path),
            "-ReleaseManifestPath",
            str(manifest_path),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def tree_hash(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_artifact_hash(root: Path) -> str:
    coverage = json.loads((root / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json").read_text(encoding="utf-8"))
    excluded = {
        ".harness/current/source/SOURCE_IDENTITY.json",
        ".harness/current/status/STATUS_KO.md",
        ".harness/current/readsets/CURRENT_READ_SET.json",
        ".harness/improvement/BACKLOG.md",
        ".harness/improvement/BACKLOG.jsonl",
    }
    rows = []
    for rel in sorted(coverage["runtime_paths"]):
        if rel in excluded:
            continue
        rows.append(f"{rel}={file_sha256(root / rel)}")
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def create_fake_release_asset(tmp: Path, repository: str = "https://github.com/vibedong/jjamppong"):
    source = tmp / "asset-source"
    source.mkdir()
    coverage = json.loads((ROOT / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json").read_text(encoding="utf-8"))
    for rel in coverage["runtime_paths"]:
        src = ROOT / rel
        dst = source / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    zip_path = tmp / "harness-runtime-v1.0.6.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(source).as_posix())
    manifest = {
        "artifact_id": "harness.release_manifest",
        "artifact_version": "1.0.6",
        "source_repository": repository,
        "release_tag": "harness-v1.0.6",
        "immutable_commit": "0123456789abcdef0123456789abcdef01234567",
        "release_asset_name": "harness-runtime-v1.0.6.zip",
        "release_asset_sha256": file_sha256(zip_path),
        "runtime_artifact_sha256": runtime_artifact_hash(source),
        "runtime_paths_sha256": coverage["runtime_paths_sha256"],
    }
    manifest_path = tmp / "HARNESS_RELEASE_MANIFEST_V1_0_6.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return zip_path, manifest_path


class ReleaseAssetHandler(http.server.BaseHTTPRequestHandler):
    zip_path: Path
    manifest_path: Path
    tag_name = "harness-v1.0.6"

    def do_GET(self):
        if self.path == "/repos/vibedong/jjamppong/releases/latest":
            body = json.dumps(
                {
                    "tag_name": self.tag_name,
                    "assets": [
                        {
                            "name": "harness-runtime-v1.0.6.zip",
                            "browser_download_url": f"http://127.0.0.1:{self.server.server_port}/harness-runtime-v1.0.6.zip",
                        },
                        {
                            "name": "HARNESS_RELEASE_MANIFEST_V1_0_6.json",
                            "browser_download_url": f"http://127.0.0.1:{self.server.server_port}/HARNESS_RELEASE_MANIFEST_V1_0_6.json",
                        },
                    ],
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/harness-runtime-v1.0.6.zip":
            body = self.zip_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/HARNESS_RELEASE_MANIFEST_V1_0_6.json":
            body = self.manifest_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, format, *args):
        return


class LocalReleaseServer:
    def __init__(self, zip_path: Path, manifest_path: Path):
        handler = type(
            "BoundReleaseAssetHandler",
            (ReleaseAssetHandler,),
            {"zip_path": zip_path, "manifest_path": manifest_path},
        )
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def api_base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()


class InstallUpdateContractTests(unittest.TestCase):
    def test_install_writes_canonical_paths_and_public_doctor(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fresh"
            target.mkdir()
            completed = run_installer(target)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            universe = json.loads((ROOT / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json").read_text(encoding="utf-8"))
            for rel in universe["runtime_paths"]:
                self.assertTrue((target / rel).exists(), rel)
            doctor = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target / "harness.ps1"), "doctor"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr + doctor.stdout)

    def test_second_bare_install_is_write_free_update_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"
            target.mkdir()
            first = run_installer(target)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            status = target / ".harness/current/status/STATUS_KO.md"
            status.write_text("# Harness 상태\n\n사용자 기획 진행 중\n", encoding="utf-8")
            before_hash = tree_hash(target)
            second = run_installer(target)
            after_hash = tree_hash(target)
            self.assertEqual(second.returncode, 2, second.stderr + second.stdout)
            self.assertEqual(before_hash, after_hash)
            self.assertIn("update_required", second.stdout)
            self.assertIn("-Update", second.stdout)
            self.assertIn("사용자 기획 진행 중", status.read_text(encoding="utf-8"))
            update_record = target / ".harness/evidence/install/UPDATE_RECORD_V1_0.json"
            self.assertFalse(update_record.exists())

    def test_update_preserves_current_planning_and_readset(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "planning"
            target.mkdir()
            first = run_installer(target)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            planning = target / ".harness/current/planning/SHARED_MEANING_LOCK.json"
            planning.parent.mkdir(parents=True, exist_ok=True)
            planning.write_text('{"user_confirmation":{"confirmed":true}}\n', encoding="utf-8")
            readset = target / ".harness/current/readsets/CURRENT_READ_SET.json"
            before = readset.read_text(encoding="utf-8")
            second = run_installer(target, "-Update")
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            self.assertEqual(planning.read_text(encoding="utf-8"), '{"user_confirmation":{"confirmed":true}}\n')
            self.assertEqual(readset.read_text(encoding="utf-8"), before)
            update_record = target / ".harness/evidence/install/UPDATE_RECORD_V1_0.json"
            self.assertTrue(update_record.exists())
            identity = json.loads((target / ".harness/current/source/SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
            self.assertTrue(identity["immutable_commit"])
            self.assertTrue(identity["artifact_sha256"])

    def test_github_url_install_uses_release_manifest_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path)
            target = tmp_path / "github-link-target"
            target.mkdir()
            completed = run_installer_from_release(
                target,
                "https://github.com/vibedong/jjamppong/releases/tag/harness-v1.0.6",
                zip_path,
                manifest_path,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            identity = json.loads((target / ".harness/current/source/SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
            self.assertEqual(identity["source_repository"], "https://github.com/vibedong/jjamppong")
            self.assertEqual(identity["release_tag"], "harness-v1.0.6")
            self.assertEqual(identity["immutable_commit"], "0123456789abcdef0123456789abcdef01234567")
            self.assertEqual(identity["artifact_sha256"], json.loads(manifest_path.read_text(encoding="utf-8"))["runtime_artifact_sha256"])

    def test_latest_github_url_records_manifest_concrete_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path)
            target = tmp_path / "latest-link-target"
            target.mkdir()
            completed = run_installer_from_release(
                target,
                "https://github.com/vibedong/jjamppong/releases/latest",
                zip_path,
                manifest_path,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            identity = json.loads((target / ".harness/current/source/SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
            self.assertEqual(identity["release_tag"], "harness-v1.0.6")
            self.assertNotEqual(identity["release_tag"], "latest")

    def test_github_url_without_sidecar_paths_downloads_release_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path)
            target = tmp_path / "downloaded-latest-target"
            target.mkdir()
            with LocalReleaseServer(zip_path, manifest_path) as server:
                env = os.environ.copy()
                env["HARNESS_GITHUB_API_BASE_URL"] = server.api_base
                completed = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ROOT / "install-harness.ps1"),
                        "-TargetPath",
                        str(target),
                        "-GitHubUrl",
                        "https://github.com/vibedong/jjamppong/releases/latest",
                    ],
                    capture_output=True,
                    text=True,
                    env=env,
                )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            identity = json.loads((target / ".harness/current/source/SOURCE_IDENTITY.json").read_text(encoding="utf-8"))
            self.assertEqual(identity["release_tag"], "harness-v1.0.6")
            self.assertEqual(identity["source_repository"], "https://github.com/vibedong/jjamppong")

    def test_github_url_repository_must_match_release_manifest_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path, repository="https://github.com/other/repo")
            target = tmp_path / "repo-mismatch-target"
            target.mkdir()
            completed = run_installer_from_release(
                target,
                "https://github.com/vibedong/jjamppong/releases/tag/harness-v1.0.6",
                zip_path,
                manifest_path,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("repository", completed.stderr.lower() + completed.stdout.lower())

    def test_github_url_tag_must_match_release_manifest_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path)
            target = tmp_path / "tag-mismatch-target"
            target.mkdir()
            completed = run_installer_from_release(
                target,
                "https://github.com/vibedong/jjamppong/releases/tag/harness-v9.9.9",
                zip_path,
                manifest_path,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("tag", completed.stderr.lower() + completed.stdout.lower())

    def test_github_url_update_preserves_mutable_state_and_doctor_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path, manifest_path = create_fake_release_asset(tmp_path)
            target = tmp_path / "github-update-target"
            target.mkdir()
            first = run_installer(target)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            status = target / ".harness/current/status/STATUS_KO.md"
            status.write_text("# Harness 현재 상태\n\n사용자 기획 진행 중\n", encoding="utf-8")
            backlog = target / ".harness/improvement/BACKLOG.jsonl"
            backlog.write_text('{"candidate_id":"IMP-LOCAL-001"}\n', encoding="utf-8")
            update = run_installer_from_release(
                target,
                "https://github.com/vibedong/jjamppong/releases/latest",
                zip_path,
                manifest_path,
                "-Update",
            )
            self.assertEqual(update.returncode, 0, update.stderr + update.stdout)
            self.assertIn("사용자 기획 진행 중", status.read_text(encoding="utf-8"))
            self.assertIn("IMP-LOCAL-001", backlog.read_text(encoding="utf-8"))
            doctor = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target / "harness.ps1"), "doctor"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr + doctor.stdout)


if __name__ == "__main__":
    unittest.main()
