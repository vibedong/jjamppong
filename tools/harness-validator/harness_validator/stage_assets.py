from pathlib import Path


STAGES = [
    {"stage_id": "R01", "title": "Product Goal", "contract_file": "R01_PRODUCT_GOAL_CONTRACT.md", "template_file": "PRODUCT_GOAL_INTAKE_TEMPLATE.md", "artifact_path": ".harness/current/planning/PRODUCT_GOAL_INTAKE.md", "skill_dir": "harness-r01-product-goal", "section_ids": ["purpose", "user_goal", "success_criteria", "clarifying_questions", "decisions", "open_items", "next_stage_readiness"]},
    {"stage_id": "R02", "title": "Domain Foundation", "contract_file": "R02_DOMAIN_FOUNDATION_CONTRACT.md", "template_file": "DOMAIN_FOUNDATION_TEMPLATE.md", "artifact_path": ".harness/current/planning/DOMAIN_FOUNDATION.md", "skill_dir": "harness-r02-domain-foundation", "section_ids": ["purpose", "roles", "domain_terms", "business_objects", "states", "events", "rules", "boundaries", "ambiguous_terms", "decisions", "trace_links"]},
    {"stage_id": "R03", "title": "Product Scope", "contract_file": "R03_PRODUCT_SCOPE_CONTRACT.md", "template_file": "PRODUCT_SCOPE_TEMPLATE.md", "artifact_path": ".harness/current/planning/PRODUCT_SCOPE.md", "skill_dir": "harness-r03-product-scope", "section_ids": ["purpose", "included_scope", "excluded_scope", "capabilities", "non_goals", "domain_trace_links", "approval_request"]},
    {"stage_id": "R04", "title": "User Experience", "contract_file": "R04_USER_EXPERIENCE_CONTRACT.md", "template_file": "USER_EXPERIENCE_TEMPLATE.md", "artifact_path": ".harness/current/planning/USER_EXPERIENCE.md", "skill_dir": "harness-r04-user-experience", "section_ids": ["purpose", "users", "workflows", "screens_or_views", "state_visibility", "error_empty_loading_states", "domain_trace_links", "approval_request"]},
    {"stage_id": "R05", "title": "Behavior Specification", "contract_file": "R05_BEHAVIOR_SPECIFICATION_CONTRACT.md", "template_file": "BEHAVIOR_SPECIFICATION_TEMPLATE.md", "artifact_path": ".harness/current/planning/BEHAVIOR_SPECIFICATION.md", "skill_dir": "harness-r05-behavior-spec", "section_ids": ["purpose", "commands", "queries", "events", "states", "policies", "acceptance_criteria", "domain_trace_links", "approval_request"]},
    {"stage_id": "R06", "title": "Technical Architecture", "contract_file": "R06_TECHNICAL_ARCHITECTURE_CONTRACT.md", "template_file": "TECHNICAL_ARCHITECTURE_TEMPLATE.md", "artifact_path": ".harness/current/planning/TECHNICAL_ARCHITECTURE.md", "skill_dir": "harness-r06-technical-architecture", "section_ids": ["purpose", "runtime_structure", "state_model", "validation_model", "security_boundaries", "migration_policy", "test_strategy", "approval_request"]},
    {"stage_id": "R07", "title": "Development Plan", "contract_file": "R07_DEVELOPMENT_PLAN_CONTRACT.md", "template_file": "DEVELOPMENT_PLAN_TEMPLATE.md", "artifact_path": ".harness/current/planning/DEVELOPMENT_PLAN.md", "skill_dir": "harness-r07-development-plan", "section_ids": ["purpose", "phases", "dependency_matrix", "allocation_registry", "test_targets", "handoff_rules", "approval_request"]},
    {"stage_id": "R08", "title": "Work Units", "contract_file": "R08_WORK_UNITS_CONTRACT.md", "template_file": "WORK_UNITS_TEMPLATE.md", "artifact_path": ".harness/current/planning/WORK_UNITS.md", "skill_dir": "harness-r08-work-units", "section_ids": ["purpose", "work_streams", "work_units", "dependency_edges", "approval_targets", "test_targets", "ready_rules", "approval_request"]},
    {"stage_id": "R09", "title": "Implementation Entry", "contract_file": "R09_IMPLEMENTATION_ENTRY_CONTRACT.md", "template_file": "IMPLEMENTATION_START_APPROVAL_REQUEST_TEMPLATE.md", "artifact_path": ".harness/current/planning/IMPLEMENTATION_START_APPROVAL_REQUEST.md", "skill_dir": "harness-r09-implementation-entry", "section_ids": ["purpose", "candidate_batch", "exact_work_unit_identities", "bootstrap_entry_audit", "git_baseline", "gate_open_request", "approval_request"]},
    {"stage_id": "R10", "title": "Implementation Execution", "contract_file": "R10_IMPLEMENTATION_EXECUTION_CONTRACT.md", "template_file": "IMPLEMENTATION_EXECUTION_STATUS_TEMPLATE.md", "artifact_path": ".harness/current/implementation/IMPLEMENTATION_EXECUTION_STATUS.md", "skill_dir": "harness-r10-implementation-execution", "section_ids": ["purpose", "exact_batch_scope", "implementation_source_manifest", "test_evidence", "review_evidence", "gate_close_request", "next_batch_status"]},
]


