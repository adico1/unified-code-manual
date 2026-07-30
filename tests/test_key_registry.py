import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_trace_names_placement_and_registry_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normal"
            COMPILER.generate(self.leaf, output)
            trace = json.loads(
                output.joinpath("traceability.json").read_text(
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
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normal"
            COMPILER.generate(self.leaf, output)
            result = subprocess.run(
                [sys.executable, "test_generated.py"],
                cwd=output,
                check=True,
                capture_output=True,
                text=True,
            )
        report = json.loads(result.stdout)
        self.assertEqual(
            report["key_callbacks"],
            {"passed": 20, "total": 20},
        )


if __name__ == "__main__":
    unittest.main()
