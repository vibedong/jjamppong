# Planning Core Integration Report KO v1.0

artifact_id: harness.planning_core_integration_report_ko
artifact_version: 1.0

## 통합 결과

Planning Core 설계 파일을 기존 Harness runtime 경로 체계에 맞춰 통합했다. `work/AGENTS.md`는 `harness/AGENTS.md`에 덮어쓰지 않았고, 기존 Harness router를 유지한 상태에서 Planning Core 참조만 짧게 추가했다.

## 파일 배치

| source | target |
| --- | --- |
| `work/SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md` | `.harness/planning/SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md` |
| `work/PLANNING_CORE_PRODUCT_SPEC_V1_0.md` | `.harness/planning/PLANNING_CORE_PRODUCT_SPEC_V1_0.md` |
| `work/PLANNING_RUNTIME_ARTIFACTS_SCHEMA_V1_0.md` | `.harness/planning/PLANNING_RUNTIME_ARTIFACTS_SCHEMA_V1_0.md` |
| `work/PLANNING_CORE_DEVELOPMENT_HANDOFF_V1_0.md` | `.harness/planning/PLANNING_CORE_DEVELOPMENT_HANDOFF_V1_0.md` |
| `work/CODEX_GOAL_PLANNING_CORE_DESIGN_LOCK.md` | `.harness/planning/CODEX_GOAL_PLANNING_CORE_DESIGN_LOCK.md` |

세부 배치 기록은 `.harness/planning/PLANNING_CORE_FILE_PLACEMENT_MAP_V1_0.json`에 있다.

## AGENTS.md 병합

`harness/AGENTS.md`는 전체 교체하지 않았다. 기존 current status, current read set, source identity, START_HERE, planning contract 우선순위를 보존했고 다음 짧은 참조만 추가했다.

- `.harness/planning/SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md`
- `.harness/planning/PLANNING_CORE_PRODUCT_SPEC_V1_0.md`
- `.harness/runtime/routing/SKILL_ROUTING_FOR_PLANNING_V1_0.json`

Planning Core 세부 규칙은 AGENTS.md가 아니라 `.harness/planning/` 문서와 `.harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md`가 소유한다.

## CURRENT_READ_SET 변경

기본 read set에는 다음 Planning Core 파일만 추가했다.

- `.harness/planning/SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md`
- `.harness/runtime/routing/SKILL_ROUTING_FOR_PLANNING_V1_0.json`

`PLANNING_CORE_PRODUCT_SPEC_V1_0.md`와 `PLANNING_RUNTIME_ARTIFACTS_SCHEMA_V1_0.md`를 기본 read set에 함께 넣으면 20KB 제한을 초과하므로 `.harness/current/readsets/PLANNING_EXTENDED_READ_SET.json`으로 분리했다.

기본 read set 총량은 11,627 bytes다. 제한은 20,480 bytes다.

## Gate 보존

기존 gate 규칙을 약화하지 않았다.

- Research Direction Gate 승인 전 외부 검색과 외부 자료 확인 금지 유지
- File Write Gate 승인 전 파일 작성 금지 유지
- Status/Read Set Advance Gate 승인 전 status/read set 변경 금지 유지
- Shared Meaning Lock 기록 전 의미 확정 금지 유지
- 제품 코드 작성 금지 유지
- Superpowers는 Planning Core에서 사용하지 않음

`PLANNING_STAGE_CONTRACT.md`에는 Planning Core가 아이디어를 바로 요구사항화하지 않고, 핵심 단어 의미 폭발과 Ambiguity Ledger, Domain Dictionary, Question Queue, Decision Ledger를 사용한다는 보강만 추가했다.

## Skill Routing

`.harness/runtime/routing/SKILL_ROUTING_FOR_PLANNING_V1_0.json`을 추가했다.

- planning_discovery: Matt Pocock 계열 `grill-me` style questioning 선호, Harness-native fallback
- planning_review: gstack findings-only review 선호, Harness-native fallback
- implementation: Planning Core 중 Superpowers 사용 금지
- 모든 planning route는 RunRecord 필요
- planning 중 mutation은 gate 전 허용하지 않음

## Dry Run

`.harness/planning/PLANNING_CORE_DRY_RUN_AUTOMATION_EXAMPLE_KO_V1_0.md`에 "자동화가 필요해" 입력 시 기대 흐름을 기록했다.

- 요구사항화 금지 선언
- "자동화" 가능한 의미 제시
- Ambiguity Ledger 후보
- Domain Dictionary 후보
- Question Queue 후보
- 파일 쓰기 전 approval 필요
- 제품 코드 생성 없음

## Doctor 결과

기준 baseline doctor는 통합 전 pass였다.

통합 후 최종 검증은 다음 public command로 수행했다.

```powershell
.\harness.ps1 doctor
```

최종 결과:

- overall_status: pass
- read_set_total_bytes: 11627
- read_set_violations: []
- coverage_violations: []
- source_identity_violations: []
- release_candidate mode: pass

## 제외 및 금지 준수

`work/` 폴더는 runtime 배치 대상으로 포함하지 않았다. `RELEASE_COVERAGE_UNIVERSE.json`의 runtime_paths에는 `work/`, `_organized_harness_design/`, `tests/`, `docs/`, `PRIVATE_HARNESS_CONTEXT/` prefix가 없다. 제품 코드 구현, 외부 skill 설치, 외부 skill 실행, Superpowers 실행, release 생성, GitHub push는 하지 않았다.