def write_text(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def contract_text(stage):
    lines = [f"# {stage['stage_id']} {stage['title']} Contract", "", f"stage_id: {stage['stage_id']}", f"purpose: Execute and verify the {stage['title']} stage without skipping Harness order.", f"artifact_path: {stage['artifact_path']}", ""]
    for section_id in stage["section_ids"]:
        lines.append(f"section_id: {section_id}")
    lines += [
        "",
        "required_inputs:",
        "- STATUS_KO.md current stage must match this contract.",
        "- CURRENT_READ_SET.json must include this contract and current artifact only.",
        "- Previous stage approved artifact hash must exist unless this is R01.",
        "",
        "allowed_actions:",
        "- Create or update only the current stage artifact.",
        "- Update STATUS_KO.md and CURRENT_READ_SET.json.",
        "- Record evidence required by this contract.",
        "",
        "forbidden_actions:",
        "- Do not create product code before R09 approval.",
        "- Do not skip required earlier stages.",
        "- Do not read archive, superseded design history, validator source, or whole directories by default.",
        "",
        "required_artifacts:",
        f"- {stage['artifact_path']}",
        "",
        "required_evidence:",
        "- Objective Rule Check evidence when this stage requests approval.",
        "- Review evidence when this stage creates an approval candidate.",
        "- Approval evidence after creator approval.",
        "",
        "external_skill_policy:",
        "- External skills are referenced from Codex/local environment and are not vendored into Harness runtime.",
        "- Skill use, fallback, wrong-stage rejection, and ambiguity are recorded under .harness/evidence/external-skills/.",
        "- Superpowers execution is forbidden before R10 with an opened Implementation Entry Gate.",
        "",
        "review_policy:",
        "- Reviewers produce findings-only evidence.",
        "- Reviewers do not mutate official artifacts and do not approve on behalf of the creator.",
        "",
        "approval_rule:",
        "- Creator approval must name the exact artifact path and SHA-256.",
        "- A later bundle approval cannot bypass exact per-artifact identity checks.",
        "",
        "read_set_update_rule:",
        "- CURRENT_READ_SET.json must list exact files, not broad runtime or validator directories.",
        "- Read set must include current stage contract, current artifact, and immediate approved predecessors only.",
        "",
        "doctor_checks:",
        "- Required section IDs exist.",
        "- Required sections are not empty marker text only.",
        "- Stage artifact path matches artifact_path.",
        "- Domain trace IDs are present from R03 onward when domain artifacts exist.",
        "- External skill and review evidence requirements are satisfied before approval.",
        "",
        "transition_rule:",
        "- Move to the next stage only when required sections, required evidence, read set update, review status, and creator approval are complete.",
        "",
    ]
    return "\n".join(lines)


def template_text(stage):
    lines = [f"# {stage['title']}", ""]
    for section_id in stage["section_ids"]:
        lines += [f"<!-- section_id: {section_id} -->", ""]
    return "\n".join(lines)


def skill_text(stage):
    return f"""---
name: {stage['skill_dir']}
description: Execute Harness {stage['stage_id']} {stage['title']} stage.
---

# Harness {stage['stage_id']} {stage['title']}

Use `.harness/definitions/stage-contracts/{stage['contract_file']}`.
Create or update `{stage['artifact_path']}`.
Do not create product code before R09 approval.
Update `.harness/current/status/STATUS_KO.md`.
Update `.harness/manifests/CURRENT_READ_SET.json`.
"""


def write_stage_assets(root):
    root = Path(root)
    for stage in STAGES:
        write_text(root / ".harness/definitions/stage-contracts" / stage["contract_file"], contract_text(stage))
        write_text(root / ".harness/definitions/templates" / stage["template_file"], template_text(stage))
        write_text(root / ".agents/skills" / stage["skill_dir"] / "SKILL.md", skill_text(stage))
    write_text(root / ".agents/skills/harness-workflow-router/SKILL.md", """---
name: harness-workflow-router
description: Route Codex to the current Harness stage using project-local status and read set.
---

# Harness Workflow Router

Read `.harness/current/status/STATUS_KO.md` first.
Read `.harness/manifests/CURRENT_READ_SET.json` second.
Use only the current stage skill and current stage contract.
Do not read archive, design history, validator source, or whole directories by default.
If current state and read set conflict, run `python tools/harness-validator/run-doctor.py --mode installed-project .`.
""")
