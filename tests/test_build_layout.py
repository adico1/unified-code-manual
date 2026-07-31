import json
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_layout import classify, coordinates


class ProductFirstBuildLayoutTests(unittest.TestCase):
    def setUp(self):
        self.leaf = {
            "format": "test",
            "what": {
                "identity": {
                    "canonical": "uc://manual/calculators/example@1",
                    "family": "calculator",
                    "variation": "example",
                    "version": 1,
                }
            },
        }
        self.files = {
            "main.py": b"print('example')\n",
            "test_generated.py": b"pass\n",
            "traceability.json": b"{}\n",
            "manifest.json": b"{}\n",
        }

    def test_canonical_identity_has_one_filesystem_key(self):
        identity = coordinates(self.leaf)
        self.assertEqual(identity["key"], "example@1")

    def test_identity_variation_drift_is_rejected(self):
        self.leaf["what"]["identity"]["variation"] = "different"
        with self.assertRaisesRegex(
            ValueError,
            "product-identity-variation-mismatch",
        ):
            coordinates(self.leaf)

    def test_user_finds_family_then_product_then_internal_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            identity, paths = classify(
                Path(directory),
                self.leaf,
                {"resolved": True},
                self.files,
                "calculators",
            )
            product = Path(directory) / "calculators" / "example@1"
            self.assertEqual(identity["group"], "calculators")
            self.assertEqual(paths["root"], product)
            self.assertEqual(
                sorted(path.name for path in product.iterdir()),
                [
                    "application",
                    "authority",
                    "manifest.json",
                    "source",
                    "specification",
                    "verification",
                ],
            )
            self.assertEqual(
                sorted(path.name for path in paths["product"].iterdir()),
                ["main.py"],
            )
            self.assertEqual(
                json.loads(paths["authority"].read_text()),
                self.leaf,
            )


if __name__ == "__main__":
    unittest.main()
