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


def materialize(
    what,
    assembly,
    key_registry,
    key_registry_authority,
    leaf_authority,
):
    result = {**what}
    action_contracts = assembly.get("action_contracts", {})
    if (
        set(action_contracts) != set(assembly["routes"])
        or any(
            set(contract)
            not in ({"arguments"}, {"arguments", "value_type"})
            or contract.get("arguments") not in (0, 1)
            or (
                contract.get("arguments") == 0
                and "value_type" in contract
            )
            or (
                contract.get("arguments") == 1
                and contract.get("value_type") != "string"
            )
            for contract in action_contracts.values()
        )
    ):
        raise ValueError("invalid-action-contract")
    if any(
        not isinstance(item, dict)
        or not {"identity", "label", "action"} <= set(item)
        or set(item) - {"identity", "label", "action", "value", "requires"}
        or not isinstance(item["identity"], str)
        or not item["identity"]
        or not isinstance(item["label"], str)
        or not isinstance(item["action"], str)
        or item["action"] not in assembly["routes"]
        or (
            "requires" in item
            and (
                not isinstance(item["requires"], str)
                or not item["requires"]
            )
        )
        for item in key_registry
    ):
        raise ValueError("invalid-key-definition")
    key_identities = [item["identity"] for item in key_registry]
    if len(key_identities) != len(set(key_identities)):
        raise ValueError("duplicate-key-identity")
    invalid_arguments = sorted(
        item["identity"]
        for item in key_registry
        if (
            action_contracts[item["action"]]["arguments"] == 0
            and "value" in item
        )
        or (
            action_contracts[item["action"]]["arguments"] == 1
            and (
                "value" not in item
                or type(item["value"]) is not str
            )
        )
    )
    if invalid_arguments:
        raise ValueError(
            "invalid-key-arguments:" + ",".join(invalid_arguments)
        )
    key_definitions = {
        item["identity"]: {
            name: value
            for name, value in item.items()
            if name != "identity"
        }
        for item in key_registry
    }
    placements = what["presentation"]["keys"]
    if any(
        set(item) != {"key", "row", "column"}
        or not isinstance(item["key"], str)
        or not isinstance(item["row"], int)
        or not isinstance(item["column"], int)
        or item["row"] < 0
        or item["column"] < 0
        for item in placements
    ):
        raise ValueError("invalid-key-placement")
    unknown = sorted(
        {item["key"] for item in placements} - key_definitions.keys()
    )
    if unknown:
        raise ValueError("unknown-key:" + ",".join(unknown))
    operation_ids = {
        item["id"]
        for group in what["semantics"]["operations"].values()
        for item in group
    }
    capabilities = {
        *(f"operation.{identity}" for identity in operation_ids),
        *(
            f"variable.{identity}"
            for identity in what["semantics"]["numeric_laws"].get(
                "variables", ()
            )
        ),
    }
    missing_requirements = sorted(
        {
            key_definitions[item["key"]]["requires"]
            for item in placements
            if "requires" in key_definitions[item["key"]]
        }
        - capabilities
    )
    if missing_requirements:
        raise ValueError(
            "key-requirement-missing:" + ",".join(missing_requirements)
        )
    definition_indexes = {
        item["identity"]: index
        for index, item in enumerate(key_registry)
    }

    def capability_trace(requirement):
        if requirement is None:
            return None
        kind, identity = requirement.split(".", 1)
        if kind == "operation":
            matches = [
                (group, index, item)
                for group, definitions in what["semantics"][
                    "operations"
                ].items()
                for index, item in enumerate(definitions)
                if item["id"] == identity
            ]
            group, index, item = matches[0]
            return {
                "identity": requirement,
                "authority": leaf_authority["identity"],
                "authority_sha256": leaf_authority["sha256"],
                "path": (
                    f"/what/semantics/operations/{group}/{index}"
                ),
                "definition_sha256": document_digest(item),
            }
        variables = what["semantics"]["numeric_laws"].get("variables", ())
        index = list(variables).index(identity)
        return {
            "identity": requirement,
            "authority": leaf_authority["identity"],
            "authority_sha256": leaf_authority["sha256"],
            "path": f"/what/semantics/numeric_laws/variables/{index}",
            "definition_sha256": document_digest(identity),
        }

    selected_keys = [
        {
            "identity": placement["key"],
            "placement": {
                "authority": leaf_authority["identity"],
                "authority_sha256": leaf_authority["sha256"],
                "path": f"/what/presentation/keys/{index}",
            },
            "registry": {
                "authority": key_registry_authority["identity"],
                "authority_sha256": key_registry_authority["sha256"],
                "definition_path": (
                    "/provides/key_registry/"
                    f"{definition_indexes[placement['key']]}"
                ),
                "definition_sha256": document_digest(
                    key_registry[definition_indexes[placement["key"]]]
                ),
            },
            **(
                {"capability": capability_trace(
                    key_definitions[placement["key"]].get("requires")
                )}
                if "requires" in key_definitions[placement["key"]]
                else {}
            ),
        }
        for index, placement in enumerate(placements)
    ]
    controls = [
        {
            "id": placement["key"],
            **key_definitions[placement["key"]],
            "row": placement["row"],
            "column": placement["column"],
        }
        for placement in placements
    ]
    presentation = deep_merge(
        {"rendering": assembly["gui_defaults"]},
        {
            **{
                name: value
                for name, value in what["presentation"].items()
                if name != "keys"
            },
            "controls": controls,
        },
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
            "selected_keys": selected_keys,
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
            "provides": sorted(document.get("provides", {})),
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
    key_registry_authority = next(
        item
        for item in authorities
        if "key_registry" in item.get("provides", ())
    )
    leaf_authority = {
        "identity": what["identity"]["canonical"],
        "kind": "what-authority",
        "sha256": document_digest(document),
    }
    resolved = {
        "format": FORMAT,
        **materialize(
            what,
            provisions["assembly"],
            provisions["key_registry"],
            key_registry_authority,
            leaf_authority,
        ),
    }
    authorities.append(leaf_authority)
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
                "identity": control["id"],
                "placement": selected["placement"],
                "registry": selected["registry"],
                **(
                    {"capability": selected["capability"]}
                    if "capability" in selected
                    else {}
                ),
                "generated_lines": [button.lineno, button.end_lineno],
            }
            for control, selected, button in zip(
                seed["presentation"]["controls"],
                seed["_assembly"]["selected_keys"],
                buttons,
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
        "import ast",
        "import importlib.util",
        "import json",
        "from pathlib import Path",
        "from types import SimpleNamespace",
        "",
        f"CASES = {cases!r}",
        f"EXPECTED_KEY_CALLBACKS = {len(seed['presentation']['controls'])!r}",
        "",
        "def verify_key_callbacks(path):",
        "    tree = ast.parse(path.read_text(encoding='utf-8'))",
        "    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}",
        f"    launch = functions[{seed['program']['launch_entrypoint']!r}]",
        "    buttons = [node for node in launch.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'grid' and isinstance(node.value.func.value, ast.Call) and isinstance(node.value.func.value.func, ast.Name) and node.value.func.value.func.id == 'Button']",
        "    results = []",
        "    for button in buttons:",
        "        construction = button.value.func.value",
        "        command = next(item.value for item in construction.keywords if item.arg == 'command')",
        "        if isinstance(command, ast.Name):",
        "            results.append(len(functions[command.id].args.args) == 0)",
        "            continue",
        "        if not isinstance(command, ast.Lambda) or not isinstance(command.body, ast.Call) or not isinstance(command.body.func, ast.Name):",
        "            results.append(False)",
        "            continue",
        "        target = functions[command.body.func.id]",
        "        results.append(len(command.args.args) == len(command.args.defaults) and len(command.body.args) == len(target.args.args))",
        "    return {'passed': sum(results), 'total': EXPECTED_KEY_CALLBACKS, 'complete': len(results) == EXPECTED_KEY_CALLBACKS and all(results)}",
        "",
        "def run():",
        "    path = Path(__file__).with_name('main.py')",
        "    specification = importlib.util.spec_from_file_location('generated_app', path)",
        "    module = importlib.util.module_from_spec(specification)",
        "    specification.loader.exec_module(module)",
        f"    results = [module.{entrypoint}(case['input']) == case['expected'] for case in CASES]",
        *editable_lines,
        "    key_callbacks = verify_key_callbacks(path)",
        "    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES], 'editable': {'passed': sum(editable), 'total': len(editable)}, 'key_callbacks': {'passed': key_callbacks['passed'], 'total': key_callbacks['total']}}",
        "    print(json.dumps(report, sort_keys=True))",
        "    return 0 if all((*results, *editable)) and key_callbacks['complete'] else 1",
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
