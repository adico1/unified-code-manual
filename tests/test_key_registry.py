import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import seed_compiler as COMPILER


class KeyRegistryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leaf = ROOT / "seed" / "applications" / "normal.seed.json"
        cls.what = json.loads(cls.leaf.read_text(encoding="utf-8"))["what"]
        family = ROOT / "seed" / "families" / "calculator.seed.json"
        provisions, authorities = COMPILER.resolve_base(
            family,
            json.loads(family.read_text(encoding="utf-8")),
        )
        cls.assembly = provisions["assembly"]
        cls.registry = provisions["key_registry"]
        cls.registry_authority = next(
            item
            for item in authorities
            if "key_registry" in item.get("provides", ())
        )
        cls.leaf_authority = {
            "identity": cls.what["identity"]["canonical"],
            "kind": "what-authority",
            "sha256": COMPILER.document_digest(
                json.loads(cls.leaf.read_text(encoding="utf-8"))
            ),
        }
        cls.generated_directory = tempfile.TemporaryDirectory()
        cls.generated_output = Path(cls.generated_directory.name) / "normal"
        _manifest, files = COMPILER.assemble(cls.leaf)
        cls.generated_output.mkdir()
        for name, content in files.items():
            cls.generated_output.joinpath(name).write_bytes(content)
        specification = importlib.util.spec_from_file_location(
            "generated_normal_self_test",
            cls.generated_output / "main.py",
        )
        cls.generated_application = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.generated_application)
        class Variable:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        class Root:
            def __init__(self):
                self.children = []

            def title(self, _value):
                return None

            def geometry(self, _value):
                return None

            def configure(self, **_values):
                return None

            def grid_columnconfigure(self, _column, **_values):
                return None

            def grid_slaves(self, *, row, column):
                return [
                    child
                    for child in reversed(self.children)
                    if child.row == row and child.column == column
                ]

            def destroy(self):
                self.children.clear()

        class Widget:
            kind = "Widget"

            def __init__(self, root, **values):
                self.root = root
                self.values = values
                self.row = None
                self.column = None
                root.children.append(self)

            def grid(self, *, row, column, **_values):
                self.row = row
                self.column = column
                return self

            def winfo_class(self):
                return self.kind

            def cget(self, identity):
                return self.values[identity]

            def destroy(self):
                self.root.children.remove(self)

        class Button(Widget):
            kind = "Button"

            def invoke(self):
                return self.values["command"]()

        cls.generated_application.Tk = Root
        cls.generated_application.StringVar = Variable
        cls.generated_application.Button = Button
        cls.generated_application.Entry = Widget
        cls.generated_application.Label = Widget

    @classmethod
    def tearDownClass(cls):
        cls.generated_directory.cleanup()

    def materialize_with(self, identity, mutation):
        registry = copy.deepcopy(self.registry)
        definition = next(
            item for item in registry if item["identity"] == identity
        )
        mutation(definition)
        return COMPILER.materialize(
            self.what,
            self.assembly,
            registry,
            self.registry_authority,
            self.leaf_authority,
        )

    def test_argument_required_action_rejects_missing_value(self):
        with self.assertRaisesRegex(
            ValueError,
            "^invalid-key-arguments:digit\\.7$",
        ):
            self.materialize_with(
                "digit.7",
                lambda definition: definition.pop("value"),
            )

    def test_argument_required_action_rejects_non_string_value(self):
        with self.assertRaisesRegex(
            ValueError,
            "^invalid-key-arguments:digit\\.7$",
        ):
            self.materialize_with(
                "digit.7",
                lambda definition: definition.__setitem__("value", 7),
            )

    def test_argument_free_action_rejects_value(self):
        with self.assertRaisesRegex(
            ValueError,
            "^invalid-key-arguments:command\\.clear\\.word$",
        ):
            self.materialize_with(
                "command.clear.word",
                lambda definition: definition.__setitem__(
                    "value",
                    "unexpected",
                ),
            )

    def test_required_capability_identity_must_resolve_once(self):
        what = copy.deepcopy(self.what)
        duplicate = copy.deepcopy(
            next(
                item
                for item in what["semantics"]["operations"]["binary"]
                if item["id"] == "add"
            )
        )
        duplicate["target"] = "operator.sub"
        what["semantics"]["operations"]["binary"].append(duplicate)
        with self.assertRaisesRegex(
            ValueError,
            "^duplicate-capability-identity:operation\\.add$",
        ):
            COMPILER.materialize(
                what,
                self.assembly,
                self.registry,
                self.registry_authority,
                self.leaf_authority,
            )

    def test_trace_names_placement_and_registry_definition(self):
        trace = json.loads(
            self.generated_output.joinpath("traceability.json").read_text(
                encoding="utf-8"
            )
        )
        key = next(
            item
            for item in trace["controls"]
            if item["identity"] == "digit.7"
        )
        self.assertEqual(
            key["placement"]["authority"],
            "uc://manual/calculators/normal@1",
        )
        self.assertRegex(
            key["placement"]["authority_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(
            key["placement"]["path"],
            "/what/presentation/keys/0",
        )
        self.assertEqual(
            key["registry"]["authority"],
            "uc://manual/registries/calculator-keys@1",
        )
        self.assertRegex(
            key["registry"]["definition_path"],
            r"^/provides/key_registry/[0-9]+$",
        )
        self.assertRegex(key["registry"]["definition_sha256"], r"^[0-9a-f]{64}$")
        operation = next(
            item
            for item in trace["controls"]
            if item["identity"] == "operator.expression.add"
        )
        self.assertEqual(operation["capability"]["identity"], "operation.add")
        self.assertEqual(
            operation["capability"]["authority"],
            "uc://manual/calculators/normal@1",
        )
        self.assertRegex(
            operation["capability"]["authority_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertRegex(
            operation["capability"]["path"],
            r"^/what/semantics/operations/[^/]+/[0-9]+$",
        )
        self.assertRegex(
            operation["capability"]["definition_sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_generated_tests_verify_every_key_callback(self):
        result = subprocess.run(
            [sys.executable, "test_generated.py"],
            cwd=self.generated_output,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        report = json.loads(result.stdout)
        self.assertEqual(
            report["key_callbacks"],
            {"passed": 20, "total": 20},
        )

    def test_generated_tests_reject_wrong_key_value(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normal"
            shutil.copytree(self.generated_output, output)
            application = output / "main.py"
            source = application.read_text(encoding="utf-8")
            mutated = source.replace(
                "text='7', command=lambda value='7': append(value)",
                "text='7', command=lambda value='9': append(value)",
                1,
            )
            self.assertNotEqual(source, mutated)
            application.write_text(mutated, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "test_generated.py"],
                cwd=output,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["key_callbacks"]["passed"], 19)
        self.assertEqual(report["key_callbacks"]["total"], 20)

    def test_generated_tests_gate_atomic_install(self):
        failing_tests = b"def run(*, emit=True):\n    return 1\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normal"
            with patch.object(COMPILER, "render_tests", return_value=failing_tests):
                with self.assertRaisesRegex(
                    ValueError,
                    "^generated-tests-failed$",
                ):
                    COMPILER.generate(self.leaf, output)
            self.assertFalse(output.exists())

    def test_generated_application_self_tests_callback_contract(self):
        report = self.generated_application.self_test_application()
        self.assertEqual(report["self_test"], {"passed": 21, "total": 21})
        self.assertTrue(report["closed"])

    def test_generated_application_self_test_rejects_broken_route(self):
        operation = self.generated_application.clear

        def broken_route(_value):
            raise RuntimeError("broken-route")

        self.generated_application.clear = broken_route
        try:
            report = self.generated_application.self_test_application()
        finally:
            self.generated_application.clear = operation
        self.assertLess(
            report["self_test"]["passed"],
            report["self_test"]["total"],
        )
        self.assertTrue(report["closed"])


if __name__ == "__main__":
    unittest.main()
