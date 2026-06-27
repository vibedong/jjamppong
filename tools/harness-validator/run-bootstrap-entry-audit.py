import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_validator.bootstrap_audit import run_bootstrap_entry_audit


parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("--batch", required=True)
args = parser.parse_args()
result = run_bootstrap_entry_audit(Path(args.root), args.batch)
print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
raise SystemExit(result["exit_code"])
