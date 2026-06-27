# Harness 1.0.3 Runtime

Harness는 Codex 앱에서 프로젝트 폴더 안에 설치해 쓰는 프로젝트 로컬 제작 workflow입니다. 별도 Windows 앱이나 Codex 플러그인이 아닙니다.

## Codex 앱에서 설치

설치할 프로젝트 폴더를 Codex 앱으로 연 뒤 GitHub 링크와 의도를 함께 말합니다.

```text
https://github.com/vibedong/jjamppong/releases/latest 하네스 설치해줘
https://github.com/vibedong/jjamppong/releases/latest 하네스 업데이트해줘
github.com/vibedong/jjamppong 하네스 설치해줘
```

Codex는 release asset의 `install-harness.ps1`을 내려받고 아래 명령을 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Install -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
python tools/harness-validator/run-doctor.py --mode installed-project .
```

업데이트는 다음 명령을 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Update -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
python tools/harness-validator/run-doctor.py --mode installed-project .
```

Harness 1.0.3은 업데이트와 복구 시 현재 기획 단계의 `STATUS_KO.md`와 `CURRENT_READ_SET.json`을 초기 상태로 되돌리지 않습니다. v1.0.2 stage set에서 v1.0.3으로 바뀌며 검토가 필요한 경우 migration evidence를 남기고 자동 stage 이동은 하지 않습니다.

## 설치 후 workflow

설치된 프로젝트는 전체 Harness 설계 문서 없이도 시작합니다.

1. `AGENTS.md`
2. `.harness/current/status/STATUS_KO.md`
3. `.harness/manifests/CURRENT_READ_SET.json`
4. `.agents/skills/harness-workflow-router/SKILL.md`
5. read set에 적힌 현재 단계 contract와 runtime workflow 파일

제품 목표를 말하면 Harness는 제품 코드를 만들기 전에 다음 순서로 진행합니다.

```text
R01 Product Goal
R02 Domain Foundation
R03 Product Scope
R04 User Experience
R05 Behavior Specification
R06 Technical Architecture
R07 Development Plan
R08 Work Units
R09 Implementation Entry
R10 Implementation Execution
```

## 검증

설치 확인:

```powershell
python tools/harness-validator/run-doctor.py --mode installed-project .
```

release payload 확인:

```powershell
python tools/harness-validator/run-doctor.py --mode release-payload .
```

## 보안

API key, password, authentication token, recovery code 같은 secret은 Git이나 일반 프로젝트 문서에 저장하지 않습니다.
