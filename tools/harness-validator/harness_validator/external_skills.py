from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .jsonio import load_json, write_canonical_json


ALLOWED_STAGE_POLICY = {
    "matt_pocock": {"R01", "R02", "R03", "R04", "R05"},
    "gstack": {"R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"},
    "superpowers": {"R10"},
}


def load_skill_catalog(root):
    path = Path(root) / ".harness/definitions/external-skills/ALLOWED_EXTERNAL_SKILL_CATALOG.json"
    if path.is_file():
        return load_json(path)
    return {
        "resolver_order": ["codex_plugin", "local_codex_skill", "github_installed_skill", "harness_native_fallback"],
        "stage_policy": {key: sorted(value) for key, value in ALLOWED_STAGE_POLICY.items()},
    }


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value))


def is_vendored_path(root, path):
    try:
        rel = Path(path).resolve().relative_to(Path(root, ".harness").resolve()).as_posix()
    except ValueError:
        return False
    return rel.startswith("external-skills/") or rel.startswith("vendored-skills/")


def source_type_for_path(path):
    normalized = Path(path).as_posix()
    if "/plugins/cache/" in normalized:
        return "codex_plugin"
    if "/.codex/skills/" in normalized:
        return "local_codex_skill"
    if "/.agents/skills/" in normalized:
        return "github_installed_skill"
    return "local_codex_skill"


def resolve_external_skill(root, stage, skill_family, requested_skill, search_roots):
    root = Path(root)
    catalog = load_skill_catalog(root)
    allowed_stage = stage in set(catalog.get("stage_policy", {}).get(skill_family, ALLOWED_STAGE_POLICY.get(skill_family, set())))
    resolver_order = catalog.get("resolver_order", ["codex_plugin", "local_codex_skill", "github_installed_skill", "harness_native_fallback"])
    matches = []
    for search_root in search_roots:
        candidate = Path(search_root) / requested_skill / "SKILL.md"
        if candidate.is_file():
            matches.append(candidate)
        direct = Path(search_root) / "SKILL.md"
        if direct.is_file() and Path(search_root).name == requested_skill:
            matches.append(direct)
    vendored = any(is_vendored_path(root, match) for match in matches)
    if vendored:
        status = "vendored_copy_forbidden"
        used = False
    elif not allowed_stage:
        status = "wrong_stage"
        used = False
    elif len(matches) > 1:
        status = "ambiguous_duplicate"
        used = False
    elif len(matches) == 1:
        status = "resolved"
        used = True
    else:
        status = "not_installed"
        used = False
    matches = sorted(matches, key=lambda item: resolver_order.index(source_type_for_path(item)) if source_type_for_path(item) in resolver_order else 999)
    resolved_path = matches[0].as_posix() if matches else None
    source_type = source_type_for_path(matches[0]) if matches else "harness_native_fallback"
    return {
        "schema_version": "1.0",
        "stage": stage,
        "skill_family": skill_family,
        "requested_skill": requested_skill,
        "resolved_status": status,
        "resolved_path": resolved_path,
        "resolved_path_style": "absolute" if resolved_path else None,
        "source_type": source_type,
        "allowed_stage": allowed_stage,
        "used": used,
        "fallback_used": status == "not_installed",
        "fallback_reason": None if used else status,
        "vendored_copy_detected": vendored,
        "permission_boundary": "findings_only_or_stage_contract_limited",
        "candidate_paths": [match.as_posix() for match in matches],
        "created_at_utc": utc_now(),
    }


def record_external_skill_resolution(root, stage, skill_family, requested_skill, resolved_status, resolved_path):
    root = Path(root)
    payload = {
        "schema_version": "1.0",
        "stage": stage,
        "skill_family": skill_family,
        "requested_skill": requested_skill,
        "resolved_status": resolved_status,
        "resolved_path": Path(resolved_path).as_posix() if resolved_path else None,
        "resolved_path_style": "absolute" if resolved_path else None,
        "source_type": "local_codex_skill" if resolved_path else "harness_native_fallback",
        "allowed_stage": stage in ALLOWED_STAGE_POLICY.get(skill_family, set()),
        "used": resolved_status == "resolved",
        "fallback_used": resolved_status != "resolved",
        "fallback_reason": None if resolved_status == "resolved" else resolved_status,
        "vendored_copy_detected": False,
        "permission_boundary": "findings_only_or_stage_contract_limited",
        "created_at_utc": utc_now(),
    }
    path = root / ".harness/evidence/external-skills" / f"EXTERNAL_SKILL_RESOLUTION_{safe_name(stage)}_{safe_name(requested_skill)}.json"
    write_canonical_json(path, payload)
    return path


def record_review_result(root, stage, findings, overall_status):
    root = Path(root)
    payload = {
        "schema_version": "1.0",
        "stage": stage,
        "review_scope": "current_stage_artifact",
        "reviewer_type": "codex_or_gstack_findings_only",
        "input_artifacts": [],
        "objective_rule_check_result": "pass" if overall_status == "pass" else "fail",
        "findings": findings,
        "overall_status": overall_status,
        "must_fix_count": sum(1 for item in findings if item.get("severity") in ("blocker", "high")),
        "creator_decision_needed_count": 0,
        "backtrack_needed_count": 0,
        "review_conflict_count": 0,
        "created_at_utc": utc_now(),
    }
    path = root / ".harness/evidence/reviews" / f"REVIEW_RESULT_{safe_name(stage)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_canonical_json(path, payload)
    return path


def record_token_quality_event(root, stage, user_request_class, approx_input_tokens, was_required_read, reason):
    root = Path(root)
    overuse = approx_input_tokens >= 50000 and not was_required_read
    payload = {
        "schema_version": "1.0",
        "stage": stage,
        "user_request_class": user_request_class,
        "approx_input_tokens": approx_input_tokens,
        "approx_output_tokens": 0,
        "files_read": [],
        "was_required_read": was_required_read,
        "overuse_suspected": overuse,
        "overuse_reason": reason if overuse else None,
        "quality_gain": None,
        "followup_rework_avoided": None,
        "created_at_utc": utc_now(),
    }
    path = root / ".harness/evidence/token-quality" / f"TOKEN_QUALITY_EVENT_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    write_canonical_json(path, payload)
    return path


def record_hil_candidate(root, source_stage, candidate_type, source_event):
    root = Path(root)
    candidate_id = f"HIL-{uuid4().hex[:12]}"
    payload = {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "source_stage": source_stage,
        "source_event": source_event,
        "candidate_type": candidate_type,
        "user_project_impact": "none_record_only",
        "harness_runtime_impact": "candidate_for_future_harness_improvement",
        "record_only": True,
        "requires_backtrack": False,
        "suggested_release": None,
        "status": "record_only",
        "created_at_utc": utc_now(),
    }
    path = root / ".harness/decisions/harness-improvement-candidates" / f"HIL_CANDIDATE_{candidate_id}.json"
    write_canonical_json(path, payload)
    return path
