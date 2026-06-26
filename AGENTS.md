# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` for the current stage read set.
- Treat `.harness/current/source_identity/SOURCE_IDENTITY.json` as the local source identity pointer.
- Use `.harness/runtime/START_WORKFLOW_KO.md` and `.harness/runtime/WORKFLOW_RULES_KO.md` for the project workflow.
- Do not use archive, design history, or validator source as default context.
- Run `python tools/harness-validator/run-doctor.py` before claiming Harness installation or update is complete.
