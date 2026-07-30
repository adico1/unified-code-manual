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

from declaration_compiler import LANGUAGE as DECLARATION_LANGUAGE
from declaration_compiler import compile_declaration


FORMAT = "manual-resolved-declaration-4"
LEAF_FORMAT = "manual-what-seed-4"
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


def deep_merge(defaults, selected):
    if not isinstance(defaults, dict) or not isinstance(selected, dict):
        return selected
    return {
        key: (
            deep_merge(defaults.get(key, {}), value)
            if key in defaults
            else value
        )
        for key, value in {**defaults, **selected}.items()
    }


def materialize(what, assembly):
    result = {**what}
    presentation = deep_merge(
        {"rendering": assembly["gui_defaults"]},
        what["presentation"],
    )
    transitions = [
        {
            **{
                "event": f"control.{control['id']}.pressed",
                "route": assembly["routes"][control["action"]],
            },
            **(
                {"argument": control["value"]}
                if "value" in control
                else {}
            ),
        }
        for control in presentation["controls"]
    ]
    laws = what["semantics"]["numeric_laws"]
    operation_ids = {
        item["id"]
        for group in what["semantics"]["operations"].values()
        for item in group
    }
    error_rules = assembly["error_rules"]
    errors = list(error_rules[laws["kind"]])
    if operation_ids & set(error_rules["zero_division_operations"]):
        errors.insert(0, "division-by-zero")
    negative_cases = assembly["negative_cases"][laws["kind"]]
    variables = {name: 0 for name in laws.get("variables", ())}
    zero_operation = next(
        (
            identity
            for identity in error_rules["zero_division_operations"]
            if identity in operation_ids
        ),
        None,
    )
    derived_acceptance = [
        {
            "id": f"derived.{identity}",
            "input": {
                **negative_cases[identity],
                **variables,
                **(
                    {
                        "expression": assembly[
                            "zero_division_expressions"
                        ][zero_operation]
                    }
                    if identity == "division-by-zero"
                    and laws["kind"] == "expression"
                    else {}
                ),
            },
            "expected": {"result": None, "error": identity},
        }
        for identity in errors
    ]
    semantics = {
        **what["semantics"],
        "validation": {
            **what["semantics"].get("validation", {}),
            "errors": errors,
        },
    }
    return {
        **result,
        "semantics": semantics,
        "presentation": presentation,
        "transitions": transitions,
        "boundaries": assembly["boundaries"],
        "acceptance": [*what["acceptance"], *derived_acceptance],
        "_assembly": {
            "stamps": assembly["stamps"],
            "registered_actions": sorted(assembly["routes"]),
        },
    }


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
    authority_root = next(
        (
            candidate
            for candidate in (owner, *owner.parents)
            if candidate.name == "seed"
        ),
        owner.parent,
    )
    if not target.is_relative_to(authority_root):
        raise ValueError("base-path-outside-authority")
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
    if what.get("program", {}).get("language") != provisions.get(
        "program_language"
    ):
        raise ValueError("program-language-authority-mismatch")
    resolved = {
        "format": FORMAT,
        **materialize(what, provisions["assembly"]),
    }
    authorities.append(
        {
            "identity": what["identity"]["canonical"],
            "kind": "what-authority",
            "sha256": document_digest(document),
        }
    )
    return resolved, authorities


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
    if program.get("language") != DECLARATION_LANGUAGE:
        errors.append("program-language")
    if "ast" in program:
        errors.append("program")
    if not program.get("case_entrypoint") or not program.get("launch_entrypoint"):
        errors.append("entrypoints")
    if not seed.get("acceptance"):
        errors.append("acceptance")
    if not errors:
        tree = compile_declaration(seed)
        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
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
        if set(seed["state"]["fields"]) != set(seed["state"].get("initial", {})):
            errors.append("state-initial")
    return sorted(set(errors))


def render_program(seed):
    tree = compile_declaration(seed)
    if not isinstance(tree, ast.Module):
        raise ValueError("program-root")
    ast.fix_missing_locations(tree)
    source = (ast.unparse(tree).rstrip() + "\n").encode()
    compile(source, "<seed-program>", "exec")
    return source


