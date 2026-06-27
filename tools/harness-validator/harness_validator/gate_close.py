from pathlib import Path

from .jsonio import load_json
from .state_model import utc_now


def check_json_status(root, relative_paths, expected_status, blocker_code, require_zero_must_fix=False):
    blockers = []
    for relative_path in relative_paths:
        path = Path(root) / relative_path
        if not path.is_file():
            blockers.append(blocker_code)
            continue
        payload = load_json(path)
        if payload.get("overall_status") != expected_status:
            blockers.append(blocker_code)
        if require_zero_must_fix and payload.get("must_fix_count") != 0:
            blockers.append(blocker_code)
    return blockers


def run_gate_close_verification(root, batch_id):
    root = Path(root)
    manifest_path = root / ".harness/current/implementation/IMPLEMENTATION_SOURCE_MANIFEST.json"
    blockers = []
    if not manifest_path.is_file():
        return {
            "schema_version": "1.0",
            "command": "run-gate-close-verification",
            "overall_status": "fail",
            "warnings": [],
            "batch_id": batch_id,
            "source_manifest_hash": None,
            "out_of_scope_files": [],
            "test_result_summary": [],
            "review_result_summary": [],
            "gate_close_eligible": False,
            "blocker_count": 1,
            "blockers": ["gate_close.missing_implementation_source_manifest"],
            "high_finding_count": 0,
            "korean_summary": {"one_line": "Gate close 검증 실패", "blocker_count": 1, "high_finding_count": 0, "implementation_start_possible": False, "next_action": "IMPLEMENTATION_SOURCE_MANIFEST.json 생성 후 재실행"},
            "checked_at_utc": utc_now(),
            "exit_code": 1,
        }
    manifest = load_json(manifest_path)
    if manifest.get("batch_id") != batch_id:
        blockers.append("gate_close.batch_mismatch")
    if manifest.get("out_of_scope_files"):
        blockers.append("gate_close.out_of_scope_files")
    blockers.extend(check_json_status(root, manifest.get("test_evidence_paths", []), "pass", "gate_close.test_evidence_failed"))
    blockers.extend(check_json_status(root, manifest.get("review_evidence_paths", []), "pass", "gate_close.review_evidence_failed", True))
    blockers = sorted(set(blockers))
    return {
        "schema_version": "1.0",
        "command": "run-gate-close-verification",
        "overall_status": "pass" if not blockers else "fail",
        "warnings": [],
        "batch_id": batch_id,
        "source_manifest_hash": manifest.get("source_manifest_hash"),
        "out_of_scope_files": manifest.get("out_of_scope_files", []),
        "test_result_summary": manifest.get("test_evidence_paths", []),
        "review_result_summary": manifest.get("review_evidence_paths", []),
        "gate_close_eligible": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "high_finding_count": 0,
        "korean_summary": {"one_line": "Gate close 검증 통과" if not blockers else "Gate close 검증 실패", "blocker_count": len(blockers), "high_finding_count": 0, "implementation_start_possible": False, "next_action": "Gate close 가능" if not blockers else "blocker 해결 후 재실행"},
        "checked_at_utc": utc_now(),
        "exit_code": 0 if not blockers else 1,
    }
