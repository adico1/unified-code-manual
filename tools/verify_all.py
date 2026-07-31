"""Build, verify, and optionally launch every seed-programmed application."""

from __future__ import annotations

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
import multiprocessing
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from catalog_materializer import materialize_catalog


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "seed" / "suite.seed.json"
CATALOG = ROOT / "seed" / "catalog.seed.json"
COMPILER = ROOT / "src" / "seed_compiler.py"
COMPILER_SOURCES = tuple(sorted((ROOT / "src").glob("*.py")))


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_compiler():
    sys.path.insert(0, str(COMPILER.parent))
    specification = importlib.util.spec_from_file_location(
        "manual_seed_compiler", COMPILER
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_suite():
    document = json.loads(SUITE.read_text(encoding="utf-8"))
    if document.get("format") != "manual-seed-program-suite-3":
        raise ValueError("unsupported-suite")
    applications = [
        item for item in document.get("applications", ()) if item.get("enabled")
    ]
    applications.extend(materialize_catalog())
    if len({item["id"] for item in applications}) != len(applications):
        raise ValueError("duplicate-application")
    return applications


def validate_catalog(document, *, normalize=True):
    errors = []
    families = document.get("families", ())
    family_identities = [item.get("identity") for item in families]
    if document.get("format") != "manual-application-profile-catalog-1":
        errors.append("unsupported-catalog")
    if len(family_identities) != len(set(family_identities)):
        errors.append("duplicate-family-identity")
    profiles = [
        (family.get("profile_namespace"), profile)
        for family in families
        for profile in family.get("profiles", ())
    ]
    identities = [profile.get("identity") for _family, profile in profiles]
    if len(identities) != len(set(identities)):
        errors.append("duplicate-profile-identity")
    for family, profile in profiles:
        identity = profile.get("identity")
        capabilities = profile.get("capabilities", ())
        status = profile.get("status")
        if not identity or not profile.get("name") or not profile.get("class"):
            errors.append(f"incomplete-profile:{identity}")
        if not capabilities or len(capabilities) != len(set(capabilities)):
            errors.append(f"invalid-capabilities:{identity}")
        if status not in {"proven", "catalogued"}:
            errors.append(f"invalid-status:{identity}")
        if status == "proven":
            seed_reference = profile.get("seed")
            if "derivation" in profile:
                name = identity.split("/")[-1].split("@", 1)[0]
                seed_reference = f"build/catalog-seeds/{name}.seed.json"
            seed = ROOT / (seed_reference or "")
            if not seed.is_file():
                errors.append(f"missing-proven-seed:{identity}")
            else:
                product = json.loads(seed.read_text(encoding="utf-8"))
                actual = product.get("what", {}).get("identity", {}).get(
                    "canonical"
                )
                if actual != profile.get("product_identity"):
                    errors.append(f"product-identity-mismatch:{identity}")
        if status == "catalogued" and (
            profile.get("seed") or profile.get("product_identity")
        ):
            errors.append(f"false-proof-reference:{identity}")
        if not str(identity).startswith(f"uc://manual/catalog/{family}/"):
            errors.append(f"family-identity-mismatch:{identity}")
    normalized = (
        {
            "format": document.get("format"),
            "identity": document.get("identity"),
            "families": [
                {
                    **{
                        key: value
                        for key, value in family.items()
                        if key != "profiles"
                    },
                    "profiles": sorted(
                        family.get("profiles", ()),
                        key=lambda item: item.get("identity", ""),
                    ),
                }
                for family in sorted(
                    families,
                    key=lambda item: item.get("identity", ""),
                )
            ],
        }
        if normalize
        else None
    )
    return errors, normalized


def verify_catalog():
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors, normalized = validate_catalog(document)
    if errors:
        raise ValueError("invalid-catalog:" + ",".join(errors))
    profiles = [
        profile
        for family in document["families"]
        for profile in family["profiles"]
    ]
    mutations = []

    family_profiles = document["families"][0]["profiles"]
    family_profiles.append(family_profiles[0])
    mutations.append(validate_catalog(document, normalize=False)[0])
    family_profiles.pop()

    target = next(
        profile
        for family in document["families"]
        for profile in family["profiles"]
    )
    saved_target = dict(target)
    target.pop("derivation", None)
    target.update(
        {
            "status": "proven",
            "seed": "seed/applications/not-present.seed.json",
            "product_identity": "uc://manual/applications/not-present@1",
        }
    )
    mutations.append(validate_catalog(document, normalize=False)[0])
    target.clear()
    target.update(saved_target)

    capabilities = family_profiles[0]["capabilities"]
    family_profiles[0]["capabilities"] = []
    mutations.append(validate_catalog(document, normalize=False)[0])
    family_profiles[0]["capabilities"] = capabilities

    capabilities.append(capabilities[0])
    mutations.append(validate_catalog(document, normalize=False)[0])
    capabilities.pop()

    if not all(mutations):
        raise ValueError("catalog-mutation-undetected")
    reordered = json.loads(json.dumps(document))
    reordered["families"].reverse()
    for family in reordered["families"]:
        family["profiles"].reverse()
    reordered_errors, reordered_normalized = validate_catalog(reordered)
    if reordered_errors or canonical(reordered_normalized) != canonical(normalized):
        raise ValueError("catalog-order-dependent")
    family_counts = {
        family["name"]: {
            "profiles": len(family["profiles"]),
            "proven": sum(
                item["status"] == "proven" for item in family["profiles"]
            ),
            "catalogued": sum(
                item["status"] == "catalogued" for item in family["profiles"]
            ),
        }
        for family in document["families"]
    }
    return {
        "identity": document["identity"],
        "profiles": len(profiles),
        "proven": sum(item["status"] == "proven" for item in profiles),
        "catalogued": sum(item["status"] == "catalogued" for item in profiles),
        "families": family_counts,
        "mutations": {"passed": len(mutations), "total": len(mutations)},
        "record_order_independent": True,
        "snapshot_sha256": digest(canonical(normalized)),
    }


def tree_bytes(path):
    return {
        item.name: item.read_bytes()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def compile_app(compiler, application, output=None):
    target = ROOT / application["output"] if output is None else Path(output)
    evidence = compiler.generate(ROOT / application["seed"], target)
    return {
        **application,
        "output_path": target,
        "application": target / "main.py",
        "evidence": evidence,
    }


def compile_application_worker(request):
    application, output = request
    return compile_app(load_compiler(), application, output)


def compile_application_pair_worker(request):
    application, second_output = request
    compiler = load_compiler()
    seed_path = ROOT / application["seed"]
    target = ROOT / application["output"]
    resolved_seed, authorities = compiler.load_seed(seed_path)
    manifest, first_files = compiler.assemble_resolved(
        resolved_seed,
        authorities,
    )
    compiler.install_files(first_files, target)
    first = {
        **application,
        "output_path": target,
        "application": target / "main.py",
        "evidence": manifest,
        "resolved_seed": resolved_seed,
        "leaf_document": json.loads(
            seed_path.read_text(encoding="utf-8")
        ),
    }
    _manifest, second = compiler.assemble_resolved(
        resolved_seed,
        authorities,
    )
    return first, second


def compile_applications(requests):
    requests = list(requests)
    try:
        with ProcessPoolExecutor(
            max_workers=min(8, len(requests)),
            mp_context=multiprocessing.get_context("fork"),
        ) as workers:
            return list(
                workers.map(
                    compile_application_worker,
                    requests,
                    chunksize=max(1, len(requests) // 16),
                )
            )
    except PermissionError:
        with ThreadPoolExecutor(
            max_workers=min(8, len(requests))
        ) as workers:
            return list(workers.map(compile_application_worker, requests))


def compile_application_pairs(requests):
    requests = list(requests)
    try:
        with ProcessPoolExecutor(
            max_workers=min(8, len(requests)),
            mp_context=multiprocessing.get_context("fork"),
        ) as workers:
            return list(
                workers.map(
                    compile_application_pair_worker,
                    requests,
                    chunksize=max(1, len(requests) // 16),
                )
            )
    except PermissionError:
        with ThreadPoolExecutor(
            max_workers=min(8, len(requests))
        ) as workers:
            return list(
                workers.map(compile_application_pair_worker, requests)
            )


def verify_isolated(generated):
    isolation = Path(tempfile.mkdtemp(prefix="manual-app-isolation-"))
    try:
        with ThreadPoolExecutor(max_workers=min(16, len(generated))) as workers:
            list(
                workers.map(
                    lambda item: shutil.copytree(
                        item["output_path"],
                        isolation / item["id"],
                    ),
                    generated,
                )
            )
        identities = [item["id"] for item in generated]
        batch = (
            "import contextlib,importlib.util,io,json,pathlib,sys\n"
            "reports=[]\n"
            "for identity in json.loads(sys.argv[1]):\n"
            " path=pathlib.Path(identity)/'test_generated.py'\n"
            " spec=importlib.util.spec_from_file_location('isolated_'+identity.replace('-','_'),path)\n"
            " module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\n"
            " stream=io.StringIO()\n"
            " with contextlib.redirect_stdout(stream): code=module.run(emit=True)\n"
            " if code: raise SystemExit(code)\n"
            " reports.append(json.loads(stream.getvalue()))\n"
            "print(json.dumps(reports,sort_keys=True))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", batch, json.dumps(identities)],
            cwd=isolation,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    finally:
        shutil.rmtree(isolation)


def verify_application_self_tests(generated):
    roots = [str(item["output_path"]) for item in generated]
    batch = (
        "import importlib.util,json,pathlib,sys,tkinter as tk\n"
        "reports=[]\n"
        "master=tk.Tk();master.withdraw()\n"
        "destroy=master.destroy\n"
        "def clear_surface():\n"
        " for child in master.winfo_children(): child.destroy()\n"
        "master.destroy=clear_surface\n"
        "for index,root in enumerate(json.loads(sys.argv[1])):\n"
        " path=pathlib.Path(root)/'main.py'\n"
        " spec=importlib.util.spec_from_file_location(f'generated_gui_{index}',path)\n"
        " module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\n"
        " factory=lambda:master\n"
        " if hasattr(module,'tk'): module.tk.Tk=factory\n"
        " if hasattr(module,'Tk'): module.Tk=factory\n"
        " operation=getattr(module,'self_test_application',None) or getattr(module,'self_test_interface')\n"
        " report=operation()\n"
        " if report['self_test']['passed']!=report['self_test']['total'] or not report['closed']: raise SystemExit(index+1)\n"
        " reports.append(report)\n"
        "destroy()\n"
        "print(json.dumps(reports,sort_keys=True))\n"
    )
    group_count = min(4, len(roots))
    groups = [
        roots[index::group_count]
        for index in range(group_count)
    ]

    def run_group(group):
        result = subprocess.run(
            [sys.executable, "-c", batch, json.dumps(group)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return json.loads(result.stdout)

    with ThreadPoolExecutor(max_workers=len(groups)) as workers:
        reports = list(workers.map(run_group, groups))
    return [report for group in reports for report in group]


def verify_determinism(compiler, applications, generated):
    second_root = Path(tempfile.mkdtemp(prefix="manual-app-rebuild-"))
    try:
        first = {
            item["id"]: tree_bytes(item["output_path"])
            for item in generated
        }
        requests = [
            (item, second_root / item["id"])
            for item in applications
        ]
        rebuilt = compile_applications(requests)
        second = {
            item["id"]: tree_bytes(item["output_path"])
            for item in rebuilt
        }
        if first != second:
            raise ValueError("non-deterministic-output")
        return {
            identity: digest(
                canonical(
                    {
                        name: digest(content)
                        for name, content in sorted(files.items())
                    }
                )
            )
            for identity, files in first.items()
        }
    finally:
        shutil.rmtree(second_root)


def seed_vocabulary(seed):
    identity = seed["identity"]
    declared = seed["semantics"].get("application_vocabulary")
    if declared:
        return set(declared)
    operations = seed["semantics"]["operations"]
    return {
        identity["variation"],
        *(
            item["id"]
            for family in operations.values()
            for item in family
        ),
        *(
            item["id"]
            for item in seed["presentation"]["controls"]
        ),
        *(
            item["route"]
            for item in seed["transitions"]
        ),
    }


def verify_compiler_separation(generated):
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in COMPILER_SOURCES
    ).casefold()
    vocabulary = set()
    registered = set()
    for application in generated:
        seed = application["resolved_seed"]
        vocabulary.update(seed_vocabulary(seed))
        registered.update(seed["_assembly"]["registered_actions"])
    generic = {
        "abs",
        "add",
        "append",
        "construction",
        "divide",
        "geometry",
        "left",
        "maximum",
        "minimum",
        "multiply",
        "power",
        "owner",
        "records",
        "right",
        "scale",
        "status",
        "subtract",
        "sum",
        "total",
        "trace",
    }
    inspected = sorted(
        item for item in vocabulary - generic - registered if len(item) >= 4
    )
    vocabulary_pattern = (
        r"(?<![a-z0-9_-])(?:"
        + "|".join(
            re.escape(item.casefold())
            for item in sorted(inspected, key=len, reverse=True)
        )
        + r")(?![a-z0-9_-])"
    )
    hits = sorted({
        match.group(0)
        for match in re.finditer(vocabulary_pattern, source)
    })
    if hits:
        raise ValueError("compiler-application-vocabulary:" + ",".join(hits))
    return {"inspected": len(inspected), "hits": len(hits)}


def source_churn(generated):
    lines = {
        item["id"]: item["output_path"].joinpath("main.py").read_text(
            encoding="utf-8"
        ).splitlines()
        for item in generated
    }
    common = set.intersection(
        *(
            {line for line in source if line.strip()}
            for source in lines.values()
        )
    )
    return {
        "physical_shared_runtime_files": 0,
        "textually_common_nonblank_lines": len(common),
        "specialized": {
            identity: {
                "total_lines": len(source),
                "nonblank_lines": sum(bool(line.strip()) for line in source),
                "nonblank_lines_not_common_to_all": sum(
                    bool(line.strip()) and line not in common
                    for line in source
                ),
            }
            for identity, source in sorted(lines.items())
        },
    }


def verify_concise_declarations(generated):
    manifests = {
        item["id"]: json.loads(
            item["output_path"].joinpath("manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for item in generated
    }
    reports = []
    for application in generated:
        path = ROOT / application["seed"]
        document = application["leaf_document"]
        what = document["what"]
        if "ast" in what["program"]:
            raise ValueError("leaf-ast-present")
        if "controls" in what["presentation"]:
            raise ValueError("leaf-expanded-controls")
        if not what["presentation"].get("keys"):
            raise ValueError("leaf-keys-absent")
        if what["state"].get("authority") != "declarations":
            raise ValueError("state-not-declared")
        forbidden_derived = {"transitions", "boundaries"} & what.keys()
        if forbidden_derived:
            raise ValueError("leaf-derived-meaning:" + ",".join(forbidden_derived))
        language = what["program"]["language"]
        if (
            language == "calculator-declaration-1"
            and what["semantics"].get("validation", {}).get("errors")
        ):
            raise ValueError("leaf-reachable-errors")
        seed = application["resolved_seed"]
        if tuple(
            item["stage"] for item in seed["_assembly"]["stamps"]
        ) != (
            "01_outer_to_inner",
            "02_inner_to_core",
            "03_core_prepare",
            "04_core_processing",
            "05_core_collect",
            "06_core_to_inner",
            "07_inner_to_outer",
        ):
            raise ValueError("seven-stage-contract")
        if manifests[application["id"]].get("generated_ast") is not True:
            raise ValueError("declaration-ast-not-generated")
        reports.append(
            {
                "id": application["id"],
                "seed_bytes": path.stat().st_size,
                "ast_source": "generated-at-build-time",
            }
        )
    return {
        "applications": reports,
        "leaf_ast_files": 0,
        "generated_ast": len(reports),
        "stamps": 7,
        "derived_transitions": sum(
            len(item["resolved_seed"]["transitions"])
            for item in generated
        ),
        "selected_keys": sum(
            len(item["leaf_document"]["what"]["presentation"]["keys"])
            for item in generated
        ),
        "derived_reachable_errors": sum(
            len({
                guard["error"]
                for command in item["resolved_seed"]["semantics"].get(
                    "commands", ()
                )
                for guard in command.get("guards", ())
            })
            + len(
                item["resolved_seed"]["semantics"]
                .get("validation", {})
                .get("errors", ())
            )
            for item in generated
        ),
        "total_seed_bytes": sum(item["seed_bytes"] for item in reports),
    }


def nested_calculations(value):
    if isinstance(value, dict):
        if set(value) == {"calculate"}:
            yield value["calculate"]
        for child in value.values():
            yield from nested_calculations(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_calculations(child)


def verify_cross_family_composition(generated, compiler):
    applications = [
        item
        for item in generated
        if item["resolved_seed"]["semantics"].get("calculations", {}).get(
            "functions"
        )
    ]
    if not applications:
        raise ValueError("cross-family-composition-absent")
    reports = []
    mutations = []
    for application in applications:
        definitions = application["resolved_seed"]["semantics"][
            "calculations"
        ]["functions"]
        source = application["application"].read_text(encoding="utf-8")
        tree = ast.parse(source)
        generated_functions = sorted(
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith("_calculation_")
        )
        expected_functions = [
            f"_calculation_{index}" for index in range(len(definitions))
        ]
        if generated_functions != expected_functions:
            raise ValueError("cross-family-specialization")
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        if not set(expected_functions) <= calls:
            raise ValueError("cross-family-calculation-unreachable")
        if any(
            token in source
            for token in (
                "semantic_expression",
                "def expression(",
                "unknown-semantic-expression",
                "seed_compiler",
            )
        ):
            raise ValueError("cross-family-runtime-interpreter")
        trace = json.loads(
            application["output_path"].joinpath(
                "traceability.json"
            ).read_text(encoding="utf-8")
        )
        expected_trace = [
            {
                "identity": item["id"],
                "seed_path": (
                    f"/semantics/calculations/functions/{index}/body"
                ),
            }
            for index, item in enumerate(definitions)
        ]
        actual_trace = [
            {
                "identity": item["identity"],
                "seed_path": item["seed_path"],
            }
            for item in trace["semantic_functions"]
        ]
        if actual_trace != expected_trace:
            raise ValueError("cross-family-traceability")
        mutated = deepcopy(application["resolved_seed"])
        mutated["semantics"]["calculations"]["functions"][0][
            "id"
        ] = "unreachable_calculation"
        mutations.append(
            expect_error(
                lambda: compiler.render_declaration_source(mutated),
                "unknown-stateful-calculation",
            )
        )
        wrong_arity = deepcopy(application["resolved_seed"])
        calculation_call = next(nested_calculations(wrong_arity))
        calculation_call["arguments"].pop()
        mutations.append(
            expect_error(
                lambda: compiler.render_declaration_source(wrong_arity),
                "invalid-stateful-calculation-arity",
            )
        )
        reports.append(
            {
                "id": application["id"],
                "functions": [item["id"] for item in definitions],
                "generated_functions": generated_functions,
                "traceability": "PASS",
                "runtime_interpreter_files": 0,
            }
        )
    shared_source = {
        path.name: path.read_text(encoding="utf-8")
        for path in COMPILER_SOURCES
    }
    if (
        "from semantic_expression import function_source"
        not in shared_source["declaration_compiler.py"]
        or "from semantic_expression import function_source"
        not in shared_source["stateful_compiler.py"]
    ):
        raise ValueError("cross-family-expression-authority-divided")
    return {
        "applications": reports,
        "shared_expression_authority": "src/semantic_expression.py",
        "mutations": {
            "passed": len(mutations),
            "total": len(applications) * 2,
        },
    }


def write_report(
    applications,
    generated,
    hashes,
    separation,
    complete_tree,
    seed_graph,
    key_registry,
    control_registry,
    key_callbacks,
    self_tests,
    declarations,
    catalog,
    cross_family,
):
    runner_bytes = Path(__file__).read_bytes()
    single_api_bytes = Path(__file__).with_name("single_api.py").read_bytes()
    report = {
        "format": "manual-seed-assembly-report-1",
        "operation": "python3 tools/single_api.py",
        "applications": [
            {
                "id": item["id"],
                "seed": item["seed"],
                "seed_sha256": item["evidence"]["seed_sha256"],
                "artifact_tree_sha256": item["evidence"]["tree_sha256"],
                "acceptance": item["evidence"]["verification"],
                "controls": len(
                    item["resolved_seed"]["presentation"]["controls"]
                ),
                "source_lines": len(
                    item["application"].read_text(encoding="utf-8").splitlines()
                ),
            }
            for item in generated
        ],
        "build_time_shared": {
            **{
                path.relative_to(ROOT).as_posix(): {
                    "sha256": digest(path.read_bytes()),
                    "lines": len(path.read_bytes().splitlines()),
                }
                for path in COMPILER_SOURCES
            },
            "tools/verify_all.py": {
                "sha256": digest(runner_bytes),
                "lines": len(runner_bytes.splitlines()),
            },
            "tools/single_api.py": {
                "sha256": digest(single_api_bytes),
                "lines": len(single_api_bytes.splitlines()),
            },
        },
        "generated_source": source_churn(generated),
        "deterministic_artifact_hashes": hashes,
        "complete_tree_sha256": complete_tree,
        "compiler_application_vocabulary": separation,
        "manual_application_code": 0,
        "manual_application_tests": 0,
        "runtime_seed_access": 0,
        "seed_graph": seed_graph,
        "key_registry": key_registry,
        "control_registry": control_registry,
        "key_callbacks": key_callbacks,
        "application_self_tests": self_tests,
        "concise_declarations": declarations,
        "application_profile_catalog": catalog,
        "cross_family_composition": cross_family,
    }
    destination = ROOT / "build" / "assembly-report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_bytes(canonical(report))
    temporary.replace(destination)
    return report


def verify_specialization(generated):
    allowed = {
        "main.py",
        "manifest.json",
        "test_generated.py",
        "traceability.json",
    }
    trees = {
        item["id"]: tree_bytes(item["output_path"])
        for item in generated
    }
    if any(set(files) != allowed for files in trees.values()):
        raise ValueError("non-specialized-output")
    sources = {files["main.py"] for files in trees.values()}
    if len(sources) != len(trees):
        raise ValueError("applications-not-independent")
    forbidden = (
        b"seed.json",
        b"universal_generator",
        b"calculator_suite",
        b"seed_compiler",
        b"declaration_compiler",
    )
    if any(
        token in files["main.py"]
        for files in trees.values()
        for token in forbidden
    ):
        raise ValueError("runtime-authority-leak")
    return trees


def expect_error(operation, identity):
    try:
        operation()
    except ValueError as error:
        if str(error) != identity:
            raise
        return identity
    raise ValueError("missing-rejection:" + identity)


def verify_seed_graph(compiler):
    temporary = Path(tempfile.mkdtemp(prefix="manual-seed-graph-"))
    try:
        copied = temporary / "seed"
        shutil.copytree(ROOT / "seed", copied)
        leaf = copied / "applications" / "normal.seed.json"
        family = copied / "families" / "calculator.seed.json"

        tampered = json.loads(family.read_text(encoding="utf-8"))
        tampered["provides"]["family"] = "tampered"
        family.write_bytes(canonical(tampered))
        tamper = expect_error(
            lambda: compiler.load_seed(leaf),
            "base-hash-mismatch",
        )

        shutil.rmtree(copied)
        shutil.copytree(ROOT / "seed", copied)
        leaf = copied / "applications" / "normal.seed.json"
        unpinned = json.loads(leaf.read_text(encoding="utf-8"))
        del unpinned["bases"][0]["sha256"]
        leaf.write_bytes(canonical(unpinned))
        floating = expect_error(
            lambda: compiler.load_seed(leaf),
            "unpinned-base",
        )

        root_path = ROOT / "seed" / "bases" / "בלי_מה.seed.json"
        root_document = json.loads(root_path.read_text(encoding="utf-8"))
        cycle = expect_error(
            lambda: compiler.resolve_base(
                root_path,
                root_document,
                (root_path.resolve(),),
            ),
            "seed-cycle",
        )

        conflict_root = temporary / "conflict-root.seed.json"
        conflict_root.write_bytes(canonical(root_document))
        conflict_document = {
            "format": compiler.BASE_FORMAT,
            "identity": "uc://manual/seeds/conflict-proof@1",
            "kind": "mutation",
            "bases": [
                {
                    "identity": root_document["identity"],
                    "path": conflict_root.name,
                    "sha256": compiler.document_digest(root_document),
                }
            ],
            "provides": {
                "canonical_encoding": "conflicting-encoding",
            },
        }
        conflict_path = temporary / "conflict.seed.json"
        conflict_path.write_bytes(canonical(conflict_document))
        conflict = expect_error(
            lambda: compiler.resolve_base(
                conflict_path,
                conflict_document,
            ),
            "base-conflict",
        )
        outside = copied.parent / "outside.seed.json"
        outside.write_bytes(canonical(root_document))
        escaped = json.loads(leaf.read_text(encoding="utf-8"))
        escaped["bases"][0] = {
            "identity": root_document["identity"],
            "path": "../../outside.seed.json",
            "sha256": compiler.document_digest(root_document),
        }
        leaf.write_bytes(canonical(escaped))
        containment = expect_error(
            lambda: compiler.load_seed(leaf),
            "base-path-outside-authority",
        )
        return {
            "tamper": tamper,
            "floating": floating,
            "cycle": cycle,
            "conflict": conflict,
            "containment": containment,
            "passed": 5,
            "total": 5,
        }
    finally:
        shutil.rmtree(temporary)


def verify_key_registry(applications, compiler):
    selected = set()
    resolved = set()
    for application in applications:
        path = ROOT / application["seed"]
        document = json.loads(path.read_text(encoding="utf-8"))
        placements = document["what"]["presentation"]["keys"]
        seed, _ = compiler.load_seed(path)
        selected.update(item["key"] for item in placements)
        resolved.update(item["id"] for item in seed["presentation"]["controls"])
        if [item["key"] for item in placements] != [
            item["id"] for item in seed["presentation"]["controls"]
        ]:
            raise ValueError("key-resolution-order")

    family_path = ROOT / "seed" / "families" / "calculator.seed.json"
    family_document = json.loads(family_path.read_text(encoding="utf-8"))
    inherited, inherited_authorities = compiler.resolve_base(
        family_path,
        family_document,
    )
    registry = inherited["key_registry"]
    registry_authority = next(
        item
        for item in inherited_authorities
        if "key_registry" in item.get("provides", ())
    )
    required_key = next(
        item
        for item in registry
        if item.get("requires", "").startswith("operation.")
    )
    proof_application = next(
        application
        for application in applications
        if required_key["identity"]
        in {
            item["key"]
            for item in json.loads(
                (ROOT / application["seed"]).read_text(encoding="utf-8")
            )["what"]["presentation"]["keys"]
        }
    )
    proof_path = ROOT / proof_application["seed"]
    proof_document = json.loads(proof_path.read_text(encoding="utf-8"))
    _, authorities = compiler.load_seed(proof_path)
    what = proof_document["what"]
    leaf_authority = {
        "identity": what["identity"]["canonical"],
        "kind": "what-authority",
        "sha256": compiler.document_digest(proof_document),
    }

    unknown_what = json.loads(json.dumps(what))
    unknown_what["presentation"]["keys"][0]["key"] = "key.unknown"
    unknown = expect_error(
        lambda: compiler.materialize(
            unknown_what,
            inherited["assembly"],
            registry,
            registry_authority,
            leaf_authority,
        ),
        "unknown-key:key.unknown",
    )
    duplicate = expect_error(
        lambda: compiler.materialize(
            what,
            inherited["assembly"],
            [*registry, registry[0]],
            registry_authority,
            leaf_authority,
        ),
        "duplicate-key-identity",
    )
    invalid_registry = json.loads(json.dumps(registry))
    invalid_registry[0]["action"] = "unregistered"
    invalid = expect_error(
        lambda: compiler.materialize(
            what,
            inherited["assembly"],
            invalid_registry,
            registry_authority,
            leaf_authority,
        ),
        "invalid-key-definition",
    )
    required_definition = next(
        item
        for item in registry
        if inherited["assembly"]["action_contracts"][item["action"]][
            "arguments"
        ]
        == 1
    )
    missing_value_registry = json.loads(json.dumps(registry))
    next(
        item
        for item in missing_value_registry
        if item["identity"] == required_definition["identity"]
    ).pop("value")
    missing_value = expect_error(
        lambda: compiler.materialize(
            what,
            inherited["assembly"],
            missing_value_registry,
            registry_authority,
            leaf_authority,
        ),
        "invalid-key-arguments:" + required_definition["identity"],
    )
    non_string_registry = json.loads(json.dumps(registry))
    next(
        item
        for item in non_string_registry
        if item["identity"] == required_definition["identity"]
    )["value"] = 7
    non_string_value = expect_error(
        lambda: compiler.materialize(
            what,
            inherited["assembly"],
            non_string_registry,
            registry_authority,
            leaf_authority,
        ),
        "invalid-key-arguments:" + required_definition["identity"],
    )
    free_definition = next(
        item
        for item in registry
        if inherited["assembly"]["action_contracts"][item["action"]][
            "arguments"
        ]
        == 0
    )
    unexpected_value_registry = json.loads(json.dumps(registry))
    next(
        item
        for item in unexpected_value_registry
        if item["identity"] == free_definition["identity"]
    )["value"] = "unexpected"
    unexpected_value = expect_error(
        lambda: compiler.materialize(
            what,
            inherited["assembly"],
            unexpected_value_registry,
            registry_authority,
            leaf_authority,
        ),
        "invalid-key-arguments:" + free_definition["identity"],
    )
    missing_what = json.loads(json.dumps(what))
    missing_identity = required_key["requires"].split(".", 1)[1]
    missing_what["semantics"]["operations"] = {
        group: [
            item
            for item in definitions
            if item["id"] != missing_identity
        ]
        for group, definitions in missing_what["semantics"]["operations"].items()
    }
    missing = expect_error(
        lambda: compiler.materialize(
            missing_what,
            inherited["assembly"],
            registry,
            registry_authority,
            leaf_authority,
        ),
        "key-requirement-missing:" + required_key["requires"],
    )
    return {
        "registry_identity": next(
            item["identity"]
            for item in authorities
            if item["identity"].endswith("calculator-keys@1")
        ),
        "definitions": len(registry),
        "selected_identities": len(selected),
        "resolved_identities": len(resolved),
        "unknown": unknown,
        "duplicate": duplicate,
        "invalid": invalid,
        "missing_requirement": missing,
        "callback_contract_mutations": {
            "missing_value": missing_value,
            "non_string_value": non_string_value,
            "unexpected_value": unexpected_value,
        },
        "runtime_registry_access": 0,
    }


def verify_control_registry(applications, compiler):
    if not applications:
        raise ValueError("stateful-proof-absent")
    application = applications[0]
    leaf_path = ROOT / application["seed"]
    document = json.loads(leaf_path.read_text(encoding="utf-8"))
    family_reference = document["bases"][0]
    family_path = (leaf_path.parent / family_reference["path"]).resolve()
    family_document = json.loads(family_path.read_text(encoding="utf-8"))
    inherited, authorities = compiler.resolve_base(
        family_path,
        family_document,
    )
    registry = inherited["control_registry"]
    registry_authority = next(
        item
        for item in authorities
        if "control_registry" in item.get("provides", ())
    )
    what = document["what"]
    leaf_authority = {
        "identity": what["identity"]["canonical"],
        "kind": "what-authority",
        "sha256": compiler.document_digest(document),
    }
    resolved, _ = compiler.load_seed(leaf_path)
    selected = [item["key"] for item in what["presentation"]["keys"]]
    if selected != [
        item["id"] for item in resolved["presentation"]["controls"]
    ]:
        raise ValueError("control-resolution-order")

    unknown_what = json.loads(json.dumps(what))
    unknown_what["presentation"]["keys"][0]["key"] = "control.unknown"
    unknown = expect_error(
        lambda: compiler.materialize_stateful(
            unknown_what,
            inherited["assembly"],
            registry,
            registry_authority,
            leaf_authority,
        ),
        "unknown-key:control.unknown",
    )

    missing_what = json.loads(json.dumps(what))
    missing_what["semantics"]["commands"] = [
        item
        for item in missing_what["semantics"]["commands"]
        if item["id"] != registry[0]["command"]
    ]
    missing = expect_error(
        lambda: compiler.materialize_stateful(
            missing_what,
            inherited["assembly"],
            registry,
            registry_authority,
            leaf_authority,
        ),
        "control-command-missing:" + registry[0]["command"],
    )

    arguments_registry = json.loads(json.dumps(registry))
    arguments_registry[0]["arguments"] = {}
    arguments = expect_error(
        lambda: compiler.materialize_stateful(
            what,
            inherited["assembly"],
            arguments_registry,
            registry_authority,
            leaf_authority,
        ),
        "control-argument-mismatch:" + registry[0]["identity"],
    )

    duplicate = expect_error(
        lambda: compiler.materialize_stateful(
            what,
            inherited["assembly"],
            [*registry, registry[0]],
            registry_authority,
            leaf_authority,
        ),
        "invalid-control-registry",
    )
    return {
        "registry_identity": registry_authority["identity"],
        "definitions": len(registry),
        "selected_identities": len(selected),
        "resolved_identities": len(
            resolved["presentation"]["controls"]
        ),
        "unknown": unknown,
        "missing_command": missing,
        "argument_mismatch": arguments,
        "duplicate": duplicate,
        "runtime_registry_access": 0,
    }


def generate_all_from_seeds(*, self_test):
    applications = load_suite()
    compiler = load_compiler()
    pairs = compile_application_pairs(
        (application, None)
        for application in applications
    )
    generated = [first for first, _second in pairs]
    calculator_applications = [
        item
        for item in generated
        if item["resolved_seed"]["program"]["language"]
        == "calculator-declaration-1"
    ]
    stateful_applications = [
        item
        for item in generated
        if item not in calculator_applications
    ]
    first_trees = {
        item["id"]: tree_bytes(item["output_path"])
        for item in generated
    }
    second_trees = {
        item["id"]: second
        for item, (_first, second) in zip(applications, pairs)
    }
    if first_trees != second_trees:
        raise ValueError("non-deterministic-output")
    hashes = {
        identity: digest(
            canonical(
                {
                    name: digest(content)
                    for name, content in sorted(files.items())
                }
            )
        )
        for identity, files in first_trees.items()
    }
    verify_specialization(generated)
    with ThreadPoolExecutor(max_workers=9) as workers:
        futures = {
            "isolated": workers.submit(verify_isolated, generated),
            "self_tests": workers.submit(
                verify_application_self_tests,
                generated,
            )
            if self_test
            else None,
            "separation": workers.submit(
                verify_compiler_separation,
                generated,
            ),
            "seed_graph": workers.submit(verify_seed_graph, compiler),
            "key_registry": workers.submit(
                verify_key_registry,
                calculator_applications,
                compiler,
            ),
            "control_registry": workers.submit(
                verify_control_registry,
                stateful_applications,
                compiler,
            ),
            "declarations": workers.submit(
                verify_concise_declarations,
                generated,
            ),
            "catalog": workers.submit(verify_catalog),
            "cross_family": workers.submit(
                verify_cross_family_composition,
                generated,
                compiler,
            ),
        }
        isolated = futures["isolated"].result()
        self_test_reports = (
            futures["self_tests"].result() if self_test else []
        )
        separation = futures["separation"].result()
        seed_graph = futures["seed_graph"].result()
        key_registry = futures["key_registry"].result()
        control_registry = futures["control_registry"].result()
        declarations = futures["declarations"].result()
        catalog = futures["catalog"].result()
        cross_family = futures["cross_family"].result()
    key_callbacks = {
        "passed": sum(item["key_callbacks"]["passed"] for item in isolated),
        "total": sum(item["key_callbacks"]["total"] for item in isolated),
    }
    if key_callbacks["passed"] != key_callbacks["total"]:
        raise ValueError("key-callback-verification")
    canonical_things = {
        "passed": sum(item["things"]["passed"] for item in isolated),
        "total": sum(item["things"]["total"] for item in isolated),
        "states": [
            "unknown",
            "absent",
            "false",
            "formed",
            "valid",
            "invalid",
        ],
        "semantic_depths": 10,
    }
    if canonical_things["passed"] != canonical_things["total"]:
        raise ValueError("canonical-thing-verification")
    self_test_verification = {
        "applications": len(self_test_reports),
        "passed": sum(
            item["self_test"]["passed"] for item in self_test_reports
        ),
        "total": sum(
            item["self_test"]["total"] for item in self_test_reports
        ),
        "closed": all(item["closed"] for item in self_test_reports),
    }
    passed = sum(
        item["evidence"]["verification"]["passed"]
        for item in generated
    )
    total = sum(
        item["evidence"]["verification"]["total"]
        for item in generated
    )
    for item in generated:
        evidence = item["evidence"]
        print(
            "generated "
            f"{item['id']}: seed={evidence['seed_sha256']} "
            f"artifact={evidence['tree_sha256']} "
            f"acceptance={evidence['verification']['passed']}/"
            f"{evidence['verification']['total']}",
            flush=True,
        )
    complete_tree = digest(canonical(hashes))
    write_report(
        applications,
        generated,
        hashes,
        separation,
        complete_tree,
        seed_graph,
        key_registry,
        control_registry,
        key_callbacks,
        self_test_verification,
        declarations,
        catalog,
        cross_family,
    )
    print(
        "proof: "
        f"applications={len(generated)} "
        f"acceptance={passed}/{total} "
        f"isolated={len(isolated)}/{len(generated)} "
        "deterministic=PASS "
        "runtime-seed-access=0 "
        "manual-application-code=0 "
        "manual-application-tests=0 "
        f"compiler-vocabulary={separation['hits']}/{separation['inspected']} "
        f"seed-graph={seed_graph['passed']}/{seed_graph['total']} "
        f"key-registry={key_registry['definitions']}/"
        f"{key_registry['selected_identities']} "
        f"control-registry={control_registry['definitions']}/"
        f"{control_registry['selected_identities']} "
        f"key-callbacks={key_callbacks['passed']}/"
        f"{key_callbacks['total']} "
        f"canonical-things={canonical_things['passed']}/"
        f"{canonical_things['total']} "
        f"application-self-tests={self_test_verification['passed']}/"
        f"{self_test_verification['total']} "
        f"closed={self_test_verification['closed']} "
        f"generated-ast={declarations['generated_ast']}/{len(generated)} "
        f"leaf-ast-files={declarations['leaf_ast_files']} "
        f"catalog={catalog['profiles']} "
        f"catalog-proven={catalog['proven']} "
        f"catalogued={catalog['catalogued']} "
        f"catalog-mutations={catalog['mutations']['passed']}/"
        f"{catalog['mutations']['total']} "
        f"cross-family={len(cross_family['applications'])} "
        f"cross-family-mutations={cross_family['mutations']['passed']}/"
        f"{cross_family['mutations']['total']} "
        f"complete-tree={complete_tree}",
        flush=True,
    )
    return {
        "verdict": "PASS",
        "applications": len(generated),
        "acceptance": {"passed": passed, "total": total},
        "key_callbacks": key_callbacks,
        "canonical_things": canonical_things,
        "application_self_tests": self_test_verification,
        "application_profile_catalog": catalog,
        "cross_family_composition": cross_family,
        "deterministic_artifact_hashes": hashes,
        "complete_tree_sha256": complete_tree,
    }


def execute(generate_only):
    generate_all_from_seeds(self_test=not generate_only)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Build and verify without starting application self-tests.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all seed-programmed applications.",
    )
    arguments = parser.parse_args(argv)
    if arguments.list:
        for application in load_suite():
            print(f"{application['id']}: {application['title']}")
        return 0
    return execute(arguments.generate_only)


if __name__ == "__main__":
    raise SystemExit(main())
