from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

CANONICAL_PATHS = [
    ".harness/current/status/STATUS_KO.md",
    ".harness/current/readsets/CURRENT_READ_SET.json",
    ".harness/current/source/SOURCE_IDENTITY.json",
    ".harness/current/START_HERE.md",
    ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md",
]

FORBIDDEN_PATH_LITERALS = [
    ".harness/manifests/CURRENT_READ_SET.json",
    ".harness/current/source_identity/SOURCE_IDENTITY.json",
    ".harness/current/navigation/START_HERE.md",
    "python -m unittest discover -s tools/harness-validator/tests",
    "tools/harness-validator/harness_validator",
]


class RuntimeContractPathTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_router_uses_only_canonical_paths(self):
        text = self.read("AGENTS.md")
        for required in CANONICAL_PATHS:
            self.assertIn(required, text)
        for forbidden in FORBIDDEN_PATH_LITERALS:
            self.assertNotIn(forbidden, text)

    def test_readme_uses_public_doctor_command(self):
        text = self.read("README.md")
        self.assertIn(".\\harness.ps1 doctor", text)
        self.assertNotIn("python -B -m unittest discover", text)
        self.assertNotIn("tools/harness-validator/tests", text)

    def test_installer_writes_canonical_paths(self):
        text = self.read("install-harness.ps1")
        normalized = text + "\n" + text.replace("/", "\\")
        for required in CANONICAL_PATHS:
            self.assertIn(required.replace("/", "\\"), normalized)
        for forbidden in FORBIDDEN_PATH_LITERALS[:3]:
            self.assertNotIn(forbidden, text)

    def test_current_read_set_is_file_only_and_small(self):
        payload = json.loads((ROOT / ".harness/current/readsets/CURRENT_READ_SET.json").read_text(encoding="utf-8"))
        total_bytes = 0
        for item in payload["paths"]:
            rel = item["path"]
            self.assertFalse(rel.endswith("/"), rel)
            self.assertNotIn("tools/", rel)
            self.assertNotIn("tests/", rel)
            self.assertNotIn("_organized_harness_design/", rel)
            target = ROOT / rel
            self.assertTrue(target.is_file(), rel)
            total_bytes += target.stat().st_size
        self.assertLessEqual(total_bytes, 20 * 1024)


if __name__ == "__main__":
    unittest.main()
