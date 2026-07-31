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

    def test_complete_verification_budget_includes_unit_suite(self):
        process = unittest.mock.Mock()
        process.communicate.return_value = ("Ran 241 tests in 1.0s\nOK", "")
        process.returncode = 0
        clock = iter((10.0, 14.9))
        with (
            patch.object(SINGLE_API.subprocess, "Popen", return_value=process),
            patch.object(SINGLE_API, "single_api", return_value={"verdict": "PASS"}),
            patch.object(SINGLE_API.time, "perf_counter", side_effect=clock),
        ):
            result, elapsed = SINGLE_API.verify_complete()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["unit_tests"], 241)
        self.assertEqual(elapsed, 4.9)
        process.communicate.assert_called_once_with(timeout=5.0)

    def test_complete_verification_rejects_total_budget_overrun(self):
        process = unittest.mock.Mock()
        process.communicate.return_value = ("Ran 241 tests in 1.0s\nOK", "")
        process.returncode = 0
        clock = iter((10.0, 15.1))
        with (
            patch.object(SINGLE_API.subprocess, "Popen", return_value=process),
            patch.object(SINGLE_API, "single_api", return_value={"verdict": "PASS"}),
            patch.object(SINGLE_API.time, "perf_counter", side_effect=clock),
        ):
            with self.assertRaisesRegex(RuntimeError, "verification-budget-exceeded"):
                SINGLE_API.verify_complete()


if __name__ == "__main__":
    unittest.main()
