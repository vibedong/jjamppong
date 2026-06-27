import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .stage_assets import STAGES


RELEASE_FORBIDDEN_PREFIXES = ("docs/", "tests/", "_organized_harness_design/", ".harness/artifacts/", ".harness/reviews/", ".harness/approvals/", ".harness/archive/")
INSTALLED_FORBIDDEN_PREFIXES = ("_organized_harness_design/", "tools/harness-validator/tests/")
READ_SET_FORBIDDEN_PREFIXES = ("tools/", "_organized_harness_design/", ".harness/archive/")
STAGE_RE = re.compile(r"\bR(0[1-9]|10)\b")
STAGE_ORDER = {stage["stage_id"]: index for index, stage in enumerate(STAGES)}
STAGE_ARTIFACTS = {stage["stage_id"]: stage["artifact_path"] for stage in STAGES}


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def blocker(code, path=None, detail=None):
    return {"code": code, "path": path, "detail": detail}


def rel(path, root):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def iter_files(root):
    for path in Path(root).rglob("*"):
        if path.is_file():
            yield path


def add_forbidden_path_blockers(root, mode, blockers):
    prefixes = RELEASE_FORBIDDEN_PREFIXES if mode == "release-payload" else INSTALLED_FORBIDDEN_PREFIXES
    for path in iter_files(root):
        relative = rel(path, root)
        if any(relative.startswith(prefix) for prefix in prefixes):
            blockers.append(blocker("doctor.forbidden_path", relative))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_set_paths(payload):
    values = payload.get("paths", [])
    result = []
    for item in values:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and "path" in item:
            result.append(item["path"])
    return result


def add_read_set_blockers(root, blockers):
    path = Path(root) / ".harness/manifests/CURRENT_READ_SET.json"
    if not path.is_file():
        blockers.append(blocker("doctor.read_set_missing", ".harness/manifests/CURRENT_READ_SET.json"))
        return
    payload = read_json(path)
    for value in read_set_paths(payload):
        normalized = value.replace("\\", "/")
        if os.path.isabs(value) or "\\" in value:
            blockers.append(blocker("doctor.read_set_not_project_relative", value))
        if any(normalized.startswith(prefix) for prefix in READ_SET_FORBIDDEN_PREFIXES):
            blockers.append(blocker("doctor.read_set_forbidden_path", normalized))
        full = Path(root) / normalized
        if full.exists() and full.is_dir():
            blockers.append(blocker("doctor.read_set_directory_path", normalized))


def get_status_stage(root):
    status = Path(root) / ".harness/current/status/STATUS_KO.md"
    if not status.is_file():
        return None
    match = STAGE_RE.search(status.read_text(encoding="utf-8"))
    return match.group(0) if match else None


def get_read_set_payload(root):
    path = Path(root) / ".harness/manifests/CURRENT_READ_SET.json"
    if not path.is_file():
        return None
    return read_json(path)


def add_status_blockers(root, blockers):
    status = Path(root) / ".harness/current/status/STATUS_KO.md"
    if not status.is_file():
        blockers.append(blocker("doctor.status_missing", ".harness/current/status/STATUS_KO.md"))
        return
    text = status.read_text(encoding="utf-8")
    if "Stage set version: harness-stage-set-v1.0.3" not in text:
        blockers.append(blocker("doctor.stage_set_version_missing", ".harness/current/status/STATUS_KO.md"))
    if not STAGE_RE.search(text):
        blockers.append(blocker("doctor.stage_token_missing", ".harness/current/status/STATUS_KO.md"))


