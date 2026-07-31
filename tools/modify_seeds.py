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
REGISTRIES = SEED_ROOT / "registries"
WITHOUT_WHAT = BASES / "בלי_מה.seed.json"
KEY_REGISTRY = REGISTRIES / "calculator-keys.seed.json"
CALCULATOR_FAMILY = SEED_ROOT / "families" / "calculator.seed.json"
LEAF_FORMAT = "manual-what-seed-4"
BASE_FORMAT = "manual-seed-base-1"


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


def key_definitions(registry_document):
    definitions = registry_document["provides"]["key_registry"]
    identities = [item["identity"] for item in definitions]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate-key-identity")
    return definitions


def key_placements(presentation, registry_document):
    if "keys" in presentation:
        return presentation["keys"]
    definitions = key_definitions(registry_document)
    by_meaning = {
        canonical(
            {
                name: value
                for name, value in item.items()
                if name not in {"identity", "requires"}
            }
        ): item["identity"]
        for item in definitions
    }
    placements = []
    for control in presentation["controls"]:
        meaning = canonical(
            {
                name: value
                for name, value in control.items()
                if name not in {"id", "row", "column"}
            }
        )
        if meaning not in by_meaning:
            raise ValueError("unregistered-key:" + control["id"])
        placements.append(
            {
                "key": by_meaning[meaning],
                "row": control["row"],
                "column": control["column"],
            }
        )
    return placements


def concise_what(what, registry_document):
    program = what["program"]
    if "ast" in program:
        raise ValueError("legacy-ast-not-supported")
    concise = {
        **what,
        "presentation": {
            **{
                name: value
                for name, value in what["presentation"].items()
                if name not in {"controls", "keys"}
            },
            "keys": key_placements(what["presentation"], registry_document),
        },
        "state": {
            **what["state"],
            "authority": "declarations",
            "initial": what["state"]["initial"],
        },
        "program": {
            "language": "calculator-declaration-1",
            "case_entrypoint": program["case_entrypoint"],
            "launch_entrypoint": program["launch_entrypoint"],
        },
    }
    concise.pop("transitions", None)
    concise.pop("boundaries", None)
    laws = concise["semantics"]["numeric_laws"]
    concise["semantics"]["numeric_laws"] = {
        key: value
        for key, value in laws.items()
        if key not in {"constants", "functions", "operators", "unary"}
    }
    concise["semantics"].pop("validation", None)
    return concise


def migrate_leaf(path, family_document, registry_document):
    document = load(path)
    if document.get("format") == LEAF_FORMAT:
        what = document["what"]
    else:
        raise ValueError(f"unsupported-seed:{path.name}")
    return {
        "format": LEAF_FORMAT,
        "bases": [
            base_reference(path, CALCULATOR_FAMILY, family_document)
        ],
        "what": concise_what(what, registry_document),
    }


def expected_documents():
    if (
        not WITHOUT_WHAT.exists()
        or not KEY_REGISTRY.exists()
        or not CALCULATOR_FAMILY.exists()
    ):
        raise ValueError("missing-base-authority")
    root_document = load(WITHOUT_WHAT)
    registry_document = load(KEY_REGISTRY)
    family_document = load(CALCULATOR_FAMILY)
    if (
        root_document.get("format") != BASE_FORMAT
        or root_document.get("bases") != []
        or registry_document.get("format") != BASE_FORMAT
        or family_document.get("format") != BASE_FORMAT
    ):
        raise ValueError("invalid-base-authority")
    registry_document["bases"] = [
        base_reference(KEY_REGISTRY, WITHOUT_WHAT, root_document)
    ]
    family_document["bases"] = [
        base_reference(CALCULATOR_FAMILY, KEY_REGISTRY, registry_document)
    ]
    leaves = {
        path: migrate_leaf(path, family_document, registry_document)
        for path in leaf_paths()
    }
    return {
        WITHOUT_WHAT: root_document,
        KEY_REGISTRY: registry_document,
        CALCULATOR_FAMILY: family_document,
        **leaves,
    }


def apply_documents(documents):
    BASES.mkdir(parents=True, exist_ok=True)
    REGISTRIES.mkdir(parents=True, exist_ok=True)
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
