# Harness 시작 Workflow

사용자가 만들 제품을 설명하면 먼저 제품 목표와 제약을 한국어로 정리하고 확인 질문을 만든다. 이 단계에서는 제품 코드를 만들지 않는다.

처음 응답에서 확인할 것:

- 누가 쓰는 제품인가
- 어떤 결과가 성공인가
- 반드시 필요한 기능은 무엇인가
- 이번에 제외할 것은 무엇인가
- 기존 프로젝트인지 빈 폴더인지

진행 순서:

1. R01 Product Goal Intake: 제품 목표를 정리하고 확인 질문을 만든다.
2. R02 Domain Foundation: 이 프로젝트 전용 Domain Foundation 문서를 만든다.
3. R03 Product Scope: 합의된 범위와 제외 범위를 문서화한다.
4. R04 User Experience: 주요 사용자 흐름과 화면 경험을 문서화한다.
5. R05 Behavior Specification: 명령, 상태, 이벤트, 예외 동작을 문서화한다.
6. R06 Development Plan: 구현 전 개발 계획을 만든다.
7. R07 Work Units: 독립 구현 단위를 만든다.
8. R08 Implementation Start Approval: 구현 시작 승인 전까지 제품 코드는 금지한다.

각 단계가 끝나면 `.harness/current/status/STATUS_KO.md`와 `.harness/manifests/CURRENT_READ_SET.json`을 갱신한다.
