import json
import os
import re
import sys
from pathlib import Path

from harness_validator.runtime_contract import (
    AGENTS_MAX_BYTES,
    FORBIDDEN_NAME_MARKERS,
    FORBIDDEN_PREFIXES,
    PLANNING_STAGE_FILES,
    PLANNING_STAGE_ORDER,
    READ_SET_MAX_BYTES,
    REQUIRED_FILES,
    SOURCE_IDENTITY_REQUIRED,
)


HEX_64 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
STAGE_TOKEN = re.compile(r"\bR0[0-8]\b")


def posix(path):
    return path.as_posix()


def add(blockers, code, message, path=None):
    item = {"code": code, "message": message}
    if path:
        item["path"] = path
    blockers.append(item)


def load_json(path, blockers, code):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add(blockers, code, str(exc), posix(path))
        return None


def scan_forbidden(root, blockers):
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.exists():
            continue
        rel = posix(path.relative_to(root))
        for marker in FORBIDDEN_NAME_MARKERS:
            if marker in rel:
                add(blockers, "forbidden_name", f"Forbidden name marker {marker}", rel)
        rel_prefix = rel + "/" if path.is_dir() else rel
        for prefix in FORBIDDEN_PREFIXES:
            if rel == prefix.rstrip("/") or rel_prefix.startswith(prefix):
                add(blockers, "forbidden_path", f"Forbidden runtime path {prefix}", rel)


def validate_read_set(root, blockers):
    read_set_path = root / ".harness/manifests/CURRENT_READ_SET.json"
    payload = load_json(read_set_path, blockers, "read_set_json_invalid")
    if not isinstance(payload, dict):
        return {"read_set_total_bytes": 0, "read_set_path_count": 0, "read_set_stage": None, "read_set_paths": []}

    entries = payload.get("paths")
    if not isinstance(entries, list):
        add(blockers, "read_set_paths_missing", "CURRENT_READ_SET.json must contain a paths list", posix(read_set_path))
        return {"read_set_total_bytes": 0, "read_set_path_count": 0, "read_set_stage": payload.get("stage"), "read_set_paths": []}

    total = 0
    read_set_paths = []
    for entry in entries:
        rel = entry.get("path") if isinstance(entry, dict) else None
        if not rel:
            add(blockers, "read_set_path_invalid", "Read set entry missing path", posix(read_set_path))
            continue
        if os.path.isabs(rel) or "\\" in rel or ".." in Path(rel).parts:
            add(blockers, "read_set_path_unsafe", "Read set path must be relative POSIX path", rel)
            continue
        read_set_paths.append(rel)
        if rel.startswith("tools/") or rel.startswith("_organized" + "_harness_design/"):
            add(blockers, "read_set_path_forbidden", "Read set must not point to tooling or design corpus", rel)
        full = root / rel
        if not full.exists():
            add(blockers, "read_set_missing_file", "Read set path does not exist", rel)
            continue
        if not full.is_file():
            add(blockers, "read_set_not_file", "Read set path must be a file", rel)
            continue
        total += full.stat().st_size
    if total > READ_SET_MAX_BYTES:
        add(blockers, "read_set_too_large", f"Read set total bytes {total} exceeds {READ_SET_MAX_BYTES}")
    return {
        "read_set_total_bytes": total,
        "read_set_path_count": len(entries),
        "read_set_stage": payload.get("stage"),
        "read_set_paths": read_set_paths,
    }