def trace_program(seed, source, authorities):
    rendered = ast.parse(source)
    functions = {
        node.name: node
        for node in rendered.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    }
    semantic_functions = seed["semantics"]["operations"].get("functions", ())
    launch = functions[seed["program"]["launch_entrypoint"]]
    buttons = [
        node
        for node in launch.body
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "grid"
            and isinstance(node.value.func.value, ast.Call)
            and isinstance(node.value.func.value.func, ast.Name)
            and node.value.func.value.func.id == "Button"
        )
    ]
    if len(buttons) != len(seed["presentation"]["controls"]):
        raise ValueError("control-trace-mismatch")
    return {
        "format": "manual-seed-trace-1",
        "seed_sha256": digest(canonical(seed)),
        "source_sha256": digest(source),
        "authorities": authorities,
        "assembly_stamps": seed["_assembly"]["stamps"],
        "top_level": [
            {
                "seed_path": "/program",
                "node": type(item).__name__,
                "generated_lines": [item.lineno, item.end_lineno],
            }
            for item in rendered.body
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
        "semantic_functions": [
            {
                "seed_path": f"/semantics/operations/functions/{index}/body",
                "identity": item["id"],
                "generated_lines": [
                    functions[f"_semantic_{index}"].lineno,
                    functions[f"_semantic_{index}"].end_lineno,
                ],
            }
            for index, item in enumerate(semantic_functions)
        ],
        "controls": [
            {
                "seed_path": f"/presentation/controls/{index}",
                "identity": control["id"],
                "generated_lines": [button.lineno, button.end_lineno],
            }
            for index, (control, button) in enumerate(
                zip(seed["presentation"]["controls"], buttons)
            )
        ],
    }


def render_tests(seed):
    entrypoint = seed["program"]["case_entrypoint"]
    transition_by_event = {
        item["event"]: item["route"]
        for item in seed["transitions"]
    }
    actions = {
        control["action"]: transition_by_event[
            f"control.{control['id']}.pressed"
        ]
        for control in seed["presentation"]["controls"]
    }
    cases = [
        {
            "id": case["id"],
            "input": case["input"],
            "expected": case["expected"],
        }
        for case in seed["acceptance"]
    ]
    editable_lines = [
        "    display_value = ['']",
        "    def display_get():",
        "        return display_value[0]",
        "    def display_set(value):",
        "        display_value[0] = value",
        "    module.display = SimpleNamespace(get=display_get, set=display_set)",
        "    editable = []",
        "    display_set('12')",
        "    module.state['expression'] = ''",
        f"    module.{actions['append']}('3')",
        "    editable.append(display_get() == '123' and module.state['expression'] == '123')",
        "    display_set('456')",
        "    module.state['expression'] = ''",
        f"    module.{actions['backspace']}()",
        "    editable.append(display_get() == '45' and module.state['expression'] == '45')",
    ]
    if "evaluate" in actions:
        editable_lines.extend(
            [
                "    display_set('7')",
                "    module.state['expression'] = ''",
                f"    module.{actions['evaluate']}()",
                "    editable.append(display_get() == '7' and module.state['expression'] == '7')",
            ]
        )
    if "push" in actions:
        editable_lines.extend(
            [
                "    display_set('8')",
                "    module.state['expression'] = ''",
                "    module.state['stack'] = []",
                f"    module.{actions['push']}()",
                "    editable.append(display_get() == '8' and module.state['stack'] == [8])",
            ]
        )
    lines = [
        '"""Generated acceptance tests. Do not edit."""',
        "import importlib.util",
        "import json",
        "from pathlib import Path",
        "from types import SimpleNamespace",
        "",
        f"CASES = {cases!r}",
        "",
        "def run():",
        "    path = Path(__file__).with_name('main.py')",
        "    specification = importlib.util.spec_from_file_location('generated_app', path)",
        "    module = importlib.util.module_from_spec(specification)",
        "    specification.loader.exec_module(module)",
        f"    results = [module.{entrypoint}(case['input']) == case['expected'] for case in CASES]",
        *editable_lines,
        "    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES], 'editable': {'passed': sum(editable), 'total': len(editable)}}",
        "    print(json.dumps(report, sort_keys=True))",
        "    return 0 if all((*results, *editable)) else 1",
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
        "compiler_sha256": digest(
            canonical(
                {
                    path.name: digest(path.read_bytes())
                    for path in sorted(Path(__file__).parent.glob("*.py"))
                }
            )
        ),
        "files": file_hashes,
        "assembly_stamps": seed["_assembly"]["stamps"],
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
