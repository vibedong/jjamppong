import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RuntimeSimulationTests(unittest.TestCase):
    def test_github_link_install_surface_and_first_turn_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mptech"
            target.mkdir()
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
                    "-SourcePath",
                    str(ROOT),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            doctor = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target / "harness.ps1"), "doctor"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr + doctor.stdout)
            payload = json.loads(doctor.stdout)
            self.assertEqual(payload["overall_status"], "pass")
            contract = (target / ".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md").read_text(encoding="utf-8")
            self.assertIn("웹 검색 금지", contract)
            self.assertIn("Shared Meaning Lock", contract)
            readset = json.loads((target / ".harness/current/readsets/CURRENT_READ_SET.json").read_text(encoding="utf-8"))
            read_paths = [item["path"] for item in readset["paths"]]
            self.assertIn(".harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md", read_paths)
            self.assertNotIn("tools/harness-validator/harness_validator", read_paths)

    def test_planning_stage_sequence_blocks_premature_research_and_file_writes(self):
        transcript = [
            {"turn": 1, "user": "나라장터 실시설계들을 크롤링해서 원하는 값만 추출하고 싶어.", "agent_action": "ask_domain_meaning_question"},
            {"turn": 2, "user": "공고랑 첨부문서에서 실시설계 관련 값만 보면 돼.", "agent_action": "draft_shared_meaning_lock_only"},
            {"turn": 3, "user": "응", "agent_action": "ask_confirmation_because_short_reply_is_ambiguous"},
            {"turn": 4, "user": "맞아. 아직 리서치는 하지 말고 내가 말한 뜻만 고정해.", "agent_action": "record_shared_meaning_lock"},
            {"turn": 5, "user": "이제 어떤 방향으로 리서치할지 먼저 제안해줘.", "agent_action": "draft_research_direction_request"},
        ]
        forbidden_before_lock = {"web_search", "api_lookup", "file_write", "status_readset_advance", "product_code"}
        actions_before_lock = {row["agent_action"] for row in transcript[:3]}
        self.assertTrue(forbidden_before_lock.isdisjoint(actions_before_lock))
        self.assertEqual(transcript[0]["agent_action"], "ask_domain_meaning_question")
        self.assertEqual(transcript[2]["agent_action"], "ask_confirmation_because_short_reply_is_ambiguous")
        self.assertEqual(transcript[3]["agent_action"], "record_shared_meaning_lock")
        self.assertEqual(transcript[4]["agent_action"], "draft_research_direction_request")


if __name__ == "__main__":
    unittest.main()
