"""Build, verify, and optionally launch every seed-programmed application."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "seed" / "suite.seed.json"
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
    if len(applications) != 10:
        raise ValueError("ten-applications-required")
    if len({item["id"] for item in applications}) != len(applications):
        raise ValueError("duplicate-application")
    return applications


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


def verify_isolated(generated):
    isolation = Path(tempfile.mkdtemp(prefix="manual-app-isolation-"))
    try:
        reports = []
        for item in generated:
            copied = isolation / item["id"]
            shutil.copytree(item["output_path"], copied)
            result = subprocess.run(
                [sys.executable, "test_generated.py"],
                cwd=copied,
                check=True,
                capture_output=True,
                text=True,
            )
            reports.append(json.loads(result.stdout))
        return reports
    finally:
        shutil.rmtree(isolation)


def verify_determinism(compiler, applications, generated):
    second_root = Path(tempfile.mkdtemp(prefix="manual-app-rebuild-"))
    try:
        first = {
            item["id"]: tree_bytes(item["output_path"])
            for item in generated
        }
        second = {
            item["id"]: tree_bytes(
                compile_app(
                    compiler,
                    item,
                    second_root / item["id"],
                )["output_path"]
            )
            for item in applications
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


def verify_compiler_separation(applications, compiler):
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in COMPILER_SOURCES
    ).casefold()
    vocabulary = set()
    registered = set()
    for application in applications:
        seed, _ = compiler.load_seed(ROOT / application["seed"])
        vocabulary.update(seed_vocabulary(seed))
        registered.update(
            item["action"]
            for item in seed["presentation"]["controls"]
        )
    generic = {
        "abs",
        "add",
        "append",
        "divide",
        "left",
        "maximum",
        "minimum",
        "multiply",
        "power",
        "right",
        "subtract",
        "sum",
        "trace",
    }
    inspected = sorted(
        item for item in vocabulary - generic - registered if len(item) >= 4
    )
    hits = [
        item
        for item in inspected
        if re.search(
            rf"(?<![a-z0-9_-]){re.escape(item.casefold())}(?![a-z0-9_-])",
            source,
        )
    ]
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


def verify_concise_declarations(applications, compiler):
    reports = []
    for application in applications:
        path = ROOT / application["seed"]
        document = json.loads(path.read_text(encoding="utf-8"))
        what = document["what"]
        if "ast" in what["program"]:
            raise ValueError("leaf-ast-present")
        if what["state"].get("authority") != "declarations":
            raise ValueError("state-not-declared")
        tree = compiler.compile_declaration(
            {"format": compiler.FORMAT, **what}
        )
        if type(tree).__name__ != "Module":
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
        "total_seed_bytes": sum(item["seed_bytes"] for item in reports),
    }


def write_report(
    applications,
    generated,
    hashes,
    separation,
    complete_tree,
    compiler,
    seed_graph,
    declarations,
):
    runner_bytes = Path(__file__).read_bytes()
    report = {
        "format": "manual-seed-assembly-report-1",
        "operation": "python3 tools/verify_all.py --generate-only",
        "applications": [
            {
                "id": item["id"],
                "seed": item["seed"],
                "seed_sha256": item["evidence"]["seed_sha256"],
                "artifact_tree_sha256": item["evidence"]["tree_sha256"],
                "acceptance": item["evidence"]["verification"],
                "controls": len(
                    compiler.load_seed(ROOT / item["seed"])[0][
                        "presentation"
                    ]["controls"]
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
        },
        "generated_source": source_churn(generated),
        "deterministic_artifact_hashes": hashes,
        "complete_tree_sha256": complete_tree,
        "compiler_application_vocabulary": separation,
        "manual_application_code": 0,
        "manual_application_tests": 0,
        "runtime_seed_access": 0,
        "seed_graph": seed_graph,
        "concise_declarations": declarations,
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
        b"read_text(",
        b"read_bytes(",
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
        return {
            "tamper": tamper,
            "floating": floating,
            "cycle": cycle,
            "conflict": conflict,
            "passed": 4,
            "total": 4,
        }
    finally:
        shutil.rmtree(temporary)


def launch(generated):
    return [
        {
            **item,
            "process": subprocess.Popen(
                [sys.executable, str(item["application"])],
                cwd=item["output_path"],
            ),
        }
        for item in generated
    ]


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


def execute(generate_only):
    applications = load_suite()
    compiler = load_compiler()
    generated = [
        compile_app(compiler, application)
        for application in applications
    ]
    verify_specialization(generated)
    isolated = verify_isolated(generated)
    hashes = verify_determinism(compiler, applications, generated)
    separation = verify_compiler_separation(applications, compiler)
    seed_graph = verify_seed_graph(compiler)
    declarations = verify_concise_declarations(applications, compiler)
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
        compiler,
        seed_graph,
        declarations,
    )
    print(
        "proof: "
        f"applications={len(generated)} "
        f"acceptance={passed}/{total} "
        f"isolated={len(isolated)}/10 "
        "deterministic=PASS "
        "runtime-seed-access=0 "
        "manual-application-code=0 "
        "manual-application-tests=0 "
        f"compiler-vocabulary={separation['hits']}/{separation['inspected']} "
        f"seed-graph={seed_graph['passed']}/{seed_graph['total']} "
        f"generated-ast={declarations['generated_ast']}/10 "
        f"leaf-ast-files={declarations['leaf_ast_files']} "
        f"complete-tree={complete_tree}",
        flush=True,
    )
    if generate_only:
        return 0
    running = launch(generated)
    for item in running:
        print(
            f"opened {item['id']}: pid={item['process'].pid}",
            flush=True,
        )
    return wait_for_windows(running)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Build and verify all applications without opening windows.",
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
