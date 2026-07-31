"""Derive every disposable build path from one canonical product identity."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


IDENTITY = re.compile(r"^uc://manual/(?:applications|calculators)/([^/@]+)@(\d+)$")
LAYERS = (
    "authority",
    "specification",
    "source",
    "application",
    "verification",
    "manifest",
)


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def coordinates(document):
    identity = document.get("what", {}).get("identity", {})
    canonical_identity = identity.get("canonical", "")
    match = IDENTITY.fullmatch(canonical_identity)
    family = identity.get("family")
    variation = identity.get("variation")
    version = identity.get("version")
    if not match or not family or not variation or version != int(match.group(2)):
        raise ValueError("invalid-product-identity")
    if variation != match.group(1):
        raise ValueError("product-identity-variation-mismatch")
    return {
        "canonical_identity": canonical_identity,
        "family": family,
        "variation": variation,
        "version": version,
        "key": f"{variation}@{version}",
    }


def paths(build_root, identity):
    build_root = Path(build_root)
    group = identity["group"]
    key = identity["key"]
    product = build_root / group / key
    return {
        "root": product,
        "authority": product / "authority" / "seed.json",
        "specification": product / "specification" / "specification.json",
        "source": product / "source" / "main.py",
        "product": product / "application",
        "test": product / "verification" / "test_generated.py",
        "traceability": product / "verification" / "traceability.json",
        "manifest": product / "manifest.json",
    }


def write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def classify(build_root, leaf, resolved, files, group):
    identity = coordinates(leaf)
    if not isinstance(group, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", group):
        raise ValueError("invalid-product-group")
    identity["group"] = group
    destinations = paths(build_root, identity)
    write(destinations["authority"], canonical(leaf))
    write(destinations["specification"], canonical(resolved))
    write(destinations["source"], files["main.py"])
    write(destinations["product"] / "main.py", files["main.py"])
    write(destinations["test"], files["test_generated.py"])
    write(destinations["traceability"], files["traceability.json"])
    write(destinations["manifest"], files["manifest.json"])
    return identity, destinations


def install_tree(stage, destination):
    stage = Path(stage)
    destination = Path(destination)
    backup = destination.with_name("." + destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        stage.rename(destination)
    except BaseException:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)