def add_state_consistency_blockers(root, blockers):
    status_stage = get_status_stage(root)
    read_set = get_read_set_payload(root)
    if not status_stage or not read_set:
        return
    read_set_stage = read_set.get("stage")
    if read_set_stage and read_set_stage != status_stage:
        blockers.append(blocker("doctor.status_read_set_stage_mismatch", ".harness/manifests/CURRENT_READ_SET.json", {"status_stage": status_stage, "read_set_stage": read_set_stage}))
    if read_set.get("stage_set_version") != "harness-stage-set-v1.0.3":
        blockers.append(blocker("doctor.read_set_stage_set_version_missing", ".harness/manifests/CURRENT_READ_SET.json"))
    current_stage = read_set_stage or status_stage
    current_index = STAGE_ORDER.get(current_stage)
    if current_index is None or current_index < 1:
        return
    paths = {value.replace("\\", "/") for value in read_set_paths(read_set)}
    for stage in STAGES[:current_index]:
        artifact = stage["artifact_path"]
        if (Path(root) / artifact).is_file() and artifact not in paths:
            blockers.append(blocker("doctor.read_set_missing_previous_planning_artifact", ".harness/manifests/CURRENT_READ_SET.json", {"stage": current_stage, "missing": artifact}))


def add_stage_asset_blockers(root, blockers):
    root = Path(root)
    for stage in STAGES:
        contract = root / ".harness/definitions/stage-contracts" / stage["contract_file"]
        template = root / ".harness/definitions/templates" / stage["template_file"]
        skill = root / ".agents/skills" / stage["skill_dir"] / "SKILL.md"
        for path in (contract, template, skill):
            if not path.is_file():
                blockers.append(blocker("doctor.stage_asset_missing", rel(path, root)))
        if contract.is_file():
            contract_text = contract.read_text(encoding="utf-8")
            for label in ("required_inputs:", "required_artifacts:", "required_evidence:", "external_skill_policy:", "review_policy:", "approval_rule:", "read_set_update_rule:", "transition_rule:", "doctor_checks:"):
                if label not in contract_text:
                    blockers.append(blocker("doctor.stage_contract_required_label_missing", rel(contract, root), label))
            for section_id in stage["section_ids"]:
                if f"section_id: {section_id}" not in contract_text:
                    blockers.append(blocker("doctor.stage_contract_section_missing", rel(contract, root), section_id))
        if template.is_file():
            template_text = template.read_text(encoding="utf-8")
            for section_id in stage["section_ids"]:
                if f"section_id: {section_id}" not in template_text:
                    blockers.append(blocker("doctor.template_section_missing", rel(template, root), section_id))
    router = root / ".agents/skills/harness-workflow-router/SKILL.md"
    if not router.is_file():
        blockers.append(blocker("doctor.stage_asset_missing", ".agents/skills/harness-workflow-router/SKILL.md"))


def add_domain_trace_blockers(root, blockers):
    for relative in (".harness/current/planning/PRODUCT_SCOPE.md", ".harness/current/planning/USER_EXPERIENCE.md", ".harness/current/planning/BEHAVIOR_SPECIFICATION.md", ".harness/current/planning/TECHNICAL_ARCHITECTURE.md"):
        path = Path(root) / relative
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if "TERM-" not in text and "OBJ-" not in text:
                blockers.append(blocker("doctor.domain_trace_missing", relative))


def add_external_review_blockers(root, blockers):
    evidence_dir = Path(root) / ".harness/evidence/external-skills"
    for path in evidence_dir.glob("EXTERNAL_SKILL_RESOLUTION_*.json"):
        payload = read_json(path)
        if payload.get("skill_family") == "superpowers" and payload.get("used") is True and payload.get("stage") != "R10":
            blockers.append(blocker("doctor.superpowers_timing_violation", rel(path, root)))
        if payload.get("vendored_copy_detected") is True:
            blockers.append(blocker("doctor.external_skill_vendored_copy", rel(path, root)))
        if payload.get("resolved_status") in ("wrong_stage", "ambiguous_duplicate", "vendored_copy_forbidden"):
            blockers.append(blocker("doctor.external_skill_resolution_failed", rel(path, root), payload.get("resolved_status")))


