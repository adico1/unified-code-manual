import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
from copy import deepcopy


ROOT = Path(__file__).resolve().parents[1]
COMPILER_PATH = ROOT / "src" / "seed_compiler.py"
sys.path.insert(0, str(ROOT / "src"))


def load_compiler():
    specification = importlib.util.spec_from_file_location(
        "observatory_seed_compiler", COMPILER_PATH
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class DevelopmentObservatoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = load_compiler()
        cls.seed_path = ROOT / "seed/applications/development-observatory.seed.json"
        cls.generated_directory = tempfile.TemporaryDirectory()
        cls.generated = Path(cls.generated_directory.name)
        cls.manifest = cls.compiler.generate(cls.seed_path, cls.generated)

    @classmethod
    def tearDownClass(cls):
        cls.generated_directory.cleanup()

    def test_seed_is_complete_and_compiles_without_runtime_authority(self):
        resolved, authorities = self.compiler.load_seed(self.seed_path)
        self.assertEqual(self.compiler.validate(resolved), [])
        self.assertGreater(len(authorities), 2)
        source = (self.generated / "main.py").read_text(encoding="utf-8")
        self.assertEqual(self.manifest["runtime_seed_files"], 0)
        self.assertIn("uc://manual/applications/development-observatory@1", source)
        self.assertIn("columnconfigure", source)
        self.assertIn("rowconfigure", source)
        self.assertIn("Treeview", source)
        self.assertIn("Development lifecycle — past, present and future", source)
        self.assertIn("Select an observation", source)
        self.assertIn("webbrowser.open", source)
        self.assertIn("Archive Request", source)
        self.assertIn("askyesno", source)
        self.assertIn("def command_archive", source)
        self.assertNotIn("def command_remove", source)
        self.assertIn("--case-json", source)
        self.assertNotIn("seed_compiler", source)

    def test_generated_api_and_acceptance_are_functional(self):
        specification = importlib.util.spec_from_file_location(
            "generated_observatory", self.generated / "main.py"
        )
        application = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(application)
        report = application.run_acceptance()
        self.assertEqual(report["passed"], report["total"])
        opened = []
        application._open_url = opened.append
        outcome = application.run_command(
            "open_link", {"link": "https://example.test/code"}
        )
        self.assertIsNone(outcome["error"])
        self.assertEqual(opened, ["https://example.test/code"])
        rejected = application.run_command("open_link", {"link": "file:///tmp/code"})
        self.assertEqual(rejected["error"], "invalid-link")
        self.assertEqual(opened, ["https://example.test/code"])
        case = json.loads(self.seed_path.read_text(encoding="utf-8"))["what"][
            "acceptance"
        ][0]["input"]
        thing = application.part(
            {"value": case, "state": "formed", "evidence": ()}
        )
        self.assertEqual(thing["state"], "valid")
        self.assertEqual(len(thing["depths"]), 10)
        cli = subprocess.run(
            [
                sys.executable,
                str(self.generated / "main.py"),
                "--case-json",
                json.dumps(case),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(cli.stdout), thing["value"])

    def test_dashboard_vocabulary_is_absent_from_generic_creators(self):
        vocabulary = {
            "development-observatory",
            "מלך_עולם",
            "אדון_הכל",
            "architecture-status",
            "root-fixed-point",
        }
        creators = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "src").glob("*.py"))
        )
        self.assertEqual({term for term in vocabulary if term in creators}, set())

    def test_every_watcher_and_sign_is_required_for_every_record(self):
        resolved, _authorities = self.compiler.load_seed(self.seed_path)
        required = ("הבט", "ראה", "חקור", "הבן", "מלך_עולם", "אדון_הכל")
        for identity in required:
            mutated = deepcopy(resolved)
            mutated["state"]["initial"]["observations"][0].pop(identity)
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(
                    ValueError,
                    "record-contract-field-missing",
                ):
                    self.compiler.render_program(mutated)

    def test_progress_is_derived_before_compilation(self):
        leaf = json.loads(self.seed_path.read_text(encoding="utf-8"))["what"]
        self.assertTrue(
            all("progress" not in record for record in leaf["state"]["initial"]["observations"])
        )
        resolved, _authorities = self.compiler.load_seed(self.seed_path)
        for record in resolved["state"]["initial"]["observations"]:
            self.assertEqual(
                record["progress"],
                record["passed"] * 100 // record["total"],
            )

    def test_generated_test_runs_from_published_verification_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = root / "product" / "application"
            verification = root / "product" / "verification"
            application.mkdir(parents=True)
            verification.mkdir(parents=True)
            shutil.copy2(self.generated / "main.py", application / "main.py")
            shutil.copy2(
                self.generated / "test_generated.py",
                verification / "test_generated.py",
            )
            result = subprocess.run(
                [sys.executable, str(verification / "test_generated.py")],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_lazy_launch_rebuilds_interface_before_loading_state(self):
        specification = importlib.util.spec_from_file_location(
            "generated_observatory_launch", self.generated / "main.py"
        )
        application = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(application)
        original = application.build_interface
        original_self_test = application.self_test_interface
        reports = []

        def build_and_close():
            root = original()
            root.withdraw()
            root.mainloop = root.destroy
            return root

        application.build_interface = build_and_close

        def observed_self_test():
            report = original_self_test()
            reports.append(report)
            return report

        application.self_test_interface = observed_self_test
        with tempfile.TemporaryDirectory() as directory:
            application.configure_state_path(Path(directory) / "state.json")
            application.launch()
        self.assertEqual(reports[0]["self_test"], {"passed": 18, "total": 18})
        self.assertEqual(
            reports[0]["interactions"],
            [
                "ask-ai",
                "complete-request",
                "reopen-request",
                "protect-system-completion",
                "open-code",
                "decline-archive",
                "archive-request",
                "protect-system-archive",
                "filter-all",
                "filter-past",
                "filter-present",
                "filter-future",
            ],
        )

    def test_structured_dashboard_presents_summary_table_and_details(self):
        specification = importlib.util.spec_from_file_location(
            "generated_observatory_surface", self.generated / "main.py"
        )
        application = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(application)
        with tempfile.TemporaryDirectory() as directory:
            application.configure_state_path(Path(directory) / "state.json")
            application.reset_state()
            root = application.build_interface()
            root.withdraw()
            table = application._collections["collection.primary"]
            self.assertEqual(
                tuple(table["columns"]),
                ("temporal", "observer", "phase", "progress", "title"),
            )
            self.assertEqual(len(table.get_children()), 4)
            self.assertEqual(
                tuple(application._metric_cards),
                (
                    "generated products",
                    "product families",
                    "acceptance cases",
                    "generated GUI checks",
                    "verification budget",
                ),
            )
            self.assertEqual(len(application._portfolio.get_children()), 74)
            portfolio_groups = {
                application._portfolio.set(item, "group")
                for item in application._portfolio.get_children()
            }
            self.assertEqual(
                portfolio_groups,
                {"calculators", "dashboards", "pong-games", "todos"},
            )
            application._tabs.select(1)
            root.update_idletasks()
            self.assertEqual(application._tabs.index(application._tabs.select()), 1)
            application._tabs.select(0)
            self.assertIn("4 shown / 4 total", application._summary.get())
            detail = application._details["collection.primary"].get("1.0", "end")
            self.assertIn("Milestone 1 seed-to-application proof", detail)
            self.assertIn("מלך_עולם", detail)
            application._buttons["filter.future"].invoke()
            self.assertEqual(len(table.get_children()), 1)
            self.assertIn("1 shown / 4 total", application._summary.get())
            root.destroy()


if __name__ == "__main__":
    unittest.main()
