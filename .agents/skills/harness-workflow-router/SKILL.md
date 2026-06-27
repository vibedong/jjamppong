---
name: harness-workflow-router
description: Route Codex to the current Harness stage using project-local status and read set.
---

# Harness Workflow Router

Read `.harness/current/status/STATUS_KO.md` first.
Read `.harness/manifests/CURRENT_READ_SET.json` second.
Use only the current stage skill and current stage contract.
Do not read archive, design history, validator source, or whole directories by default.
If current state and read set conflict, run `python tools/harness-validator/run-doctor.py --mode installed-project .`.
