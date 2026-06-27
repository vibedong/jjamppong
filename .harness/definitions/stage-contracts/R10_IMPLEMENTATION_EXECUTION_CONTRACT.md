# R10 Implementation Execution Contract

stage_id: R10
purpose: Execute and verify the Implementation Execution stage without skipping Harness order.
artifact_path: .harness/current/implementation/IMPLEMENTATION_EXECUTION_STATUS.md

section_id: purpose
section_id: exact_batch_scope
section_id: implementation_source_manifest
section_id: test_evidence
section_id: review_evidence
section_id: gate_close_request
section_id: next_batch_status

required_inputs:
- STATUS_KO.md current stage must match this contract.
- CURRENT_READ_SET.json must include this contract and current artifact only.
- Previous stage approved artifact hash must exist unless this is R01.

allowed_actions:
- Create or update only the current stage artifact.
- Update STATUS_KO.md and CURRENT_READ_SET.json.
- Record evidence required by this contract.

forbidden_actions:
- Do not create product code before R09 approval.
- Do not skip required earlier stages.
- Do not read archive, superseded design history, validator source, or whole directories by default.

required_artifacts:
- .harness/current/implementation/IMPLEMENTATION_EXECUTION_STATUS.md

required_evidence:
- Objective Rule Check evidence when this stage requests approval.
- Review evidence when this stage creates an approval candidate.
- Approval evidence after creator approval.

external_skill_policy:
- External skills are referenced from Codex/local environment and are not vendored into Harness runtime.
- Skill use, fallback, wrong-stage rejection, and ambiguity are recorded under .harness/evidence/external-skills/.
- Superpowers execution is forbidden before R10 with an opened Implementation Entry Gate.

review_policy:
- Reviewers produce findings-only evidence.
- Reviewers do not mutate official artifacts and do not approve on behalf of the creator.

approval_rule:
- Creator approval must name the exact artifact path and SHA-256.
- A later bundle approval cannot bypass exact per-artifact identity checks.

read_set_update_rule:
- CURRENT_READ_SET.json must list exact files, not broad runtime or validator directories.
- Read set must include current stage contract, current artifact, and immediate approved predecessors only.

doctor_checks:
- Required section IDs exist.
- Required sections are not empty marker text only.
- Stage artifact path matches artifact_path.
- Domain trace IDs are present from R03 onward when domain artifacts exist.
- External skill and review evidence requirements are satisfied before approval.

transition_rule:
- Move to the next stage only when required sections, required evidence, read set update, review status, and creator approval are complete.
