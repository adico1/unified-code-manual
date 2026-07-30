"""Migrate and maintain the content-addressed seed ancestry graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = ROOT / "seed"
SEEDS = SEED_ROOT / "applications"
BASES = SEED_ROOT / "bases"
WITHOUT_WHAT = BASES / "בלי_מה.seed.json"
CALCULATOR_FAMILY = SEED_ROOT / "families" / "calculator.seed.json"
LEAF_FORMAT = "manual-what-seed-3"
BASE_FORMAT = "manual-seed-base-1"
LEGACY_FORMAT = "manual-seed-program-2"


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def pretty(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def base_reference(owner, target, document):
    return {
        "identity": document["identity"],
        "path": Path(os.path.relpath(target, owner.parent)).as_posix(),
        "sha256": digest(document),
    }


def leaf_paths():
    return sorted(
        path
        for path in SEEDS.glob("*.seed.json")
        if path.is_file()
    )


def migrate_leaf(path, family_document):
    document = load(path)
    if document.get("format") == LEGACY_FORMAT:
        what = {
            key: value
            for key, value in document.items()
            if key != "format"
        }
    elif document.get("format") == LEAF_FORMAT:
        what = document["what"]
    else:
        raise ValueError(f"unsupported-seed:{path.name}")
    return {
        "format": LEAF_FORMAT,
        "bases": [
            base_reference(path, CALCULATOR_FAMILY, family_document)
        ],
        "what": what,
    }


def expected_documents():
    if not WITHOUT_WHAT.exists() or not CALCULATOR_FAMILY.exists():
        raise ValueError("missing-base-authority")
    root_document = load(WITHOUT_WHAT)
    family_document = load(CALCULATOR_FAMILY)
    if (
        root_document.get("format") != BASE_FORMAT
        or root_document.get("bases") != []
        or family_document.get("format") != BASE_FORMAT
    ):
        raise ValueError("invalid-base-authority")
    family_document["bases"] = [
        base_reference(CALCULATOR_FAMILY, WITHOUT_WHAT, root_document)
    ]
    leaves = {
        path: migrate_leaf(path, family_document)
        for path in leaf_paths()
    }
    return {
        WITHOUT_WHAT: root_document,
        CALCULATOR_FAMILY: family_document,
        **leaves,
    }


def apply_documents(documents):
    BASES.mkdir(parents=True, exist_ok=True)
    changed = []
    for path, document in documents.items():
        content = pretty(document)
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def check_documents(documents):
    differences = [
        path.relative_to(ROOT).as_posix()
        for path, document in documents.items()
        if not path.exists() or path.read_bytes() != pretty(document)
    ]
    if differences:
        raise ValueError("seed-graph-not-canonical:" + ",".join(differences))
    return len(documents)


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    documents = expected_documents()
    result = (
        {"changed": apply_documents(documents)}
        if arguments.apply
        else {"verified": check_documents(documents)}
    )
    result.update(
        {
            "base_seed": documents[WITHOUT_WHAT]["identity"],
            "leaf_seeds": len(leaf_paths()),
        }
    )
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
