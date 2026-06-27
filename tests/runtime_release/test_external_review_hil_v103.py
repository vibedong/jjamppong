import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness-validator"))

from harness_validator.external_skills import resolve_external_skill, record_external_skill_resolution, record_review_result, record_token_quality_event, record_hil_candidate


class ExternalReviewHilTests(unittest.TestCase):
    def test_external_skill_resolution_fallback_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = record_external_skill_resolution(Path(tmp), "R02", "matt_pocock", "grill-me", "not_installed", None)
            payload = json.loads(path.read_text(encoding="utf-8"))
            for key in ("schema_version", "stage", "skill_family", "requested_skill", "resolved_status", "resolved_path", "resolved_path_style", "source_type", "allowed_stage", "used", "fallback_used", "fallback_reason", "vendored_copy_detected", "permission_boundary", "created_at_utc"):
                self.assertIn(key, payload)
            self.assertEqual(payload["resolved_status"], "not_installed")
            self.assertTrue(payload["fallback_used"])
            self.assertEqual(payload["fallback_reason"], "not_installed")

    def test_external_skill_resolver_policy_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / ".codex/skills/grill-me/SKILL.md"
            local.parent.mkdir(parents=True)
            local.write_text("---\nname: grill-me\n---\n", encoding="utf-8")
            resolved = resolve_external_skill(root, "R02", "matt_pocock", "grill-me", [root / ".codex/skills"])
            self.assertEqual(resolved["resolved_status"], "resolved")
            self.assertFalse(resolved["vendored_copy_detected"])

            wrong_stage = resolve_external_skill(root, "R02", "superpowers", "test-driven-development", [root / ".codex/plugins/cache/openai-curated-remote/superpowers/5.1.4/skills"])
            self.assertEqual(wrong_stage["resolved_status"], "wrong_stage")
            self.assertFalse(wrong_stage["used"])

            duplicate_a = root / ".codex/skills/gstack/plan-eng-review/SKILL.md"
            duplicate_b = root / ".agents/skills/plan-eng-review/SKILL.md"
            duplicate_a.parent.mkdir(parents=True)
            duplicate_b.parent.mkdir(parents=True)
            duplicate_a.write_text("---\nname: plan-eng-review\n---\n", encoding="utf-8")
            duplicate_b.write_text("---\nname: plan-eng-review\n---\n", encoding="utf-8")
            ambiguous = resolve_external_skill(root, "R07", "gstack", "plan-eng-review", [root / ".codex/skills/gstack", root / ".agents/skills"])
            self.assertEqual(ambiguous["resolved_status"], "ambiguous_duplicate")

            vendored = root / ".harness/external-skills/grill-me/SKILL.md"
            vendored.parent.mkdir(parents=True)
            vendored.write_text("---\nname: grill-me\n---\n", encoding="utf-8")
            blocked = resolve_external_skill(root, "R02", "matt_pocock", "grill-me", [root / ".harness/external-skills"])
            self.assertTrue(blocked["vendored_copy_detected"])
            self.assertEqual(blocked["resolved_status"], "vendored_copy_forbidden")

    def test_review_result_and_token_quality_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = record_review_result(Path(tmp), "R03", [], "pass")
            token = record_token_quality_event(Path(tmp), "R01", "simple_status_request", 210000, False, "read_set_too_large")
            self.assertTrue(review.is_file())
            review_payload = json.loads(review.read_text(encoding="utf-8"))
            for key in ("review_scope", "reviewer_type", "input_artifacts", "objective_rule_check_result", "findings", "overall_status", "must_fix_count", "creator_decision_needed_count", "backtrack_needed_count", "review_conflict_count"):
                self.assertIn(key, review_payload)
            payload = json.loads(token.read_text(encoding="utf-8"))
            for key in ("stage", "user_request_class", "approx_input_tokens", "approx_output_tokens", "files_read", "was_required_read", "overuse_suspected", "overuse_reason", "quality_gain", "followup_rework_avoided"):
                self.assertIn(key, payload)
            self.assertTrue(payload["overuse_suspected"])

    def test_hil_candidate_record_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = record_hil_candidate(Path(tmp), "R01", "token_overuse", "simple request read too much")
            payload = json.loads(path.read_text(encoding="utf-8"))
            for key in ("candidate_id", "source_stage", "source_event", "candidate_type", "user_project_impact", "harness_runtime_impact", "record_only", "requires_backtrack", "suggested_release", "status"):
                self.assertIn(key, payload)
            self.assertEqual(payload["status"], "record_only")
            self.assertTrue(payload["record_only"])
