# Read Set Policy

초기 read set은 20 KiB 이하여야 한다.

규칙:

- read set은 파일만 가리킨다.
- read set은 기본 상태에서 `tools/`를 가리키지 않는다.
- read set은 `_organized_harness_design/`를 가리키지 않는다.
- 긴 작업 뒤에는 `STATUS_KO.md`를 짧게 갱신한다.
- validator 코드는 doctor 실패를 분석할 때만 읽는다.
- 필수 workflow 문서를 읽는 것은 과토큰이 아니다.

단순 작업에서 전체 설계 문서나 validator source를 읽으면 wasteful over-reading으로 기록한다.

새 채팅과 업데이트 후에는 현재 단계 read set을 유지한다. 업데이트 때문에 현재 단계 read set이 초기 설치 read set으로 되돌아가면 안 된다. 현재 단계가 R02 이상이면 이전 단계의 planning 산출물도 read set에 포함되어야 한다.