def add_gate_blockers(root, blockers):
    path = Path(root) / ".harness/current/gate/GATE_STATE.json"
    if not path.is_file():
        return
    payload = read_json(path)
    if payload.get("gate_status") == "open_for_exact_batch" and not payload.get("open_work_unit_ids"):
        blockers.append(blocker("doctor.gate_ready_conflict", ".harness/current/gate/GATE_STATE.json"))
    counts = payload.get("ready_to_start_counts", {})
    if counts.get("ready", 0) > 0 and payload.get("gate_status") != "open_for_exact_batch":
        blockers.append(blocker("doctor.ready_to_start_gate_mismatch", ".harness/current/gate/GATE_STATE.json"))


def implementation_start_possible(root, blockers, mode):
    if mode != "installed-project" or blockers:
        return False
    path = Path(root) / ".harness/current/gate/GATE_STATE.json"
    if not path.is_file():
        return False
    try:
        payload = read_json(path)
    except Exception:
        return False
    return payload.get("gate_status") == "open_for_exact_batch" and bool(payload.get("open_work_unit_ids"))


def add_hil_mixing_blockers(root, blockers):
    current = Path(root) / ".harness/current"
    if not current.exists():
        return
    for path in current.rglob("HIL_CANDIDATE_*.json"):
        blockers.append(blocker("doctor.hil_candidate_mixed_into_product_state", rel(path, root)))


def validate(root, mode="installed-project"):
    if mode not in ("release-payload", "installed-project"):
        raise ValueError(f"unknown doctor mode: {mode}")
    root = Path(root)
    blockers = []
    add_forbidden_path_blockers(root, mode, blockers)
    release_files = sorted(rel(path, root) for path in iter_files(root))
    if mode == "installed-project":
        add_read_set_blockers(root, blockers)
        add_status_blockers(root, blockers)
        add_state_consistency_blockers(root, blockers)
        add_stage_asset_blockers(root, blockers)
        add_domain_trace_blockers(root, blockers)
        add_external_review_blockers(root, blockers)
        add_gate_blockers(root, blockers)
        add_hil_mixing_blockers(root, blockers)
    forbidden_files = [item["path"] for item in blockers if item["code"] == "doctor.forbidden_path"]
    status_path = root / ".harness/current/status/STATUS_KO.md"
    status_text = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    stage_match = STAGE_RE.search(status_text)
    read_set_file = root / ".harness/manifests/CURRENT_READ_SET.json"
    read_paths = read_set_paths(read_json(read_set_file)) if read_set_file.is_file() else []
    payload_hash = hashlib.sha256("\n".join(release_files).encode("utf-8")).hexdigest()
    can_start_implementation = implementation_start_possible(root, blockers, mode)
    state_conflict_codes = ("doctor.gate_ready_conflict", "doctor.ready_to_start_gate_mismatch", "doctor.status_read_set_stage_mismatch", "doctor.read_set_stage_set_version_missing")
    return {
        "schema_version": "1.0",
        "command": "doctor",
        "mode": mode,
        "overall_status": "pass" if not blockers else "fail",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "warnings": [],
        "metrics": {"checked_files": sum(1 for _ in iter_files(root))},
        "high_finding_count": 0,
        "korean_summary": {"one_line": "통과" if not blockers else "차단 항목 있음", "blocker_count": len(blockers), "high_finding_count": 0, "implementation_start_possible": can_start_implementation, "next_action": "없음" if not blockers else "blocker를 수정한 뒤 doctor를 다시 실행"},
        "release_files": release_files if mode == "release-payload" else [],
        "forbidden_files": forbidden_files,
        "payload_hash": payload_hash if mode == "release-payload" else None,
        "runtime_only_passed": mode != "release-payload" or not forbidden_files,
        "stage": stage_match.group(0) if stage_match else None,
        "stage_set_version": "harness-stage-set-v1.0.3" if "harness-stage-set-v1.0.3" in status_text else None,
        "read_set_paths": read_paths,
        "state_conflicts": [item for item in blockers if item["code"] in state_conflict_codes],
        "path_policy_findings": [item for item in blockers if item["code"].startswith("doctor.read_set_")],
        "exit_code": 0 if not blockers else 1,
        "checked_at_utc": utc_now(),
    }
