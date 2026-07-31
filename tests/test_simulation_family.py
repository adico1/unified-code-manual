import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

import seed_compiler as COMPILER
from catalog_materializer import materialize_catalog


class SimulationFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_path = ROOT / "seed/applications/classic-paddle-duel.seed.json"
        cls.resolved, cls.authorities = COMPILER.load_seed(cls.seed_path)

    def test_classic_seed_generates_exact_acceptance(self):
        manifest, files = COMPILER.assemble_resolved(
            self.resolved,
            self.authorities,
        )
        self.assertEqual(manifest["verification"], {
            "cases": ["classic.motion", "classic.control"],
            "passed": 2,
            "total": 2,
        })
        source = files["main.py"].decode()
        self.assertNotIn("seed_compiler", source)
        self.assertNotIn(".seed.json", source)
        self.assertIn("def advance():", source)

    def test_unknown_control_identity_is_rejected(self):
        document = json.loads(self.seed_path.read_text(encoding="utf-8"))
        what = copy.deepcopy(document["what"])
        what["presentation"]["keys"][0]["key"] = "participant.unknown"
        family_path = ROOT / "seed/families/bounded-simulation.seed.json"
        provisions, authorities = COMPILER.resolve_base(
            family_path,
            json.loads(family_path.read_text(encoding="utf-8")),
        )
        registry_authority = next(
            item
            for item in authorities
            if "simulation_control_registry" in item.get("provides", ())
        )
        leaf_authority = {
            "identity": what["identity"]["canonical"],
            "sha256": COMPILER.document_digest(document),
        }
        with self.assertRaisesRegex(ValueError, "^unknown-key:participant.unknown$"):
            COMPILER.materialize_simulation(
                what,
                provisions["assembly"],
                provisions["simulation_control_registry"],
                registry_authority,
                leaf_authority,
            )

    def test_every_proven_paddle_profile_executes_generated_tests(self):
        applications = {
            item["id"]: item
            for item in materialize_catalog()
        }
        identities = (
            "solo-opponent",
            "wall-training",
            "doubles",
            "multiball",
            "power-up",
            "obstacle",
            "timed-score-attack",
        )
        with tempfile.TemporaryDirectory() as directory:
            for identity in identities:
                application = applications[identity]
                output = Path(directory) / identity
                COMPILER.generate(ROOT / application["seed"], output)
                specification = importlib.util.spec_from_file_location(
                    "generated_" + identity.replace("-", "_"),
                    output / "test_generated.py",
                )
                module = importlib.util.module_from_spec(specification)
                specification.loader.exec_module(module)
                self.assertEqual(module.run(emit=False), 0, identity)


if __name__ == "__main__":
    unittest.main()
