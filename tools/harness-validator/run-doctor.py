import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from harness_validator.doctor import main


if __name__ == "__main__":
    raise SystemExit(main())
