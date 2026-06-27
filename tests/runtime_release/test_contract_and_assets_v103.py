import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness-validator"))


class ContractAndAssetsTests(unittest.TestCase):
    def test_runtime_contract_v103(self):
        from harness_validator import runtime_contract as c

        self.assertEqual(c.HARNESS_RUNTIME_VERSION, "1.0.4")
        self.assertEqual(c.STAGE_SET_VERSION, "harness-stage-set-v1.0.3")
        self.assertEqual(tuple(c.PLANNING_STAGE_FILES), ("R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"))
        self.assertEqual(c.PLANNING_STAGE_FILES["R06"], ".harness/current/planning/TECHNICAL_ARCHITECTURE.md")
        self.assertEqual(c.PLANNING_STAGE_FILES["R10"], ".harness/current/implementation/IMPLEMENTATION_EXECUTION_STATUS.md")

    def test_all_stage_contracts_templates_and_skills_exist(self):
        from harness_validator.stage_assets import STAGES

        self.assertEqual(len(STAGES), 10)
        for stage in STAGES:
            self.assertTrue((ROOT / ".harness/definitions/stage-contracts" / stage["contract_file"]).is_file(), stage["stage_id"])
            self.assertTrue((ROOT / ".harness/definitions/templates" / stage["template_file"]).is_file(), stage["stage_id"])
            skill_path = ROOT / ".agents/skills" / stage["skill_dir"] / "SKILL.md"
            self.assertTrue(skill_path.is_file(), stage["stage_id"])
            contract = (ROOT / ".harness/definitions/stage-contracts" / stage["contract_file"]).read_text(encoding="utf-8")
            template = (ROOT / ".harness/definitions/templates" / stage["template_file"]).read_text(encoding="utf-8")
            for section_id in stage["section_ids"]:
                self.assertIn(f"section_id: {section_id}", contract)
                self.assertIn(f"<!-- section_id: {section_id} -->", template)
            for required_label in ("required_inputs:", "required_artifacts:", "required_evidence:", "external_skill_policy:", "review_policy:", "approval_rule:", "read_set_update_rule:", "transition_rule:", "doctor_checks:"):
                self.assertIn(required_label, contract, stage["stage_id"])

    def test_external_skill_catalog_exists(self):
        path = ROOT / ".harness/definitions/external-skills/ALLOWED_EXTERNAL_SKILL_CATALOG.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["catalog_version"], "1.0")
        self.assertEqual(payload["resolver_order"], ["codex_plugin", "local_codex_skill", "github_installed_skill", "harness_native_fallback"])
        self.assertIn("superpowers", payload["default_excluded_skill_families"])


if __name__ == "__main__":
    unittest.main()
