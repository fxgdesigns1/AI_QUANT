import unittest
from pathlib import Path


class TestPhase8LOneClickContract(unittest.TestCase):
    def test_ps1_has_no_runner_restart(self):
        root = Path(__file__).resolve().parents[1]
        ps1 = (root / "scripts" / "phase8l_one_click_build_research_env.ps1").read_text(encoding="utf-8")
        self.assertNotIn("ai-quant-runner", ps1.lower())

    def test_ps1_prints_macbook_pull_commands(self):
        root = Path(__file__).resolve().parents[1]
        ps1 = (root / "scripts" / "phase8l_one_click_build_research_env.ps1").read_text(encoding="utf-8")
        self.assertIn("latest_phase8l_research_result_manifest.json", ps1)
        self.assertIn("MacBook pull commands", ps1)

    def test_importer_does_not_touch_runtime_config(self):
        root = Path(__file__).resolve().parents[1]
        src = (root / "scripts" / "phase8l_import_result_pack_to_alpha.py").read_text(encoding="utf-8")
        self.assertNotIn("runtime/config.yaml", src)


if __name__ == "__main__":
    unittest.main()
