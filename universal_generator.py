"""Compile one complete structured seed program into one exact application."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path


FORMAT = "manual-seed-program-2"
LEAF_FORMAT = "manual-what-seed-3"
BASE_FORMAT = "manual-seed-base-1"
REQUIRED_CONTRACT = frozenset(
    {
        "identity",
        "semantics",
        "state",
        "transitions",
        "presentation",
        "boundaries",
        "program",
        "acceptance",
    }
)


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def document_digest(value):
    return digest(canonical(value))


def load_document(path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_reference(owner, reference, ancestry):
    if set(reference) != {"identity", "path", "sha256"}:
        raise ValueError("unpinned-base")
    relative = Path(reference["path"])
    if relative.is_absolute():
        raise ValueError("base-path-not-relative")
    target = (owner.parent / relative).resolve(strict=True)
    document = load_document(target)
    if document.get("identity") != reference["identity"]:
        raise ValueError("base-identity-mismatch")
    if document_digest(document) != reference["sha256"]:
        raise ValueError("base-hash-mismatch")
    return resolve_base(target, document, ancestry)


def resolve_base(path, document, ancestry=()):
    canonical_path = path.resolve(strict=True)
    if canonical_path in ancestry:
        raise ValueError("seed-cycle")
    if document.get("format") != BASE_FORMAT:
        raise ValueError("base-format")
    references = document.get("bases", ())
    identities = [reference.get("identity") for reference in references]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate-base")
    provisions = {}
    authorities = []
    next_ancestry = (*ancestry, canonical_path)
    for reference in references:
        inherited, inherited_authorities = resolve_reference(
            canonical_path,
            reference,
            next_ancestry,
        )
        for name, value in inherited.items():
            if name in provisions and provisions[name] != value:
                raise ValueError("base-conflict")
            provisions[name] = value
        authorities.extend(inherited_authorities)
    for name, value in document.get("provides", {}).items():
        if name in provisions and provisions[name] != value:
            raise ValueError("base-conflict")
        provisions[name] = value
    authorities.append(
        {
            "identity": document["identity"],
            "sha256": document_digest(document),
        }
    )
    return provisions, authorities


def load_seed(path):
    path = Path(path).resolve(strict=True)
    document = load_document(path)
    if document.get("format") == FORMAT:
        return document, [
            {
                "identity": document["identity"]["canonical"],
                "kind": "legacy-complete-seed",
                "sha256": document_digest(document),
            }
        ]
    if document.get("format") != LEAF_FORMAT:
        raise ValueError("leaf-format")
    references = document.get("bases", ())
    if not references:
        raise ValueError("leaf-without-base")
    provisions = {}
    authorities = []
    for reference in references:
        inherited, inherited_authorities = resolve_reference(path, reference, ())
        for name, value in inherited.items():
            if name in provisions and provisions[name] != value:
                raise ValueError("base-conflict")
            provisions[name] = value
        authorities.extend(inherited_authorities)
    what = document.get("what", {})
    if what.get("identity", {}).get("family") != provisions.get("family"):
        raise ValueError("family-authority-mismatch")
    required = set(provisions.get("required_meaning", ()))
    if required - what.keys():
        raise ValueError("incomplete-what")
    resolved = {"format": FORMAT, **what}
    authorities.append(
        {
            "identity": what["identity"]["canonical"],
            "kind": "what-authority",
            "sha256": document_digest(document),
        }
    )
    return resolved, authorities


def decode_node(value):
    if isinstance(value, list):
        return [decode_node(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "_type" not in value:
        return {key: decode_node(item) for key, item in value.items()}
    node_type = value["_type"]
    constructor = getattr(ast, node_type, None)
    if constructor is None or not isinstance(constructor, type):
        raise ValueError("unknown-program-node")
    return constructor(
        **{
            key: decode_node(item)
            for key, item in value.items()
            if key != "_type"
        }
    )


def validate(seed):
    errors = []
    if seed.get("format") != FORMAT:
        errors.append("format")
    if REQUIRED_CONTRACT - seed.keys():
        errors.append("contract")
    identity = seed.get("identity", {})
    if (
        not identity.get("canonical")
        or not identity.get("family")
        or not identity.get("variation")
        or not isinstance(identity.get("version"), int)
    ):
        errors.append("identity")
    if not seed.get("semantics", {}).get("numeric_laws"):
        errors.append("numeric-laws")
    if not seed.get("semantics", {}).get("operations"):
        errors.append("operations")
    if not seed.get("transitions"):
        errors.append("transitions")
    controls = seed.get("presentation", {}).get("controls", ())
    positions = [
        (item.get("row"), item.get("column"))
        for item in controls
    ]
    if not controls or len(positions) != len(set(positions)):
        errors.append("controls")
    if len({item.get("id") for item in controls}) != len(controls):
        errors.append("control-identities")
    events = {item.get("event") for item in seed.get("transitions", ())}
    if any(f"control.{item.get('id')}.pressed" not in events for item in controls):
        errors.append("control-routes")
    program = seed.get("program", {})
    if program.get("language") != "python-ast-3":
        errors.append("program-language")
    if not isinstance(program.get("ast"), dict):
        errors.append("program")
    if not program.get("case_entrypoint") or not program.get("launch_entrypoint"):
        errors.append("entrypoints")
    if not seed.get("acceptance"):
        errors.append("acceptance")
    if not errors:
        tree = decode_node(program["ast"])
        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        }
        names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        attributes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        constants = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float, str))
        }
        routes = {
            item.get("route")
            for item in seed["transitions"]
        }
        if not routes <= functions:
            errors.append("transition-program-link")
        if not {
            program["case_entrypoint"],
            program["launch_entrypoint"],
        } <= functions:
            errors.append("entrypoint-program-link")
        presentation_literals = {
            seed["presentation"]["title"],
            seed["presentation"]["geometry"],
            seed["presentation"]["mode_label"],
            *seed["presentation"]["theme"].values(),
            *(
                item["label"]
                for item in seed["presentation"]["controls"]
            ),
            *(
                item["argument"]
                for item in seed["transitions"]
                if item.get("argument") is not None
            ),
        }
        if not presentation_literals <= constants:
            errors.append("presentation-program-link")
        operation_declarations = [
            item
            for family in seed["semantics"]["operations"].values()
            for item in family
        ]
        program_symbols = names | attributes | constants
        if any(
            not {
                item.get("id"),
                item.get("syntax", "").rsplit(".", 1)[-1],
                item.get("target", "").rsplit(".", 1)[-1],
                item.get("token"),
            }
            & program_symbols
            for item in operation_declarations
        ):
            errors.append("operation-program-link")
        if not set(seed["state"]["fields"]) <= constants:
            errors.append("state-program-link")
    return sorted(set(errors))


def render_program(seed):
    tree = decode_node(seed["program"]["ast"])
    if not isinstance(tree, ast.Module):
        raise ValueError("program-root")
    ast.fix_missing_locations(tree)
    source = (ast.unparse(tree).rstrip() + "\n").encode()
    compile(source, "<seed-program>", "exec")
    return source


def trace_program(seed, source, authorities):
    rendered = ast.parse(source)
    original = seed["program"]["ast"].get("body", ())
    functions = {
        node.name: node
        for node in rendered.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    }
    return {
        "format": "manual-seed-trace-1",
        "seed_sha256": digest(canonical(seed)),
        "source_sha256": digest(source),
        "authorities": authorities,
        "top_level": [
            {
                "seed_path": f"/program/ast/body/{index}",
                "node": item.get("_type", "unknown"),
                "generated_lines": [
                    rendered.body[index].lineno,
                    rendered.body[index].end_lineno,
                ],
            }
            for index, item in enumerate(original)
        ],
        "contract_sections": {
            f"/{name}": digest(canonical(seed[name]))
            for name in sorted(REQUIRED_CONTRACT - {"program"})
        },
        "event_routes": [
            {
                "seed_path": f"/transitions/{index}",
                "event": transition["event"],
                "route": transition["route"],
                "generated_lines": [
                    functions[transition["route"]].lineno,
                    functions[transition["route"]].end_lineno,
                ],
            }
            for index, transition in enumerate(seed["transitions"])
        ],
    }


def render_tests(seed):
    entrypoint = seed["program"]["case_entrypoint"]
    cases = [
        {
            "id": case["id"],
            "input": case["input"],
            "expected": case["expected"],
        }
        for case in seed["acceptance"]
    ]
    lines = [
        '"""Generated acceptance tests. Do not edit."""',
        "import importlib.util",
        "import json",
        "from pathlib import Path",
        "",
        f"CASES = {cases!r}",
        "",
        "def run():",
        "    path = Path(__file__).with_name('main.py')",
        "    specification = importlib.util.spec_from_file_location('generated_app', path)",
        "    module = importlib.util.module_from_spec(specification)",
        "    specification.loader.exec_module(module)",
        f"    results = [module.{entrypoint}(case['input']) == case['expected'] for case in CASES]",
        "    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES]}",
        "    print(json.dumps(report, sort_keys=True))",
        "    return 0 if all(results) else 1",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(run())",
        "",
    ]
    return "\n".join(lines).encode()


def verify_runtime_source(source):
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden_imports = {
        name for name in imported if "generator" in name or "seed" in name
    }
    forbidden_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"read_bytes", "read_text"}
    }
    forbidden_calls.update(
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "compile"}
    )
    if forbidden_imports or forbidden_calls:
        raise ValueError("runtime-authority-leak")


def acceptance_result(seed, source):
    namespace = {"__name__": "generated.verification"}
    exec(compile(source, "<generated-verification>", "exec"), namespace)
    operation = namespace[seed["program"]["case_entrypoint"]]
    results = [
        operation(case["input"]) == case["expected"]
        for case in seed["acceptance"]
    ]
    if not all(results):
        raise ValueError("acceptance-failed")
    return {
        "passed": sum(results),
        "total": len(results),
        "cases": [case["id"] for case in seed["acceptance"]],
    }


def install(stage, output):
    backup = output.with_name("." + output.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        stage.rename(output)
    except BaseException:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def generate(seed_path, output):
    seed_path = Path(seed_path).resolve(strict=True)
    output = Path(output).resolve(strict=False)
    seed, authorities = load_seed(seed_path)
    errors = validate(seed)
    if errors:
        raise ValueError(",".join(errors))
    source = render_program(seed)
    verify_runtime_source(source)
    verification = acceptance_result(seed, source)
    tests = render_tests(seed)
    trace = canonical(trace_program(seed, source, authorities))
    files = {
        "main.py": source,
        "test_generated.py": tests,
        "traceability.json": trace,
    }
    file_hashes = {
        name: digest(content)
        for name, content in sorted(files.items())
    }
    tree_hash = digest(canonical(file_hashes))
    manifest = {
        "format": "manual-seed-application-2",
        "identity": seed["identity"],
        "seed_sha256": digest(canonical(seed)),
        "authorities": authorities,
        "compiler_sha256": digest(Path(__file__).read_bytes()),
        "files": file_hashes,
        "tree_sha256": tree_hash,
        "verification": verification,
        "runtime_seed_files": 0,
        "runtime_shared_engine_files": 0,
        "manual_application_files": 0,
        "manual_test_files": 0,
    }
    files["manifest.json"] = canonical(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix="." + output.name + "-", dir=output.parent)
    )
    try:
        for name, content in files.items():
            (stage / name).write_bytes(content)
        test_namespace = {"__name__": "generated.tests"}
        exec(compile(tests, "<generated-tests>", "exec"), test_namespace)
        install(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("seed")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    sys.stdout.buffer.write(canonical(generate(arguments.seed, arguments.output)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
