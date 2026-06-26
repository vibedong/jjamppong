from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


FINAL_RELEASE_BLOCKERS = (
    "unresolved_must_fix",
    "creator_decision_needed",
    "backtrack_needed",
    "review_conflict",
    "stale_work_unit_identity",
    "unapproved_work_unit_completion",
    "missing_completion_evidence",
    "missing_test_target_evidence",
    "secret_scan_finding",
    "github_remote_tag_mismatch",
    "release_artifact_hash_mismatch",
    "final_validator_failure",
    "ac_coverage_gap",
    "cqe_coverage_gap",
    "test_target_coverage_gap",
    "tree_inventory_hash_mismatch",
    "duplicate_scan_finding",
    "classification_scan_finding",
    "final_source_manifest_tag_mismatch",
    "release_notes_policy_failure",
    "archive_export_or_asset_missing",
    "release_guidance_missing",
)


SECRET_ASSIGNMENT_PATTERNS = (
    re.compile(
        r"(?i)[\"']?(?P<key>[a-z0-9_.-]+(?:[_-][a-z0-9_.-]+)*)[\"']?\s*[:=]\s*"
        r"[\"']?(?P<value>[^\"'\s,}]{8,})"
    ),
)


ROOT_DUPLICATE_PATTERNS = (
    re.compile(r"^GPT_PRO_.*\.(md|zip)$", re.IGNORECASE),
    re.compile(r"^HARNESS_.*(AUDIT|REGRESSION|GOAL).*\.(md|zip)$", re.IGNORECASE),
    re.compile(r"^_organized_harness_design.*\.zip$", re.IGNORECASE),
)


CLASSIFIED_ROOT_PREFIXES = (
    ".harness/",
    "_organized_harness_design/",
    "HARNESS_1_0_IMPLEMENTATION_ENTRY_GOALS/",
    "docs/",
    "tests/",
    "tools/",
)


