# Harness Runtime Commands

설치 확인:

```powershell
python tools/harness-validator/run-doctor.py
```

설치:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Install -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
```

업데이트:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Update -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
```

복구:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-harness.ps1 -Mode Repair -ReleaseUrl https://github.com/vibedong/jjamppong/releases/latest
```
