"""Resolve the one canonical ROOT authority before application assembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


FORMAT = "unified-root-seed-1"
STANDARD = "TEN-1"
UEM = "UEM-16-v0.1"
STATES = ("unknown", "absent", "false", "formed", "valid", "invalid")


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_root(path):
    path = Path(path).resolve(strict=True)
    repository = path.parents[1]
    root = load_json(path)
    errors = []
    if root.get("format") != FORMAT:
        errors.append("root-format")
    standard = root.get("standard", {})
    if standard.get("version") != STANDARD:
        errors.append("standard-version")
    if tuple(standard.get("thing_states", ())) != STATES:
        errors.append("canonical-states")
    if len(standard.get("semantic_depths", ())) != 10:
        errors.append("semantic-depths")
    if root.get("machine", {}).get("identity") != UEM:
        errors.append("machine-identity")
    authorities = root.get("authorities", ())
    identities = [item.get("identity") for item in authorities]
    paths = [item.get("path") for item in authorities]
    if len(identities) != len(set(identities)):
        errors.append("duplicate-authority-identity")
    if len(paths) != len(set(paths)):
        errors.append("duplicate-authority-path")
    verified = []
    for reference in authorities:
        target = (repository / reference["path"]).resolve(strict=True)
        if repository not in target.parents:
            errors.append("authority-path-escape")
            continue
        document = load_json(target)
        actual = digest(document)
        if actual != reference.get("sha256"):
            errors.append("authority-hash:" + reference["path"])
        verified.append(reference["path"])
    required = set(root.get("operation", {}).get("required_authorities", ()))
    if not required <= set(paths):
        errors.append("operation-authority-missing")
    if errors:
        raise ValueError("invalid-root:" + ",".join(sorted(set(errors))))
    return {
        "identity": root["identity"],
        "root_sha256": digest(root),
        "standard_version": STANDARD,
        "uem_version": UEM,
        "semantic_depths": 10,
        "canonical_states": list(STATES),
        "authorities": len(verified),
        "verified_authorities": verified,
        "open_gaps": list(root.get("open_gaps", ())),
        "verdict": "PASS",
    }
