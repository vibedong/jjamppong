import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "harness_v1_0_5" / "fixtures"


def evaluate_response(text: str) -> dict[str, bool]:
    no_research = "리서치" in text and ("하지 않" in text or "전에는" in text)
    chooses_external_or_technical_direction = any(
        term in text
        for term in [
            "검색해서",
            "공식 자료 확인",
            "외부 자료 확인",
            "외부 사이트",
            "문서 구조",
            "수집 경로",
            "자동 수집 방식",
            "기술적으로는",
            "기술부터",
            "프레임워크",
            "데이터베이스",
            "출력 형식은",
        ]
    )
    question_count = text.count("?") + text.count("나요") + text.count("인가요")
    open_ended_meaning_question = any(
        term in text
        for term in ["무엇을 뜻하나요", "어떤 의미", "어떤 업무", "판정 기준은 무엇", "어떤 상황", "누가 어떤 결과"]
    )
    proposes_fields_or_scope = any(term in text for term in ["날짜", "금액", "담당자", "상태", "최근 30일", "엑셀", "CSV"])
    leading_question = any(term in text for term in ["하면 되죠", "맞죠", "뽑으면 되죠", "확정하면 될까요", "우선으로 할까요", "기준으로"])
    return {
        "mentions_no_research": no_research,
        "asks_one_meaning_axis": question_count >= 1 and question_count <= 2 and open_ended_meaning_question and not leading_question and not proposes_fields_or_scope,
        "does_not_choose_external_or_technical_method": not chooses_external_or_technical_direction,
    }


class PlanningStageOracleTests(unittest.TestCase):
    def check_fixture(self, name: str):
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        actual = evaluate_response(payload["agent_response"])
        self.assertEqual(actual, payload["expected"], payload["case_id"])

    def test_positive_socrates_response_passes(self):
        self.check_fixture("planning_positive.json")

    def test_leading_question_response_fails_oracle(self):
        self.check_fixture("planning_negative_leading_question.json")

    def test_technical_premise_response_fails_oracle(self):
        self.check_fixture("planning_negative_technical_premise.json")

    def test_field_scope_proposal_response_fails_oracle(self):
        self.check_fixture("planning_negative_field_scope_proposal.json")

    def test_external_method_choice_response_fails_oracle(self):
        self.check_fixture("planning_negative_external_method_choice.json")

    def test_contract_contains_required_forbidden_actions(self):
        contract = (ROOT / ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md").read_text(encoding="utf-8")
        for literal in [
            "외부 검색 금지",
            "외부 자료·도구·서비스 문서 확인 금지",
            "기술·수집·출력 방식 선택 금지",
            "파일 작성 금지",
            "status/read set 변경 금지",
            "Socrates persona",
            "grill-me",
            "Shared Meaning Lock",
            "Research Direction Gate",
        ]:
            self.assertIn(literal, contract)

    def test_runtime_planning_surfaces_do_not_hardcode_previous_incident(self):
        surfaces = [
            ROOT / "AGENTS.md",
            ROOT / ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md",
            ROOT / ".agents/skills/harness-planning-socrates/SKILL.md",
        ]
        forbidden_literals = [
            "나라장터",
            "실시설계",
            "공공데이터",
            "크롤",
            "crawler",
            "API lookup",
            "API 문서",
            "Do not choose API",
        ]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for literal in forbidden_literals:
                self.assertNotIn(literal, text, f"{path} must not hardcode {literal!r}")


if __name__ == "__main__":
    unittest.main()
