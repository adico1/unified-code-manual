import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import root_authority


class RootAuthorityTests(unittest.TestCase):
    def test_root_is_the_single_pinned_operation_authority(self):
        result = root_authority.verify_root(ROOT / "seed" / "ROOT.seed.json")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["semantic_depths"], 10)
        self.assertEqual(result["open_gaps"], [])
        self.assertGreater(result["authorities"], 10)

    def test_changed_authority_is_rejected(self):
        original = json.loads(
            (ROOT / "seed" / "ROOT.seed.json").read_text(encoding="utf-8")
        )
        mutated = copy.deepcopy(original)
        mutated["authorities"][0]["sha256"] = "0" * 64
        load = root_authority.load_json

        def changed(path):
            return mutated if Path(path).name == "ROOT.seed.json" else load(path)

        with patch.object(root_authority, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "authority-hash"):
                root_authority.verify_root(ROOT / "seed" / "ROOT.seed.json")


if __name__ == "__main__":
    unittest.main()
