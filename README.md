# Harness 1.0.6 Runtime

Harness는 Codex 앱에서 프로젝트 폴더 안에 설치해 쓰는 프로젝트 로컬 제작 workflow입니다. 별도 Windows 앱이나 Codex 플러그인이 아닙니다.

## GitHub 링크 설치

Codex 앱에서 설치할 프로젝트 폴더를 열고 다음처럼 말합니다.

```text
https://github.com/vibedong/jjamppong/releases/latest 의 Harness를 이 폴더에 설치해줘.
```

Codex는 release asset의 `install-harness.ps1`을 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -GitHubUrl https://github.com/vibedong/jjamppong/releases/latest
```

이미 Harness가 설치된 폴더에서 다시 설치를 요청하면 installer는 파일을 쓰지 않고 update preflight를 보여줍니다. 업데이트가 목적이면 다음처럼 말합니다.

```text
https://github.com/vibedong/jjamppong/releases/latest 의 Harness로 업데이트해줘.
```

Codex는 다음 명령을 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -GitHubUrl https://github.com/vibedong/jjamppong/releases/latest -Update
```

## 설치 후 첫 검증

```powershell
.\harness.ps1 doctor
```

설치된 프로젝트의 일반 사용자는 `python -m unittest`를 실행하지 않습니다. 개발자용 테스트는 source/developer release에서만 사용합니다.

## 첫 대화 원칙

사용자가 제품 아이디어를 말하면 Harness는 바로 리서치하거나 구현하지 않습니다. 먼저 `.harness/runtime/contracts/PLANNING_STAGE_CONTRACT.md`에 따라 Socrates persona로 사용자의 의미를 확인하고, Shared Meaning Lock이 명시적으로 기록된 뒤에만 다음 gate로 이동합니다.

## 보안

API key, password, authentication token, recovery code 같은 secret은 Git이나 일반 프로젝트 문서에 저장하지 않습니다.