def validate_source_identity(root, blockers):
    path = root / ".harness/current/source_identity/SOURCE_IDENTITY.json"
    payload = load_json(path, blockers, "source_identity_json_invalid")
    if not isinstance(payload, dict):
        return
    for key in SOURCE_IDENTITY_REQUIRED:
        if key not in payload or (key != "previous_identity" and not payload.get(key)):
            add(blockers, "source_identity_missing_field", f"Missing source identity field {key}", posix(path))
    for key in ("installer_sha256", "runtime_asset_sha256"):
        value = payload.get(key)
        if value and not HEX_64.match(value):
            add(blockers, "source_identity_bad_hash", f"{key} must be 64 lowercase hex", posix(path))
    source_commit = payload.get("source_commit")
    commit_status = payload.get("source_commit_status")
    if source_commit and not GIT_SHA.match(source_commit):
        add(blockers, "source_identity_bad_commit", "source_commit must be 40 lowercase hex", posix(path))
    if not source_commit and not commit_status:
        add(blockers, "source_identity_missing_commit_status", "source_commit or source_commit_status is required", posix(path))


def parse_status_stage(root, blockers):
    status_path = root / ".harness/current/status/STATUS_KO.md"
    try:
        text = status_path.read_text(encoding="utf-8")
    except Exception as exc:
        add(blockers, "status_read_failed", str(exc), posix(status_path))
        return None
    for line in text.splitlines():
        if "현재 단계" in line:
            match = STAGE_TOKEN.search(line)
            if match:
                return match.group(0)
    matches = STAGE_TOKEN.findall(text)
    if not matches:
        return None
    return matches[-1]


def validate_workflow_state(root, blockers, read_set_metrics):
    status_stage = parse_status_stage(root, blockers)
    read_set_stage = read_set_metrics.get("read_set_stage")
    read_set_paths = set(read_set_metrics.get("read_set_paths") or [])
    planning_root = root / ".harness/current/planning"
    planning_files = []
    if planning_root.exists():
        planning_files = [path for path in planning_root.rglob("*") if path.is_file()]

    if planning_files and status_stage in (None, "R00"):
        add(
            blockers,
            "workflow_state_conflict",
            "Planning artifacts exist but STATUS_KO.md is still at initial install state",
            ".harness/current/status/STATUS_KO.md",
        )

    if status_stage in PLANNING_STAGE_ORDER:
        if read_set_stage and not str(read_set_stage).startswith(status_stage):
            add(
                blockers,
                "workflow_read_set_stage_conflict",
                f"Read set stage {read_set_stage} does not match current status stage {status_stage}",
                ".harness/manifests/CURRENT_READ_SET.json",
            )
        required_stages = PLANNING_STAGE_ORDER[: PLANNING_STAGE_ORDER.index(status_stage) + 1]
        for stage in required_stages:
            required_path = PLANNING_STAGE_FILES[stage]
            if not (root / required_path).is_file():
                add(blockers, "workflow_missing_stage_artifact", f"Missing planning artifact for {stage}", required_path)
            if required_path not in read_set_paths:
                add(blockers, "workflow_read_set_missing_stage_artifact", f"Read set omits planning artifact for {stage}", required_path)


def validate(root):
    blockers = []
    root = root.resolve()
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            add(blockers, "required_file_missing", "Required runtime file missing", rel)
    agents = root / "AGENTS.md"
    if agents.is_file():
        size = agents.stat().st_size
        if size > AGENTS_MAX_BYTES:
            add(blockers, "agents_too_large", f"AGENTS.md size {size} exceeds {AGENTS_MAX_BYTES}", "AGENTS.md")
        text = agents.read_text(encoding="utf-8")
        if "unittest" + " discover" in text or ("tools/harness-validator/" + "tests") in text:
            add(blockers, "agents_forbidden_test_command", "AGENTS.md must point to runtime doctor, not engineering tests", "AGENTS.md")
    scan_forbidden(root, blockers)
    metrics = validate_read_set(root, blockers)
    validate_source_identity(root, blockers)
    validate_workflow_state(root, blockers, metrics)
    metrics["blocker_count"] = len(blockers)
    return {
        "overall_status": "pass" if not blockers else "fail",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "metrics": metrics,
    }


def main(argv=None):
    argv = list(argv or sys.argv[1:])
    root = Path(argv[0]) if argv else Path.cwd()
    result = validate(root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["blocker_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
