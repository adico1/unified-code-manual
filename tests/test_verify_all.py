import importlib.util
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
    def test_macos_worker_thread_cannot_select_fork_context(self):
        with (
            patch.object(VERIFY_ALL.sys, "platform", "darwin"),
            ThreadPoolExecutor(max_workers=1) as worker,
        ):
            context = worker.submit(VERIFY_ALL.safe_process_context).result()
        self.assertIsNone(context)

    def test_main_thread_retains_fast_fork_before_gui_startup(self):
        with patch.object(VERIFY_ALL.sys, "platform", "darwin"):
            context = VERIFY_ALL.safe_process_context()
        self.assertEqual(context.get_start_method(), "fork")

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
            with (
                patch.object(VERIFY_ALL, "SUITE", suite),
                patch.object(VERIFY_ALL, "materialize_catalog", return_value=[]),
            ):
                loaded = VERIFY_ALL.load_suite()
        self.assertEqual(
            [item["id"] for item in loaded],
            [item["id"] for item in applications],
        )

    def test_gui_verification_executes_generated_application_entrypoint(self):
        source = (
            ROOT / "tools" / "verify_all.py"
        ).read_text(encoding="utf-8")
        self.assertIn("path=pathlib.Path(root)/'main.py'", source)
        self.assertIn("self_test_application", source)
        self.assertNotIn('"test_generated.py", "--gui-e2e"', source)


if __name__ == "__main__":
    unittest.main()
