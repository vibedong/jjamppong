# Harness Remote Handoff - 2026-06-29

이 문서는 Codex 데스크톱 스레드가 휴대폰에 보이지 않을 때, GitHub에서 현재 논의 상태를 이어보기 위한 원격 handoff입니다.

## 현재 작업 위치

로컬 작업 폴더:

```text
F:\jjamppong-harness-release
```

하네스 폴더:

```text
F:\jjamppong-harness-release\harness
```

원격 저장소:

```text
https://github.com/vibedong/jjamppong
```

현재 source identity 기준:

```text
release_tag: harness-v1.0.6
immutable_commit: 9320767fac8d238b1a115c0402f661155c7d5aec
source_identity_status: resolved
```

## 잠정 중단한 항목

`HBI-2026-06-29-001: Socratic-style Domain Planner persona 정합성`은 잠정 중단했다.

이 항목은 다음만 다룬다.

- `Socrates persona`라는 표현이 역사적 소크라테스 흉내처럼 읽히는 문제
- `Socratic-style Domain Planner`로 정리할지 여부
- 제품 의미를 명확히 하기 위한 질문 원칙 정의
- gate/route/status 문제는 이 항목에서 다루지 않음

별도 항목:

`HBI-2026-06-29-003: Gate and planning route wording 정합성`

이 항목은 다음만 다룬다.

- gate는 폴더가 아니라 승인 규칙이라는 점
- `grill`은 gate가 아니라 route/mode/question-pressure capability라는 점
- UI/status에서 `Current gate`와 `Planning route`를 분리하는 문제

## 현재 논의 주제

하네스 폴더 구조를 사용자와 Codex 모두 이해하기 쉽게 만들자는 논의로 전환했다.

사용자가 제안한 큰 단계:

```text
1. 기획
2. 개발계획
3. 개발
4. 개선
```

현재 판단:

- 이 네 단계 구분은 사용자-facing 흐름으로는 타당하다.
- 다만 `current/runtime/planning/improvement`를 곧바로 모두 갈아엎는 것은 위험하다.
- `runtime/`은 gate, schema, contract, release coverage와 연결된 공통 규칙 엔진이므로 유지하는 편이 안전하다.
- 먼저 stage-oriented layer를 추가하는 설계가 더 안전하다.

권장 방향:

```text
.harness/
  current/        # 지금 상태판
  runtime/        # 모든 단계가 공통으로 따르는 규칙, gate, schema
  stages/         # 사용자와 Codex가 이해하는 진행 단계
    01_planning/
    02_development_planning/
    03_development/
    04_improvement/
```

## 방금 확인한 runtime 구조

현재 runtime 폴더:

```text
.harness/runtime/
  contracts/
    PLANNING_STAGE_CONTRACT.md
  routing/
    SKILL_ROUTING_FOR_PLANNING_V1_0.json
  coverage/
    RELEASE_COVERAGE_UNIVERSE.json
  schemas/
    shared-meaning-lock.schema.json
    research-direction.schema.json
    file-write-approval.schema.json
    read-audit-token-quality.schema.json
    test-target-class.schema.json
```

비개발자용 의미:

- `contracts/`: 에이전트가 반드시 지켜야 하는 행동 계약서
- `routing/`: 어느 단계에서 어떤 skill/capability를 쓸지 정하는 표
- `coverage/`: release에 포함되는 파일 목록과 금지 범위
- `schemas/`: gate 승인서와 기록지의 양식

## 다음에 이어갈 질문

다음 논의는 바로 구조 변경이 아니라, 먼저 이 질문을 확정해야 한다.

1. 네 단계 `기획/개발계획/개발/개선`은 “사용자 제품 개발 흐름”인가, “하네스 자체 업데이트 흐름”인가, 아니면 둘 다에 적용되는 공통 언어인가?
2. `개선`은 제품 개선인가, 하네스 개선인가, 완료 후 learning/solution 정리인가?
3. 새 구조는 실제 파일 이동인가, 아니면 기존 `current/runtime`을 유지하고 `stages/` 안내 layer를 추가하는 방식인가?

현재 추천은:

```text
기존 current/runtime은 유지하고,
stages/를 추가해서 네 단계 흐름을 드러낸다.
```

## 주의할 점

- release runtime 구조를 바로 변경하지 말 것
- read set을 무겁게 만들지 말 것
- gate 이름과 개수를 바꾸지 말 것
- `runtime/`을 단계 폴더 안으로 복사해서 중복 원본을 만들지 말 것
- 먼저 backlog에 stage-oriented folder structure 항목을 추가하고 writing-plans로 설계할 것
