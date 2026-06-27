# R05 Behavior Specification Contract

stage_id: R05
purpose: Execute and verify the Behavior Specification stage without skipping Harness order.
artifact_path: .harness/current/planning/BEHAVIOR_SPECIFICATION.md

section_id: purpose
section_id: commands
section_id: queries
section_id: events
section_id: states
section_id: policies
section_id: acceptance_criteria
section_id: domain_trace_links
section_id: approval_request

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
- .harness/current/planning/BEHAVIOR_SPECIFICATION.md

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
