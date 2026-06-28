# Codex Goal — Harness Planning Core 구현 전 설계 고정

Goal 모드로 진행해줘.

이번 Goal은 전체 Harness 구현이 아니라 Planning Core를 구현 가능한 수준으로 고정하는 것이다.

읽어야 할 파일:

- AGENTS.md
- SOCRATIC_DOMAIN_PLANNER_PERSONA_V1_0.md
- PLANNING_CORE_PRODUCT_SPEC_V1_0.md
- PLANNING_RUNTIME_ARTIFACTS_SCHEMA_V1_0.md
- PLANNING_CORE_DEVELOPMENT_HANDOFF_V1_0.md

목표:

1. Planning Core를 기존 Harness 전체 설계와 충돌하지 않게 통합한다.
2. 짧은 AGENTS.md 라우터를 적용한다.
3. Socratic Domain Planner Persona를 기획 단계 기본 persona로 설정한다.
4. Ambiguity Ledger, Domain Dictionary, Question Queue, Decision Ledger를 Planning Core의 source of truth로 둔다.
5. Matt Pocock 계열은 질문 압박 capability로 route한다.
6. gstack은 findings-only planning review로 route한다.
7. Superpowers는 Planning Core에서 사용하지 않는다.
8. “자동화가 필요해” 테스트 시나리오를 acceptance test로 고정한다.

금지:

- 제품 코드 작성
- 전체 Harness 구현
- Work Units 실행
- validator 구현
- Superpowers 실행
- Implementation Gate 변경

산출물:

- PLANNING_CORE_INTEGRATION_PLAN_KO_V1_0.md
- PLANNING_CORE_STAGE_CONTRACT_V1_0.md
- PLANNING_CORE_OBJECTIVE_CHECKS_V1_0.md
- PLANNING_CORE_TEST_TARGETS_V1_0.md
- PLANNING_CORE_IMPLEMENTATION_PLAN_REQUEST_KO_V1_0.md

마지막 보고:

- Planning Core가 왜 필요한지
- 기존 Harness와 어떻게 연결되는지
- 첫 구현 slice
- test scenarios
- 다음 개발계획으로 넘길 준비 여부
