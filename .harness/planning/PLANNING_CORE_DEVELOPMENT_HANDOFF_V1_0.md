# Planning Core Development Handoff v1.0

## 1. 개발계획에 바로 넣을 개발 목표

첫 구현 목표는 전체 Harness 1.0이 아니라 **Planning Core vertical slice**다.

### Slice P0 — 상태와 라우팅

사용자가 Codex 앱에서 프로젝트를 열었을 때:

1. 짧은 `AGENTS.md`가 현재 상태와 Planning Core 파일을 가리킨다.
2. `STATUS_KO.md`는 현재 Harness 상태를 보여준다.
3. `SKILL_ROUTING_FOR_PLANNING_V1_0.json`은 Matt Pocock 계열 또는 Harness-native fallback을 가리킨다.
4. 제품 코드 작성은 금지된다.

### Slice P1 — 모호성 발견

사용자가 “자동화가 필요해”라고 입력하면:

1. AI는 요구사항화를 금지한다고 선언한다.
2. “자동화”의 가능한 의미를 펼친다.
3. Ambiguity Ledger에 `AMB-001`을 만든다.
4. Question Queue에 blocking question을 만든다.

### Slice P2 — 도메인 사전 작성

사용자가 의미를 선택하면:

1. 선택 의미와 금지 의미가 기록된다.
2. Domain Dictionary에 “자동화”가 생성된다.
3. creator confirmation이 true가 되기 전까지 다음 단계로 가지 않는다.

### Slice P3 — 문제와 해결책 분리

사용자가 실제 경험 이야기를 제공하면:

1. story record가 만들어진다.
2. opportunity/problem이 기록된다.
3. proposed solution과 problem이 분리된다.

### Slice P4 — 기획 완료 판정

blocking ambiguity가 0이고 핵심 체크가 통과하면:

1. Domain Planning Brief가 생성된다.
2. gstack findings-only 검토 또는 Harness-native 검토가 실행된다.
3. 사용자 의미 확인 요청이 만들어진다.

## 2. 구현 금지 범위

이 개발계획에서는 다음을 하지 않는다.

- 전체 Harness 구현
- Superpowers 실행
- Work Units 739개 실행
- 제품 코드 생성
- 외부 배포
- GPT Pro 검토 패킷 자동 생성
- 여러 에이전트 수렴 테스트 기본 적용

## 3. 필요한 파일

```text
AGENTS.md
.harness/current/status/STATUS_KO.md
.harness/current/readsets/CURRENT_READ_SET.json
.harness/current/readsets/PLANNING_EXTENDED_READ_SET.json
.harness/planning/SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md
.harness/planning/PLANNING_CORE_PRODUCT_SPEC_V1_0.md
.harness/planning/PLANNING_RUNTIME_ARTIFACTS_SCHEMA_V1_0.md
.harness/runtime/routing/SKILL_ROUTING_FOR_PLANNING_V1_0.json
.harness/artifacts/planning/AMBIGUITY_LEDGER.jsonl
.harness/artifacts/planning/DOMAIN_DICTIONARY.jsonl
.harness/artifacts/planning/QUESTION_QUEUE.jsonl
.harness/artifacts/planning/DECISION_LEDGER.jsonl
.harness/artifacts/planning/DOMAIN_PLANNING_BRIEF.md
```

## 4. Skill routing

```json
{
  "planning_discovery": {
    "preferred_family": "mattpocock",
    "preferred_capability": "grill-me / grilling / grill-with-docs",
    "fallback": "harness_native_socratic_questions",
    "run_record_required": true
  },
  "planning_review": {
    "preferred_family": "gstack",
    "preferred_capability": "findings-only review",
    "fallback": "harness_native_findings_review",
    "source_mutation_allowed": false,
    "run_record_required": true
  },
  "implementation": {
    "preferred_family": "superpowers",
    "allowed": false,
    "reason": "Planning Core 구현 전에는 사용하지 않음"
  }
}
```

## 5. 개발 acceptance criteria

1. 사용자가 모호한 단어를 입력하면 Ambiguity Ledger가 생성된다.
2. AI가 PRD 또는 요구사항으로 바로 변환하지 않는다.
3. 가능한 의미와 금지 의미를 질문한다.
4. 사용자가 선택한 의미는 Domain Dictionary에 저장된다.
5. 모든 질문은 Question Queue에 목적과 상태를 가진다.
6. 답변은 fact/assumption/proposed_solution/decision으로 분리된다.
7. blocking ambiguity가 남아 있으면 planning completion은 false다.
8. Domain Planning Brief는 기획 완료 조건 통과 후에만 생성된다.
9. gstack 검토 또는 fallback 검토는 원본을 수정하지 않는다.
10. RunRecord 없이 기획 산출물을 만들지 않는다.

## 6. 테스트 시나리오

### Test A — 자동화 모호성

입력:

```text
자동화가 필요해.
```

기대:

- AI가 요구사항화 금지 선언
- “자동화” possible meanings 제시
- AMB-001 생성
- Question Queue 생성
- 코드 생성 없음

### Test B — 결정 대행 금지

입력:

```text
AI가 알아서 결정해주면 좋겠어.
```

기대:

- AI가 결정 대행의 위험을 설명
- 가능한 자동화 범위를 나눔
- 사용자 승인 없이는 decision 기록 안 함
- forbidden_interpretations에 “AI final approval” 기록

### Test C — 완료 차단

조건:

- 핵심 용어 1개가 open ambiguity

기대:

- planning completion false
- 다음 단계 이동 차단

### Test D — 기획안 생성

조건:

- blocking ambiguity 0
- Domain Dictionary confirmed
- Story Record exists
- non-goal exists
- creator meaning confirmed

기대:

- Domain Planning Brief 생성
- ready_for_product_scope true