CLASSIFIED_ROOT_FILES = {"AGENTS.md", ".gitignore", "README.md", "install-harness.ps1"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _canonical_json(value) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256_text(text)


def _write_text(path: Path, value: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")
    return _sha256_text(value)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.as_posix()}:{line_number}: JSONL row must be object")
        rows.append(value)
    return rows


def _source_paths(source_root: Path) -> dict[str, Path]:
    return {
        "approval_targets": source_root
        / "_organized_harness_design"
        / "manifests"
        / "WORK_UNIT_APPROVAL_TARGET_LIST_V1_0.jsonl",
        "ac_registry": source_root
        / "_organized_harness_design"
        / "active"
        / "current-stage"
        / "technical-architecture"
        / "TECHNICAL_ARCHITECTURE_ACCEPTANCE_CRITERION_TRACE_REGISTRY_V1_2.jsonl",
        "cqe_catalog": source_root
        / "_organized_harness_design"
        / "active"
        / "current-stage"
        / "technical-architecture"
        / "TECHNICAL_ARCHITECTURE_COMMAND_QUERY_EVENT_CATALOG_V1_2.json",
        "test_target_registry": source_root
        / "_organized_harness_design"
        / "active"
        / "current-stage"
        / "work-units"
        / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl",
    }


def _load_source_universe(source_root: Path) -> dict[str, set[str]]:
    paths = _source_paths(source_root)
    approved = _read_jsonl(paths["approval_targets"])
    ac_rows = _read_jsonl(paths["ac_registry"])
    cqe = _read_json(paths["cqe_catalog"])
    tt_rows = _read_jsonl(paths["test_target_registry"])
    entries = cqe.get("entries")
    if not isinstance(entries, list):
        raise ValueError("CQE catalog entries must be a list")
    return {
        "approved_work_units": {str(row["work_unit_id"]) for row in approved},
        "acceptance_criteria": {str(row["registry_id"]) for row in ac_rows},
        "command_query_event": {str(row["id"]) for row in entries if isinstance(row, dict) and "id" in row},
        "test_targets": {str(row["test_target_id"]) for row in tt_rows},
    }


def _add_string_or_list(target: set[str], value: Any) -> None:
    if isinstance(value, str):
        target.add(value)
    elif isinstance(value, list):
        target.update(str(item) for item in value if item)


def _collect_evidence(root: Path, approved_work_units: set[str]) -> dict[str, Any]:
    evidence_root = root / ".harness" / "evidence" / "work-units"
    actual_work_units = {path.name for path in evidence_root.iterdir() if path.is_dir()} if evidence_root.exists() else set()
    missing_work_units = sorted(approved_work_units - actual_work_units)
    extra_work_units = sorted(actual_work_units - approved_work_units)
    covered_ac: set[str] = set()
    covered_cqe: set[str] = set()
    covered_tt: set[str] = set()
    missing_completion: list[str] = []
    missing_tests: list[str] = []
    failing_tests: list[str] = []
    invalid_evidence: list[str] = []
    failed_completion: list[str] = []

    for work_unit_id in sorted(approved_work_units):
        unit_dir = evidence_root / work_unit_id
        if not unit_dir.exists():
            missing_completion.append(work_unit_id)
            missing_tests.append(work_unit_id)
            continue

        completion_path = unit_dir / "completion-evidence.json"
        handoff_paths = sorted(unit_dir.glob("handoff*.json"))
        if not completion_path.exists() and not handoff_paths:
            missing_completion.append(work_unit_id)

        payload_paths = ([completion_path] if completion_path.exists() else []) + handoff_paths
        for payload_path in payload_paths:
            try:
                payload = _read_json(payload_path)
            except (OSError, json.JSONDecodeError) as exc:
                invalid_evidence.append(f"{work_unit_id}: {payload_path.name}: {exc}")
                continue
            if not isinstance(payload, dict):
                invalid_evidence.append(f"{work_unit_id}: {payload_path.name}: JSON object required")
                continue
            if payload_path == completion_path:
                if payload.get("completion_result") != "pass" and payload.get("verification_result") != "pass":
                    failed_completion.append(f"{work_unit_id}: {payload_path.name}: result not pass")
            elif payload_path.name.startswith("handoff"):
                if payload.get("verification_result") != "pass" and payload.get("handoff_contract_verified") is not True:
                    failed_completion.append(f"{work_unit_id}: {payload_path.name}: verification not pass")
            _add_string_or_list(covered_ac, payload.get("acceptance_criterion_id"))
            _add_string_or_list(covered_ac, payload.get("acceptance_criterion_ids"))
            _add_string_or_list(covered_ac, payload.get("direct_acceptance_criteria"))
            _add_string_or_list(covered_ac, payload.get("direct_acceptance_criterion_ids"))
            _add_string_or_list(covered_cqe, payload.get("command_query_event_ids"))
            _add_string_or_list(covered_cqe, payload.get("public_interfaces"))
            _add_string_or_list(covered_cqe, payload.get("provided_interfaces"))
            _add_string_or_list(covered_tt, payload.get("test_target_ids"))

        test_path = unit_dir / "test-results.jsonl"
        if not test_path.exists() or not test_path.is_file():
            missing_tests.append(work_unit_id)
            continue
        try:
            rows = _read_jsonl(test_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            invalid_evidence.append(f"{work_unit_id}: test-results.jsonl: {exc}")
            continue
        if not rows:
            missing_tests.append(work_unit_id)
            continue
        for row in rows:
            if row.get("result") != "pass":
                failing_tests.append(work_unit_id)
            _add_string_or_list(covered_tt, row.get("test_target_id"))

    return {
        "actual_work_units": actual_work_units,
        "missing_work_units": missing_work_units,
        "extra_work_units": extra_work_units,
        "covered_acceptance_criteria": covered_ac,
        "covered_command_query_event": covered_cqe,
        "covered_test_targets": covered_tt,
        "missing_completion": sorted(set(missing_completion)),
        "missing_tests": sorted(set(missing_tests)),
        "failing_tests": sorted(set(failing_tests)),
        "invalid_evidence": invalid_evidence,
        "failed_completion": failed_completion,
    }


def _coverage_section(expected: set[str], covered: set[str]) -> dict[str, Any]:
    missing = sorted(expected - covered)
    extra = sorted(covered - expected)
    return {
        "expected_count": len(expected),
        "covered_count": len(expected & covered),
        "missing_count": len(missing),
        "missing_ids": missing,
        "extra_observed_ids": extra,
        "coverage_hash": _sha256_text(_canonical_json(sorted(expected & covered))),
    }


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = set(path.relative_to(root).parts)
        if ".git" in parts or ".worktrees" in parts or "__pycache__" in parts:
            continue
        if rel.endswith(".pyc"):
            continue
        if rel.startswith(".harness/evidence/release-candidate/"):
            continue
        yield rel, path


def _tree_inventory(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for rel, path in _iter_files(root):
        data = path.read_bytes()
        rows.append({"path": rel, "size": len(data), "sha256": _sha256_bytes(data)})
    return {
        "file_count": len(rows),
        "inventory_hash": _sha256_text(_canonical_json(rows)),
        "files": rows,
    }


def _root_duplicate_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        if name in CLASSIFIED_ROOT_FILES or name == ".git":
            continue
        if any(pattern.match(name) for pattern in ROOT_DUPLICATE_PATTERNS):
            findings.append(name)
    return findings


def _classification_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for rel, _path in _iter_files(root):
        if rel in CLASSIFIED_ROOT_FILES:
            continue
        if any(rel.startswith(prefix) for prefix in CLASSIFIED_ROOT_PREFIXES):
            continue
        findings.append(rel)
    return findings


def _secret_findings(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for rel, path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            for pattern in SECRET_ASSIGNMENT_PATTERNS:
                match = pattern.search(line)
                if match and _is_sensitive_assignment_key(match.group("key")):
                    findings.append({"path": rel, "marker": "secret_assignment"})
                    break
            else:
                continue
            break
    return findings


def _is_sensitive_assignment_key(raw_key: str) -> bool:
    key = raw_key.lower().replace("-", "_")
    if key in {"secret_scan_finding", "secret_findings"} or key.endswith("_finding") or key.endswith("_findings"):
        return False
    safe_token_keys = {
        "expected_token_cost",
        "token_cost",
        "token_quality_measurement",
        "tokens_used",
        "remaining_tokens",
    }
    if key in safe_token_keys:
        return False
    sensitive_terms = (
        "api_key",
        "apikey",
        "password",
        "auth_token",
        "authentication_token",
        "recovery_code",
        "client_secret",
        "secret_access_key",
        "access_token",
        "github_token",
    )
    return any(term in key for term in sensitive_terms) or key.endswith("_secret")


def _git_head(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _remote_tag_status(root: Path, tag: str) -> dict[str, Any]:
    status = {
        "tag": tag,
        "local_tag_commit": None,
        "remote_tag_commit": None,
        "remote_tag_verified": False,
        "mismatch": False,
    }
    try:
        status["local_tag_commit"] = subprocess.check_output(
            ["git", "rev-list", "-n", "1", tag], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        status["mismatch"] = True
        return status
    try:
        output = subprocess.check_output(
            ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        status["mismatch"] = True
        return status
    if not output:
        status["mismatch"] = True
        return status
    status["remote_tag_commit"] = output.split()[0]
    status["remote_tag_verified"] = status["remote_tag_commit"] == status["local_tag_commit"]
    status["mismatch"] = not status["remote_tag_verified"]
    return status


def _release_closure_checks(
    coverage: dict[str, Any],
    blockers: dict[str, int],
    require_remote_tag: bool,
) -> dict[str, dict[str, Any]]:
    return {
        "REL-CLOSE-01": {
            "surface": "AC/CQE/test target coverage closure",
            "status": "pass"
            if coverage["acceptance_criteria"]["missing_count"] == 0
            and coverage["command_query_event"]["missing_count"] == 0
            and coverage["test_targets"]["missing_count"] == 0
            else "fail",
            "evidence": {
                "acceptance_criteria": coverage["acceptance_criteria"]["coverage_hash"],
                "command_query_event": coverage["command_query_event"]["coverage_hash"],
                "test_targets": coverage["test_targets"]["coverage_hash"],
            },
        },
        "REL-CLOSE-02": {
            "surface": "Final validator pass",
            "status": "pass" if blockers["final_validator_failure"] == 0 else "fail",
            "evidence": "final_release_blockers.final_validator_failure",
        },
        "REL-CLOSE-03": {
            "surface": "Secret exclusion and forbidden file scan",
            "status": "pass" if blockers["secret_scan_finding"] == 0 else "fail",
            "evidence": "secret_findings",
        },
        "REL-CLOSE-04": {
            "surface": "Tree inventory, duplicate scan, classification scan",
            "status": "pass"
            if blockers["tree_inventory_hash_mismatch"] == 0
            and blockers["duplicate_scan_finding"] == 0
            and blockers["classification_scan_finding"] == 0
            else "fail",
            "evidence": "tree_inventory.inventory_hash",
        },
        "REL-CLOSE-05": {
            "surface": "Release candidate manifest and review packet",
            "status": "pass" if blockers["archive_export_or_asset_missing"] == 0 else "fail",
            "evidence": ".harness/evidence/release-candidate/RELEASE_CANDIDATE_MANIFEST_V1_0.json",
        },
        "REL-CLOSE-06": {
            "surface": "Git tag and remote verification",
            "status": "pending_final_release_tag" if not require_remote_tag else "pass",
            "evidence": "tag_status",
        },
        "REL-CLOSE-07": {
            "surface": "GitHub Release verification",
            "status": "not_applicable_for_release_candidate" if not require_remote_tag else "pending_github_release",
            "evidence": "public GitHub Release is deferred for release candidate mode",
        },
        "REL-CLOSE-08": {
            "surface": "Archive/export and user guidance",
            "status": "pass"
            if blockers["archive_export_or_asset_missing"] == 0 and blockers["release_guidance_missing"] == 0
            else "fail",
            "evidence": [
                ".harness/evidence/release-candidate/RELEASE_GUIDANCE_KO_V1_0.md",
                ".harness/evidence/release-candidate/TREE_INVENTORY_V1_0.jsonl",
            ],
        },
    }


def validate_release_candidate(
    root: Path | str,
    source_root: Path | str,
    tag: str,
    require_remote_tag: bool = False,
) -> dict[str, Any]:
    root = Path(root)
    source_root = Path(source_root)
    blockers = {name: 0 for name in FINAL_RELEASE_BLOCKERS}
    content_errors: list[str] = []
    try:
        universe = _load_source_universe(source_root)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        universe = {
            "approved_work_units": set(),
            "acceptance_criteria": set(),
            "command_query_event": set(),
            "test_targets": set(),
        }
        content_errors.append(f"source universe load failure: {exc}")
        blockers["final_validator_failure"] = 1

    evidence = _collect_evidence(root, universe["approved_work_units"]) if universe["approved_work_units"] else {
        "actual_work_units": set(),
        "missing_work_units": [],
        "extra_work_units": [],
        "covered_acceptance_criteria": set(),
        "covered_command_query_event": set(),
        "covered_test_targets": set(),
        "missing_completion": [],
        "missing_tests": [],
        "failing_tests": [],
        "invalid_evidence": [],
    }
    ac_coverage = _coverage_section(universe["acceptance_criteria"], evidence["covered_acceptance_criteria"])
    cqe_coverage = _coverage_section(universe["command_query_event"], evidence["covered_command_query_event"])
    tt_coverage = _coverage_section(universe["test_targets"], evidence["covered_test_targets"])
    if ac_coverage["missing_count"]:
        blockers["ac_coverage_gap"] = 1
    if cqe_coverage["missing_count"]:
        blockers["cqe_coverage_gap"] = 1
    if tt_coverage["missing_count"]:
        blockers["test_target_coverage_gap"] = 1
    if (
        evidence["missing_work_units"]
        or evidence["missing_completion"]
        or evidence["invalid_evidence"]
        or evidence["failed_completion"]
    ):
        blockers["missing_completion_evidence"] = 1
    if evidence["missing_tests"] or evidence["failing_tests"]:
        blockers["missing_test_target_evidence"] = 1
    if evidence["extra_work_units"]:
        blockers["unapproved_work_unit_completion"] = 1

    secret_findings = _secret_findings(root)
    duplicate_findings = _root_duplicate_findings(root)
    classification_findings = _classification_findings(root)
    if secret_findings:
        blockers["secret_scan_finding"] = 1
    if duplicate_findings:
        blockers["duplicate_scan_finding"] = 1
    if classification_findings:
        blockers["classification_scan_finding"] = 1
    tag_status = _remote_tag_status(root, tag) if require_remote_tag else {
        "tag": tag,
        "local_tag_commit": None,
        "remote_tag_commit": None,
        "remote_tag_verified": False,
        "mismatch": False,
        "candidate_mode_remote_tag_not_required": True,
    }
    if tag_status["mismatch"]:
        blockers["github_remote_tag_mismatch"] = 1

    inventory = _tree_inventory(root)
    if not re.fullmatch(r"[0-9a-f]{64}", inventory["inventory_hash"]):
        blockers["tree_inventory_hash_mismatch"] = 1
    release_guidance_path = root / ".harness" / "evidence" / "release-candidate" / "RELEASE_GUIDANCE_KO_V1_0.md"
    if not release_guidance_path.exists():
        blockers["release_guidance_missing"] = 1
    release_manifest_path = root / ".harness" / "evidence" / "release-candidate" / "RELEASE_CANDIDATE_MANIFEST_V1_0.json"
    if not release_manifest_path.exists():
        blockers["archive_export_or_asset_missing"] = 1

    validation_passed = all(value == 0 for value in blockers.values())
    if not validation_passed and blockers["final_validator_failure"] == 0:
        blockers["final_validator_failure"] = 1
    result = {
        "artifact_id": "harness.release_candidate.final_closure",
        "artifact_version": "1.0",
        "tag": tag,
        "head": _git_head(root),
        "validation_passed": all(value == 0 for key, value in blockers.items() if key != "final_validator_failure")
        and blockers["final_validator_failure"] == 0,
        "final_release_blockers": blockers,
        "coverage": {
            "work_units": {
                "expected_count": len(universe["approved_work_units"]),
                "evidence_count": len(evidence["actual_work_units"] & universe["approved_work_units"]),
                "missing_count": len(evidence["missing_work_units"]),
                "extra_count": len(evidence["extra_work_units"]),
                "missing_ids": evidence["missing_work_units"],
                "extra_ids": evidence["extra_work_units"],
            },
            "acceptance_criteria": ac_coverage,
            "command_query_event": cqe_coverage,
            "test_targets": tt_coverage,
        },
        "evidence_errors": {
            "missing_completion": evidence["missing_completion"],
            "missing_tests": evidence["missing_tests"],
            "failing_tests": evidence["failing_tests"],
            "invalid_evidence": evidence["invalid_evidence"],
            "failed_completion": evidence["failed_completion"],
        },
        "secret_findings": secret_findings,
        "duplicate_scan_findings": duplicate_findings,
        "classification_scan_findings": classification_findings,
        "tree_inventory": {
            "file_count": inventory["file_count"],
            "inventory_hash": inventory["inventory_hash"],
        },
        "tag_status": tag_status,
    }
    result["validation_passed"] = all(value == 0 for value in result["final_release_blockers"].values())
    result["release_closure_checks"] = _release_closure_checks(
        result["coverage"], result["final_release_blockers"], require_remote_tag
    )
    return result


def build_release_candidate(
    root: Path | str,
    source_root: Path | str,
    tag: str,
    require_remote_tag: bool = False,
) -> dict[str, Any]:
    root = Path(root)
    evidence_dir = root / ".harness" / "evidence" / "release-candidate"
    guidance = (
        "# Harness 1.0 Release Candidate Guidance\n\n"
        f"- 후보 태그: `{tag}`\n"
        "- 목적: Harness 1.0 릴리스 후보의 검증 증거와 사용 안내를 고정한다.\n"
        "- 금지: secret, API key, password, authentication token, recovery code를 Git 또는 일반 문서에 저장하지 않는다.\n"
        "- 공개 GitHub Release는 별도 최종 확인 뒤 exact tag 기준으로만 생성한다.\n"
    )
    guidance_sha = _write_text(evidence_dir / "RELEASE_GUIDANCE_KO_V1_0.md", guidance)
    inventory = _tree_inventory(root)
    inventory_path = evidence_dir / "TREE_INVENTORY_V1_0.jsonl"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_text = "".join(_canonical_json(row) + "\n" for row in inventory["files"])
    inventory_path.write_text(inventory_text, encoding="utf-8", newline="\n")
    inventory_file_sha = _sha256_text(inventory_text)
    manifest_path = evidence_dir / "RELEASE_CANDIDATE_MANIFEST_V1_0.json"
    _write_json(manifest_path, {"release_candidate_manifest_status": "provisional_manifest_asset"})
    final_result = validate_release_candidate(root, source_root, tag, require_remote_tag=require_remote_tag)
    manifest = dict(final_result)
    manifest.update(
        {
            "release_candidate_manifest_status": "candidate_ready_for_review" if final_result["validation_passed"] else "blocked",
            "release_guidance_path": ".harness/evidence/release-candidate/RELEASE_GUIDANCE_KO_V1_0.md",
            "release_guidance_sha256": guidance_sha,
            "tree_inventory_path": ".harness/evidence/release-candidate/TREE_INVENTORY_V1_0.jsonl",
            "tree_inventory_file_sha256": inventory_file_sha,
        }
    )
    manifest_sha = _write_json(manifest_path, manifest)
    final_result = validate_release_candidate(root, source_root, tag, require_remote_tag=require_remote_tag)
    final_result["release_candidate_manifest_path"] = ".harness/evidence/release-candidate/RELEASE_CANDIDATE_MANIFEST_V1_0.json"
    final_result["release_candidate_manifest_sha256"] = manifest_sha
    _write_json(evidence_dir / "FINAL_RELEASE_CLOSURE_RESULT_V1_0.json", final_result)
    return final_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--tag", default="harness-v1.0.0-rc.1")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-remote-tag", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        result = build_release_candidate(args.root, args.source_root, args.tag, args.require_remote_tag)
    else:
        result = validate_release_candidate(args.root, args.source_root, args.tag, args.require_remote_tag)
    print(_canonical_json(result))
    return 0 if result["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
