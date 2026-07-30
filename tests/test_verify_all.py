import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = importlib.util.spec_from_file_location(
    "manual_verify_all",
    ROOT / "tools" / "verify_all.py",
)
VERIFY_ALL = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(VERIFY_ALL)


class DynamicSuiteTests(unittest.TestCase):
    def test_suite_size_is_declared_by_enabled_applications(self):
        applications = [
            {
                "enabled": True,
                "id": f"application-{index}",
            }
            for index in range(11)
        ]
        document = {
            "format": "manual-seed-program-suite-3",
            "applications": applications,
        }
        with tempfile.TemporaryDirectory() as directory:
            suite = Path(directory) / "suite.seed.json"
            suite.write_text(json.dumps(document), encoding="utf-8")
            with patch.object(VERIFY_ALL, "SUITE", suite):
                loaded = VERIFY_ALL.load_suite()
        self.assertEqual(
            [item["id"] for item in loaded],
            [item["id"] for item in applications],
        )


if __name__ == "__main__":
    unittest.main()
