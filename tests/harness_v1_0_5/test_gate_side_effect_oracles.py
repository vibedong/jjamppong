import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "harness_v1_0_5" / "fixtures"


def evaluate_gate(event: dict) -> dict:
    action = event.get("requested_action")
    if action == "web_search" and not event.get("user_approved_research_direction"):
        return {"allowed": False, "reason_code": "research_direction_gate_closed"}
    if action == "record_shared_meaning_lock" and not event.get("confirmation_is_explicit"):
        return {"allowed": False, "reason_code": "shared_meaning_confirmation_ambiguous"}
    if action == "write_file" and (event.get("file_write_gate") != "open" or not event.get("exact_write_paths")):
        return {"allowed": False, "reason_code": "file_write_gate_closed_or_missing_exact_paths"}
    if action == "advance_status_readset" and event.get("status_readset_advance_gate") != "open":
        return {"allowed": False, "reason_code": "status_readset_advance_gate_closed"}
    return {"allowed": True, "reason_code": "allowed"}


class GateSideEffectOracleTests(unittest.TestCase):
    def check_fixture(self, name: str):
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        actual = evaluate_gate(payload["event"])
        self.assertEqual(actual, payload["expected"], payload["case_id"])

    def test_research_requires_approved_direction(self):
        self.check_fixture("research_missing_approval.json")

    def test_short_confirmation_cannot_lock_shared_meaning(self):
        self.check_fixture("shared_meaning_ambiguous_short_reply.json")

    def test_file_write_requires_open_gate_and_exact_paths(self):
        self.check_fixture("file_write_missing_exact_list.json")

    def test_status_readset_advance_requires_gate(self):
        self.check_fixture("status_readset_unapproved_advance.json")

    def test_contract_names_all_gate_evidence_paths(self):
        contract = (ROOT / ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md").read_text(encoding="utf-8")
        for literal in [
            ".harness/current/planning/SHARED_MEANING_LOCK.json",
            ".harness/current/research/RESEARCH_DIRECTION_REQUEST.md",
            ".harness/current/research/RESEARCH_DIRECTION_APPROVAL.json",
            ".harness/current/evidence/FILE_WRITE_APPROVAL.json",
            ".harness/current/evidence/STATUS_READ_SET_ADVANCE_APPROVAL.json",
        ]:
            self.assertIn(literal, contract)


if __name__ == "__main__":
    unittest.main()
