"""One operation from independent seeds to self-tested lazy applications."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_all import generate_all_from_seeds
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from root_authority import verify_root

MAX_VERIFICATION_SECONDS = 5.0
ROOT = Path(__file__).resolve().parents[1]


def single_api():
    root = verify_root(
        Path(__file__).resolve().parents[1] / "seed" / "ROOT.seed.json"
    )
    result = generate_all_from_seeds(self_test=True)
    return {**result, "root": root}


def verify_complete():
    started = time.perf_counter()
    unit = subprocess.Popen(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        result = single_api()
        unit_output, unit_error = unit.communicate(
            timeout=MAX_VERIFICATION_SECONDS
        )
    except BaseException:
        unit.kill()
        unit.communicate()
        raise
    elapsed = time.perf_counter() - started
    if unit.returncode:
        raise RuntimeError(
            "unit-verification-failed:" + (unit_error.strip() or unit_output.strip())
        )
    unit_evidence = unit_output + "\n" + unit_error
    unit_match = re.search(r"Ran (\d+) tests? in", unit_evidence)
    if unit_match is None:
        raise RuntimeError("unit-verification-evidence-missing")
    if elapsed > MAX_VERIFICATION_SECONDS:
        raise RuntimeError(
            f"verification-budget-exceeded:{elapsed:.6f}>"
            f"{MAX_VERIFICATION_SECONDS:.6f}"
        )
    return {**result, "unit_tests": int(unit_match.group(1))}, elapsed


def main():
    result, elapsed = verify_complete()
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
