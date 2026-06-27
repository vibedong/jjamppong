from pathlib import Path

from .jsonio import load_json
from .state_model import gate_open_eligible, safe, utc_now


def git_baseline_verified(root):
    records = list((Path(root) / ".harness/evidence/git").glob("GIT_BASELINE_RECORD_*.json"))
    for record in records:
        payload = load_json(record)
        if payload.get("remote_push_verified") is True or payload.get("baseline_commit_status") == "verified":
            return True
    return False


def external_skill_evidence_exists(root):
    return any((Path(root) / ".harness/evidence/external-skills").glob("EXTERNAL_SKILL_RESOLUTION_*.json"))


def run_bootstrap_entry_audit(root, batch_id):
    root = Path(root)
    blockers = []
    batch_path = root / ".harness/current/batches" / f"BATCH_MANIFEST_{safe(batch_id)}.json"
    batch_approval_path = root / ".harness/approvals/batches" / f"BATCH_APPROVAL_{safe(batch_id)}.json"
    if not batch_path.is_file():
        blockers.append("bootstrap.missing_batch_manifest")
    if not batch_approval_path.is_file():
        blockers.append("bootstrap.batch_not_approved")
    if not git_baseline_verified(root):
        blockers.append("bootstrap.git_baseline_unverified")
    if not external_skill_evidence_exists(root):
        blockers.append("bootstrap.external_skill_resolution_missing")
    eligibility = gate_open_eligible(root, batch_id)
    blockers.extend(eligibility.get("blockers", []))
    blockers = sorted(set(blockers))
    batch = load_json(batch_path) if batch_path.is_file() else {"work_unit_ids": []}
    baseline_ok = git_baseline_verified(root)
    external_ok = external_skill_evidence_exists(root)
    return {
        "schema_version": "1.0",
        "command": "run-bootstrap-entry-audit",
        "overall_status": "pass" if not blockers else "fail",
        "warnings": [],
        "batch_id": batch_id,
        "approved_work_units": batch.get("work_unit_ids", []),
        "dependency_closure_passed": "bootstrap.missing_batch_manifest" not in blockers,
        "git_remote_verified": baseline_ok,
        "baseline_verified": baseline_ok,
        "external_skill_resolution_passed": external_ok,
        "gate_open_eligible": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "high_finding_count": 0,
        "korean_summary": {"one_line": "구현 진입 감사 통과" if not blockers else "구현 진입 감사 실패", "blocker_count": len(blockers), "high_finding_count": 0, "implementation_start_possible": not blockers, "next_action": "Gate open 가능" if not blockers else "blocker 해결 후 재실행"},
        "checked_at_utc": utc_now(),
        "exit_code": 0 if not blockers else 1,
    }
