import json
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_layout import classify, complete_tree_digest, coordinates
from verify_all import observe_products, verify_product_first_layout, write_index


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

    def test_complete_tree_identity_observes_every_non_identity_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("first\n", encoding="utf-8")
            (root / "index.json").write_text("{}\n", encoding="utf-8")
            first = complete_tree_digest(root)
            (root / "README.md").write_text("second\n", encoding="utf-8")
            second = complete_tree_digest(root)
            self.assertNotEqual(first, second)
            (root / "complete-tree.sha256").write_text(
                second + "\n",
                encoding="utf-8",
            )
            self.assertEqual(complete_tree_digest(root), second)

    def test_navigation_rejects_corrupted_index_and_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity, paths = classify(
                root,
                self.leaf,
                {"resolved": True},
                self.files,
                "calculators",
            )
            item = {
                "id": "example",
                "identity": identity,
                "authority_path": paths["authority"],
                "specification_path": paths["specification"],
                "source_path": paths["source"],
                "application": paths["product"] / "main.py",
                "output_path": paths["product"],
                "test_path": paths["test"],
                "traceability_path": paths["traceability"],
                "manifest_path": paths["manifest"],
            }
            (root / "reports").mkdir()
            write_index(root, [item], "product-tree")
            complete = complete_tree_digest(root)
            (root / "complete-tree.sha256").write_text(complete + "\n")
            verify_product_first_layout(root, [item], complete)

            index_path = root / "index.json"
            original_index = index_path.read_bytes()
            index = json.loads(original_index)
            index["products"][0]["variation"] = "wrong"
            index_path.write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, "build-index-invalid"):
                verify_product_first_layout(root, [item], complete)
            index_path.write_bytes(original_index)

            readme = root / "README.md"
            readme.write_text("wrong destination\n")
            with self.assertRaisesRegex(ValueError, "build-readme-invalid"):
                verify_product_first_layout(root, [item], complete)

    def test_every_product_lens_detects_its_missing_distinction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = {
                "seed_sha256": "seed",
                "authorities": [{"identity": "authority"}],
            }
            trace_raw = json.dumps(trace, sort_keys=True).encode()
            main = b"print('example')\n"
            tests = b"pass\n"
            manifest = {
                "identity": self.leaf["what"]["identity"],
                "seed_sha256": "seed",
                "authorities": trace["authorities"],
                "files": {
                    "main.py": hashlib.sha256(main).hexdigest(),
                    "test_generated.py": hashlib.sha256(tests).hexdigest(),
                    "traceability.json": hashlib.sha256(trace_raw).hexdigest(),
                },
                "verification": {"passed": 1, "total": 1},
                "runtime_seed_files": 0,
                "manual_application_files": 0,
                "manual_test_files": 0,
            }
            files = {
                "main.py": main,
                "test_generated.py": tests,
                "traceability.json": trace_raw,
                "manifest.json": json.dumps(manifest).encode(),
            }
            identity, paths = classify(
                root,
                self.leaf,
                {"identity": self.leaf["what"]["identity"]},
                files,
                "calculators",
            )
            item = {
                "id": "example",
                "identity": identity,
                "leaf_document": self.leaf,
                "authority_path": paths["authority"],
                "specification_path": paths["specification"],
                "source_path": paths["source"],
                "application": paths["product"] / "main.py",
                "output_path": paths["product"],
                "test_path": paths["test"],
                "traceability_path": paths["traceability"],
                "manifest_path": paths["manifest"],
            }
            self.assertEqual(observe_products([item])["passed"], 4)

            paths["source"].unlink()
            with self.assertRaisesRegex(ValueError, "behold"):
                observe_products([item])
            paths["source"].write_bytes(main)

            item["leaf_document"]["what"]["identity"]["variation"] = "wrong"
            with self.assertRaisesRegex(ValueError, "see"):
                observe_products([item])
            item["leaf_document"]["what"]["identity"]["variation"] = "example"

            item["application"].write_bytes(b"changed\n")
            with self.assertRaisesRegex(ValueError, "investigate"):
                observe_products([item])
            item["application"].write_bytes(main)

            changed_trace = dict(trace)
            changed_trace["authorities"] = []
            item["traceability_path"].write_text(json.dumps(changed_trace))
            with self.assertRaisesRegex(ValueError, "understand"):
                observe_products([item])

    def test_malformed_navigation_is_named(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "README.md").write_text("unused", encoding="utf-8")
            (root / "index.json").write_text("{}", encoding="utf-8")
            (root / "complete-tree.sha256").write_text(
                "unused\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "build-index-invalid"):
                verify_product_first_layout(root, [], "unused")


if __name__ == "__main__":
    unittest.main()
