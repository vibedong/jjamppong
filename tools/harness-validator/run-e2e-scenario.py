import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_validator.e2e_scenario import run_scenario


parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("--scenario", required=True)
args = parser.parse_args()
result = run_scenario(Path(args.root), args.scenario)
print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
raise SystemExit(result["exit_code"])
