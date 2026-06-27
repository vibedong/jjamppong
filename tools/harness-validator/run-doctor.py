import argparse
import json
from pathlib import Path

from harness_validator.doctor import validate


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("release-payload", "installed-project"), default="installed-project")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    result = validate(Path(args.root), mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
