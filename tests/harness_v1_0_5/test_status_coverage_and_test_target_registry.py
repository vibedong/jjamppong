import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "harness_v1_0_5" / "fixtures"
RUNTIME_UNIVERSE = ROOT / ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json"
TEST_TARGET_SCHEMA = ROOT / ".harness/runtime/schemas/test-target-class.schema.json"

FORBIDDEN_PATH_PREFIXES = (
    "tests/",
    "tools/",
    "docs/",
    "_organized_harness_design/",
    "PRIVATE_HARNESS_CONTEXT/",
)

REQUIRED_TEST_TARGET_CLASSES = {
    "oracle_fixture",
    "schema_validation",
    "public_doctor",
    "install_update",
    "runtime_release_surface",
    "runtime_simulation",
    "manual_review",
}


def paths_sha256(paths: list[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(paths)) + "\n").encode("utf-8")).hexdigest()


def validate_runtime_paths(paths: list[str]) -> tuple[bool, str]:
    for rel in paths:
        if rel.endswith("/") or rel.startswith(FORBIDDEN_PATH_PREFIXES):
            return False, "release_runtime_path_forbidden"
    return True, "valid"


def validate_test_target(target: dict) -> tuple[bool, str]:
    test_target_id = target.get("test_target_id", "")
    if not re.match(r"^TT-[A-Z0-9]+-[0-9]{3}$", test_target_id):
        return False, "test_target_id_must_be_stable_prefixed_id"
    if target.get("class") not in REQUIRED_TEST_TARGET_CLASSES:
        return False, "test_target_class_not_allowed"
    return True, "valid"


class StatusCoverageAndTestTargetRegistryTests(unittest.TestCase):
    def test_release_coverage_universe_exists_and_uses_canonical_hash(self):
        payload = json.loads(RUNTIME_UNIVERSE.read_text(encoding="utf-8"))
        self.assertEqual(payload["artifact_id"], "harness.release_coverage_universe")
        self.assertEqual(payload["artifact_version"], "1.0.6")
        self.assertEqual(payload["runtime_paths_sha256"], paths_sha256(payload["runtime_paths"]))
        valid, reason = validate_runtime_paths(payload["runtime_paths"])
        self.assertTrue(valid, reason)
        for rel in payload["runtime_paths"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_release_coverage_fixture_rejects_forbidden_paths(self):
        payload = json.loads((FIXTURES / "release_coverage_extra_id.json").read_text(encoding="utf-8"))
        valid, reason = validate_runtime_paths(payload["runtime_paths"])
        self.assertEqual({"valid": valid, "reason_code": reason}, payload["expected"])

    def test_test_target_class_schema_contains_canonical_classes(self):
        schema = json.loads(TEST_TARGET_SCHEMA.read_text(encoding="utf-8"))
        enum = set(schema["properties"]["class"]["enum"])
        self.assertEqual(enum, REQUIRED_TEST_TARGET_CLASSES)

    def test_invalid_test_target_alias_fixture_is_rejected(self):
        payload = json.loads((FIXTURES / "test_target_invalid_alias.json").read_text(encoding="utf-8"))
        valid, reason = validate_test_target(payload["target"])
        self.assertEqual({"valid": valid, "reason_code": reason}, payload["expected"])


if __name__ == "__main__":
    unittest.main()
