import json
from pathlib import Path


def dumps_canonical_json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def write_canonical_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps_canonical_json(payload), encoding="utf-8", newline="\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
