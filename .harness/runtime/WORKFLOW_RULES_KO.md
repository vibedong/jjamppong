# Harness Runtime Workflow Rules

R00 Install Check:

- `python tools/harness-validator/run-doctor.py`가 통과해야 한다.
- source identity가 존재해야 한다.

R01 Product Goal Intake:

- 제품 목표, 사용자, 성공 결과, 제약, 제외 범위를 정리한다.
- 확인 질문을 만든다.
- 제품 코드는 만들지 않는다.

R02 Domain Foundation:

- 이 프로젝트 전용 Domain Foundation 문서를 만든다.
- Harness 설계용 Domain Foundation과 사용자 프로젝트 Domain Foundation을 구분한다.

R03 Product Scope:

- must-have, later, unclear를 나누고 Product Scope 문서를 만든다.

R04 User Experience:

- 주요 사용자 흐름, 화면, 상태 확인 방식을 User Experience 문서로 만든다.

R05 Behavior Specification:

- 명령, Query, 상태, 이벤트, 예외, 승인 흐름을 Behavior Specification 문서로 만든다.

R06 Development Plan:

- 구현 계획, 테스트 기준, rollback 기준을 만든다.

R07 Work Units:

- fresh implementation agent가 독립적으로 실행할 Work Units를 만든다.

R08 Implementation Start Approval:

- Domain Foundation, Product Scope, User Experience, Behavior Specification, Development Plan, Work Units가 준비되기 전에는 구현 시작 승인을 열지 않는다.
- 구현 시작 승인 전 제품 코드는 금지한다.

R09 Implementation Execution:

- 승인된 Work Units 기준으로만 코드 작성과 테스트를 진행한다.
