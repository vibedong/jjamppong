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

기획단계 상태 기계는 유한하다. 사용자의 문장이 다양해도 Harness는 현재 단계에서 다음 중 하나로만 처리한다.

- 정보가 충분하면 다음 단계로 이동한다.
- 정보가 부족하면 확인 질문을 만들고 현재 단계에 머문다.
- 현재 단계 수정 요청이면 현재 단계 산출물만 갱신한다.
- 이전 결정과 충돌하면 필요한 이전 단계로 되돌아간다.
- 구현 또는 제품 코드 작성을 요구하면 R08 승인 전까지 차단하고 현재 단계를 유지한다.

새 채팅에서는 먼저 `STATUS_KO.md`와 `CURRENT_READ_SET.json`을 읽고 현재 단계를 복원한다. 업데이트 또는 복구 후에도 현재 단계와 read set이 R00으로 되돌아가면 안 된다.
