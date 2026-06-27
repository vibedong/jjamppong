import json
import os
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_RUNTIME_ROOT", SOURCE_ROOT)).resolve()

REQUIRED_RUNTIME_PATHS = [
    "AGENTS.md",
    "README.md",
    "install-harness.ps1",
    "harness.ps1",
    ".agents/skills/harness-planning-socrates/SKILL.md",
    ".harness/current/status/STATUS_KO.md",
    ".harness/current/START_HERE.md",
    ".harness/current/readsets/CURRENT_READ_SET.json",
    ".harness/current/source/SOURCE_IDENTITY.json",
    ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md",
    ".harness/runtime/schemas/shared-meaning-lock.schema.json",
    ".harness/runtime/schemas/research-direction.schema.json",
    ".harness/runtime/schemas/file-write-approval.schema.json",
    ".harness/runtime/schemas/read-audit-token-quality.schema.json",
    ".harness/runtime/schemas/test-target-class.schema.json",
    ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json",
    ".harness/improvement/BACKLOG.md",
    ".harness/improvement/BACKLOG.jsonl",
]

FORBIDDEN_RUNTIME_PATHS = [
    "tests",
    "tools",
    "docs",
    "_organized_harness_design",
    "PRIVATE_HARNESS_CONTEXT",
]


class RuntimeReleaseSurfaceTests(unittest.TestCase):
    def runtime_universe(self):
        return set(json.loads((ROOT / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json").read_text(encoding="utf-8"))["runtime_paths"])

    def test_required_runtime_files_exist(self):
        for rel in REQUIRED_RUNTIME_PATHS:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_forbidden_runtime_paths_are_absent_in_runtime_candidate(self):
        if ROOT == SOURCE_ROOT:
            self.skipTest("source tree intentionally contains source-only developer tests")
        for rel in FORBIDDEN_RUNTIME_PATHS:
            self.assertFalse((ROOT / rel).exists(), rel)

    def test_root_contains_only_runtime_surface_in_runtime_candidate(self):
        if ROOT == SOURCE_ROOT:
            self.skipTest("source tree intentionally contains source-only developer files")
        allowed = {
            ".agents",
            ".git",
            ".gitignore",
            ".harness",
            "AGENTS.md",
            "README.md",
            "install-harness.ps1",
            "harness.ps1",
        }
        actual = {path.name for path in ROOT.iterdir()}
        extra = actual - allowed
        self.assertEqual(extra, set())

    def test_recursive_file_set_matches_release_coverage_universe_in_runtime_candidate(self):
        if ROOT == SOURCE_ROOT:
            self.skipTest("source tree intentionally contains source-only developer files")
        actual = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git/" not in path.relative_to(ROOT).as_posix()
        }
        self.assertEqual(actual, self.runtime_universe())


if __name__ == "__main__":
    unittest.main()
