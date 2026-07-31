import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = importlib.util.spec_from_file_location(
    "manual_single_api",
    ROOT / "tools" / "single_api.py",
)
SINGLE_API = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(SINGLE_API)


class SingleApiContractTests(unittest.TestCase):
    def test_single_api_delegates_to_complete_seed_flow_once(self):
        expected = {"verdict": "PASS"}
        root = {"identity": "uc://roots/unified-code@1", "verdict": "PASS"}
        with (
            patch.object(
                SINGLE_API,
                "generate_all_from_seeds",
                return_value=expected,
            ) as operation,
            patch.object(SINGLE_API, "verify_root", return_value=root),
        ):
            result = SINGLE_API.single_api()
        self.assertEqual(result, {**expected, "root": root})
        operation.assert_called_once_with(self_test=True)


if __name__ == "__main__":
    unittest.main()
