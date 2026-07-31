"""Materialize complete derived seeds from generic pinned merge declarations."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "seed" / "catalog.seed.json"
OUTPUT = ROOT / "build" / "catalog-seeds"


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def merge_patch(target, patch):
    if not isinstance(patch, dict):
        return patch
    source = target if isinstance(target, dict) else {}
    result = dict(source)
    for identity, value in patch.items():
        if value is None:
            result.pop(identity, None)
        else:
            result[identity] = merge_patch(result.get(identity), value)
    return result


def resolve_prototype(reference):
    if set(reference) != {"path", "sha256"}:
        raise ValueError("invalid-prototype-reference")
    relative = Path(reference["path"])
    if relative.is_absolute():
        raise ValueError("absolute-prototype-path")
    path = (ROOT / relative).resolve(strict=True)
    if not path.is_relative_to(ROOT / "seed"):
        raise ValueError("prototype-outside-seed-authority")
    raw = path.read_bytes()
    if digest(raw) != reference["sha256"]:
        raise ValueError("prototype-hash-mismatch")
    return json.loads(raw), path


def profile_name(profile):
    return profile["identity"].split("/")[-1].split("@", 1)[0]


def materialize_profile(profile):
    derivation = profile["derivation"]
    if set(derivation) != {"prototype", "patch"}:
        raise ValueError("invalid-derived-seed")
    prototype, prototype_path = resolve_prototype(derivation["prototype"])
    seed = merge_patch(prototype, derivation["patch"])
    canonical_identity = seed.get("what", {}).get("identity", {}).get("canonical")
    if canonical_identity != profile.get("product_identity"):
        raise ValueError("derived-product-identity-mismatch")
    return seed, prototype_path


def materialize_catalog(destination=OUTPUT):
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    profiles = [
        profile
        for family in document["families"]
        for profile in family["profiles"]
        if "derivation" in profile
    ]
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    expected = set()
    results = []
    for profile in profiles:
        name = profile_name(profile)
        path = destination / f"{name}.seed.json"
        seed, prototype_path = materialize_profile(profile)
        for reference in seed["bases"]:
            authority = (prototype_path.parent / reference["path"]).resolve(
                strict=True
            )
            reference["path"] = os.path.relpath(authority, path.parent)
        raw = canonical(seed)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(raw)
        temporary.replace(path)
        expected.add(path.name)
        results.append(
            {
                "id": name,
                "title": profile["name"],
                "seed": path.relative_to(ROOT).as_posix(),
                "output": f"build/{name}",
                "enabled": True,
                "seed_sha256": digest(raw),
            }
        )
    unexpected = {
        path.name
        for path in destination.glob("*.seed.json")
    } - expected
    for name in unexpected:
        (destination / name).unlink()
    return results
