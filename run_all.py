"""Generate and display every enabled calculator in showcase.json."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "showcase.json"


def load_catalog():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("format") != "manual-calculator-showcase-1":
        raise ValueError("unsupported-showcase")
    calculators = [
        item for item in catalog.get("calculators", ()) if item.get("enabled")
    ]
    if not calculators:
        raise ValueError("no-enabled-calculators")
    return calculators


def generate(calculator):
    generator_path = ROOT / calculator["generator"]
    specification = importlib.util.spec_from_file_location(
        "showcase_" + calculator["id"].replace("-", "_"),
        generator_path,
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    arguments = [
        ROOT / calculator["seed"],
        ROOT / calculator["output"],
    ]
    if calculator.get("profile_id"):
        arguments.append(calculator["profile_id"])
    evidence = module.generate(*arguments)
    return {
        "id": calculator["id"],
        "title": calculator["title"],
        "application": ROOT / calculator["output"] / "main.py",
        "evidence": evidence,
    }


def launch(generated):
    return [
        {
            **item,
            "process": subprocess.Popen(
                [sys.executable, str(item["application"])],
                cwd=item["application"].parent,
            ),
        }
        for item in generated
    ]


def tree_bytes(path):
    return {
        item.name: item.read_bytes()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def verify_exact_rebuild(calculators, generated):
    first = {
        item["id"]: tree_bytes(item["application"].parent)
        for item in generated
    }
    if any(set(files) != {"main.py", "manifest.json"} for files in first.values()):
        raise ValueError("non-specialized-output")
    second = [generate(calculator) for calculator in calculators]
    if any(
        first[item["id"]] != tree_bytes(item["application"].parent)
        for item in second
    ):
        raise ValueError("non-deterministic-output")
    forbidden = (
        b"profile.json",
        b"calculator_runtime",
        b"read_text(",
        b"read_bytes(",
    )
    if any(
        token in files["main.py"]
        for files in first.values()
        for token in forbidden
    ):
        raise ValueError("runtime-authority-leak")
    return second


def wait_for_windows(running):
    try:
        while any(item["process"].poll() is None for item in running):
            time.sleep(0.1)
    except KeyboardInterrupt:
        for item in running:
            if item["process"].poll() is None:
                item["process"].terminate()
        for item in running:
            item["process"].wait()
    return max((item["process"].returncode or 0) for item in running)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate and verify all calculators without opening windows.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List every enabled calculator without generating it.",
    )
    arguments = parser.parse_args(argv)
    calculators = load_catalog()
    if arguments.list:
        for calculator in calculators:
            print(f"{calculator['id']}: {calculator['title']}")
        return 0
    generated = verify_exact_rebuild(
        calculators,
        [generate(calculator) for calculator in calculators],
    )
    for item in generated:
        identity = item["evidence"].get(
            "seed_sha256",
            item["evidence"]["files"]["main.py"],
        )
        passed = item["evidence"]["verification"]["passed"]
        total = item["evidence"]["verification"]["total"]
        print(
            f"generated {item['id']}: {identity} acceptance={passed}/{total}",
            flush=True,
        )
    print(
        "proof: exact-output=PASS deterministic=PASS runtime-authority-leak=0",
        flush=True,
    )
    if arguments.generate_only:
        return 0
    running = launch(generated)
    for item in running:
        print(
            f"opened {item['id']}: pid={item['process'].pid}",
            flush=True,
        )
    return wait_for_windows(running)


if __name__ == "__main__":
    raise SystemExit(main())
