"""One operation from independent seeds to self-tested lazy applications."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_all import generate_all_from_seeds

MAX_VERIFICATION_SECONDS = 5.0


def single_api():
    return generate_all_from_seeds(self_test=True)


def main():
    started = time.perf_counter()
    result = single_api()
    elapsed = time.perf_counter() - started
    if elapsed > MAX_VERIFICATION_SECONDS:
        raise RuntimeError(
            f"verification-budget-exceeded:{elapsed:.6f}>"
            f"{MAX_VERIFICATION_SECONDS:.6f}"
        )
    print(
        json.dumps(
            {
                "singleApi": result,
                "verification_seconds": round(elapsed, 6),
            },
            sort_keys=True,
        )
    )
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
