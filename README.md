# Harness 1.0 Runtime

Harness는 Codex 앱에서 프로젝트 폴더 안에 설치해 쓰는 프로젝트 로컬 제작 workflow입니다. 별도 Windows 앱이나 Codex 플러그인이 아닙니다.

## Codex 앱에서 설치

설치할 프로젝트 폴더를 Codex 앱으로 연 뒤 GitHub 링크와 의도를 함께 말합니다.

```text
github.com/vibedong/jjamppong 하네스 설치해줘.
https://github.com/vibedong/jjamppong/releases/latest 하네스 설치해줘.
github 링크로 하네스 업데이트해줘.
```

Codex는 release asset의 `install-harness.ps1`을 내려받고 아래 명령을 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Install -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
python tools/harness-validator/run-doctor.py
```

업데이트는 다음 명령을 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Update -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
python tools/harness-validator/run-doctor.py
```

비공개 저장소면 GitHub CLI와 `gh auth login`이 필요합니다. 공개 release asset이 아니면 public link-only ready로 주장하지 않습니다.

## 설치 후 workflow

설치된 프로젝트는 전체 Harness 설계 문서 없이도 시작합니다.

1. `AGENTS.md`
2. `.harness/current/status/STATUS_KO.md`
3. `.harness/manifests/CURRENT_READ_SET.json`
4. read set에 적힌 runtime workflow 파일

제품 목표를 말하면 Harness는 제품 코드를 만들기 전에 다음 순서로 진행합니다.

```text
Product Goal Intake
Domain Foundation
Product Scope
User Experience
Behavior Specification
Development Plan
Work Units
Implementation Start Approval
```

## 검증

설치 확인:

```powershell
python tools/harness-validator/run-doctor.py
```

## 보안

API key, password, authentication token, recovery code 같은 secret은 Git이나 일반 프로젝트 문서에 저장하지 않습니다.
