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
