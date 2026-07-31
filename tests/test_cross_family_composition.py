import copy
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import seed_compiler as COMPILER


class CrossFamilyCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_path = (
            ROOT / "seed" / "applications" / "costed-todo.seed.json"
        )
        cls.seed, cls.authorities = COMPILER.load_seed(cls.seed_path)

    def test_seed_calculation_is_specialized_and_traceable(self):
        manifest, files = COMPILER.assemble_resolved(
            self.seed,
            self.authorities,
        )
        source = files["main.py"].decode()
        trace = json.loads(files["traceability.json"])
        self.assertIn(
            "def _calculation_0(quantity, unit_price):",
            source,
        )
        self.assertIn("return (quantity * unit_price)", source)
        self.assertNotIn("semantic_expression", source)
        self.assertNotIn("def expression(", source)
        self.assertEqual(
            [
                {
                    "identity": item["identity"],
                    "seed_path": item["seed_path"],
                }
                for item in trace["semantic_functions"]
            ],
            [{
                "identity": "line_total",
                "seed_path": (
                    "/semantics/calculations/functions/0/body"
                ),
            }],
        )
        self.assertEqual(manifest["runtime_seed_files"], 0)
        self.assertEqual(manifest["runtime_shared_engine_files"], 0)

    def test_generated_acceptance_and_callbacks_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "costed-todo"
            COMPILER.generate(self.seed_path, output)
            specification = importlib.util.spec_from_file_location(
                "generated_costed_todo_tests",
                output / "test_generated.py",
            )
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                result = module.run()
            report = json.loads(stream.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["passed"], 2)
        self.assertEqual(report["total"], 2)
        self.assertEqual(
            report["key_callbacks"],
            {"passed": 7, "total": 7},
        )

    def test_unknown_calculation_is_rejected(self):
        mutated = copy.deepcopy(self.seed)
        mutated["semantics"]["calculations"]["functions"][0][
            "id"
        ] = "unreachable"
        with self.assertRaisesRegex(
            ValueError,
            "^unknown-stateful-calculation$",
        ):
            COMPILER.render_declaration_source(mutated)

    def test_wrong_calculation_arity_is_rejected(self):
        mutated = copy.deepcopy(self.seed)
        calculate = mutated["semantics"]["commands"][0]["effects"][0][
            "value"
        ]["object"]["total"]["calculate"]
        calculate["arguments"].pop()
        with self.assertRaisesRegex(
            ValueError,
            "^invalid-stateful-calculation-arity$",
        ):
            COMPILER.render_declaration_source(mutated)


if __name__ == "__main__":
    unittest.main()
