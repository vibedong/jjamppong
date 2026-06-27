from pathlib import Path

from .external_skills import record_external_skill_resolution, record_review_result, record_token_quality_event
from .jsonio import write_canonical_json
from .stage_assets import STAGES
from .state_model import utc_now


SCENARIO_ID = "repair-shop-planning-r01-r09"
USER_INPUT = "나는 소규모 제조/수리 업체용 작업 접수·진행 상태 관리 웹앱을 만들고 싶어. 고객이 작업을 접수하고, 직원이 상태를 바꾸고, 메모를 남기고, 완료 기록을 볼 수 있으면 돼. Harness 기준으로 처음부터 진행해줘."


STAGE_ARTIFACTS = [
    ("R01", ".harness/current/planning/PRODUCT_GOAL_INTAKE.md", "# Product Goal\n\n사용자 입력: {user_input}\n\n확인 질문:\n- 고객 접수는 로그인 없이 가능한가?\n- 직원 상태 변경 권한은 누가 가지는가?\n\n성공 기준:\n- 작업 접수부터 완료 기록까지 추적한다.\n"),
    ("R02", ".harness/current/planning/DOMAIN_FOUNDATION.md", "# Domain Foundation\n\nTERM-001 작업 접수\nTERM-002 고객\nTERM-003 직원\nTERM-004 상태\nOBJ-001 메모\nOBJ-002 완료 기록\n\n업무 규칙:\n- 직원은 작업 상태를 변경한다.\n"),
    ("R03", ".harness/current/planning/PRODUCT_SCOPE.md", "# Product Scope\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nIncluded scope:\n- 고객 작업 접수\n- 직원 상태 변경\n- 메모 기록\n- 완료 기록 조회\n\nExcluded scope:\n- 결제\n- 재고 관리\n"),
    ("R04", ".harness/current/planning/USER_EXPERIENCE.md", "# User Experience\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nWorkflows:\n- 고객이 작업을 접수한다.\n- 직원이 상태를 변경하고 메모를 남긴다.\n\nState visibility:\n- 접수, 진행, 완료 상태가 보인다.\n"),
    ("R05", ".harness/current/planning/BEHAVIOR_SPECIFICATION.md", "# Behavior Specification\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nCommands:\n- submit_job_request\n- change_job_status\n- add_job_note\n\nQueries:\n- list_job_status\n- view_completion_record\n\nEvents:\n- job_requested\n- job_status_changed\n- job_note_added\n- job_completed\n\nStates:\n- received\n- in_progress\n- complete\n\nPolicies:\n- 직원만 상태를 변경한다.\n"),
    ("R06", ".harness/current/planning/TECHNICAL_ARCHITECTURE.md", "# Technical Architecture\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nRuntime structure:\n- project-local Harness files\n\nValidation model:\n- doctor and objective rule checks before approval\n"),
    ("R07", ".harness/current/planning/DEVELOPMENT_PLAN.md", "# Development Plan\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nPhases:\n- domain model\n- workflow screens\n- persistence\n\nHandoff rules:\n- each phase records evidence before next phase\n"),
    ("R08", ".harness/current/planning/WORK_UNITS.md", "# Work Units\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nPlanning-only Work Unit records:\n- WU-001 define job request model\n- WU-002 define status workflow\n\nNo product code is created in this stage.\n"),
    ("R09", ".harness/current/planning/IMPLEMENTATION_START_APPROVAL_REQUEST.md", "# Implementation Start Approval Request\n\nDomain trace: TERM-001 TERM-002 TERM-003 TERM-004 OBJ-001 OBJ-002\n\nCandidate batch:\n- none approved in simulation\n\nImplementation Entry Gate: closed\n"),
]

CONTRACT_BY_STAGE = {stage["stage_id"]: stage["contract_file"] for stage in STAGES}


def write_text(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def update_read_set(root, stage, artifact):
    contract_path = f".harness/definitions/stage-contracts/{CONTRACT_BY_STAGE[stage]}"
    if not (Path(root) / contract_path).is_file():
        raise FileNotFoundError(contract_path)
    payload = {
        "schema_version": "1.0",
        "stage": stage,
        "paths": [
            ".harness/current/status/STATUS_KO.md",
            artifact,
            contract_path,
        ],
    }
    path = Path(root) / ".harness/manifests/CURRENT_READ_SET.json"
    write_canonical_json(path, payload)
    return payload["paths"]


def run_scenario(root, scenario):
    if scenario != SCENARIO_ID:
        return {"schema_version": "1.0", "command": "run-e2e-scenario", "overall_status": "fail", "blocker_count": 1, "blockers": ["e2e.unknown_scenario"], "warnings": [], "high_finding_count": 0, "korean_summary": {"one_line": "알 수 없는 E2E scenario", "blocker_count": 1, "high_finding_count": 0, "implementation_start_possible": False, "next_action": "scenario ID 확인"}, "checked_at_utc": utc_now(), "exit_code": 2}
    root = Path(root)
    transitions = []
    created_artifacts = []
    read_set_changes = []
    for stage, artifact, template in STAGE_ARTIFACTS:
        text = template.format(user_input=USER_INPUT)
        write_text(root / artifact, text)
        created_artifacts.append(artifact)
        read_paths = update_read_set(root, stage, artifact)
        read_set_changes.append({"stage": stage, "paths": read_paths})
        transitions.append({"stage": stage, "artifact": artifact, "harness_response_summary": f"{stage} artifact created from approved workflow contract"})
    write_text(root / ".harness/current/status/STATUS_KO.md", "# Harness 상태\n\n- 현재 단계: R09 Implementation Entry\n- Stage set version: harness-stage-set-v1.0.3\n- Implementation Entry Gate: closed\n")
    skill = record_external_skill_resolution(root, "R02", "matt_pocock", "grill-me", "not_installed", None)
    review = record_review_result(root, "R09", [], "pass")
    token = record_token_quality_event(root, "R01", "planning_golden_path", 42000, True, None)
    src_exists = (root / "src").exists()
    payload = {
        "schema_version": "1.0",
        "command": "run-e2e-scenario",
        "overall_status": "pass" if not src_exists else "fail",
        "blocker_count": 0 if not src_exists else 1,
        "blockers": [] if not src_exists else ["e2e.product_code_created_before_gate"],
        "warnings": [],
        "scenario_id": scenario,
        "transcript_path": ".harness/evidence/e2e/E2E_R01_R09_PLANNING_001.json",
        "user_input": USER_INPUT,
        "stage_transitions": transitions,
        "created_artifacts": created_artifacts,
        "read_set_changes": read_set_changes,
        "external_skill_evidence": [skill.relative_to(root).as_posix()],
        "review_evidence": [review.relative_to(root).as_posix()],
        "token_quality_events": [token.relative_to(root).as_posix()],
        "implementation_started": src_exists,
        "implementation_blocked_before_gate": not src_exists,
        "high_finding_count": 0,
        "korean_summary": {"one_line": "기획 단계 workflow 통과" if not src_exists else "기획 단계 workflow 실패", "blocker_count": 0 if not src_exists else 1, "high_finding_count": 0, "implementation_start_possible": False, "next_action": "R09 승인 전까지 구현 금지 유지"},
        "checked_at_utc": utc_now(),
        "exit_code": 0 if not src_exists else 1,
    }
    write_canonical_json(root / ".harness/evidence/e2e/E2E_R01_R09_PLANNING_001.json", payload)
    return payload
