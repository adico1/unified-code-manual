"""One operation from calculator seeds to self-tested lazy applications."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_all import generate_all_from_seeds


def single_api():
    return generate_all_from_seeds(self_test=True)


def main():
    result = single_api()
    print(json.dumps({"singleApi": result}, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
