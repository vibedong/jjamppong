import os
from pathlib import Path


def normalize_relative_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    normalized = value.replace("\\", "/").strip("/")
    if os.path.isabs(value) or normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("path must be project-relative")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("path must not be empty")
    return normalized


def to_posix_relative(path, root):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
