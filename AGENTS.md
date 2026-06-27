# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` second, and read only listed files unless a stage contract requires more.
- Use `.agents/skills/harness-workflow-router/SKILL.md` to choose the current Harness stage skill.
- Use `.harness/runtime/START_WORKFLOW_KO.md` and `.harness/runtime/WORKFLOW_RULES_KO.md` for the project workflow.
- Do not read archive, design history, validator source, or whole directories by default.
- Do not create product code before R09 Implementation Entry approval.
- Run `python tools/harness-validator/run-doctor.py --mode installed-project .` before claiming Harness installation or update is complete.
