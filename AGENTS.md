# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` for the current stage read set.
- Treat `.harness/current/source_identity/SOURCE_IDENTITY.json` as the local source identity pointer.
- Do not use `.harness/archive/` as a primary source.
- Keep work inside the active Implementation Entry Gate scope.
- Run `python -m unittest discover -s tools/harness-validator/tests` before claiming implementation work is complete.
