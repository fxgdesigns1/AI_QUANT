import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.phase8l_alpha_export_research_data import build_dry_run_plan, run_export


class TestPhase8LAlphaExport(unittest.TestCase):
    def test_dry_run_plan_no_credentials_needed(self):
        plan = build_dry_run_plan(
            instruments=["EUR_USD"],
            granularities=["M15"],
            days=14,
            output_dir=Path("/tmp/x"),
            max_export_size_bytes=500 * 1024 * 1024,
            credentials_present=False,
        )
        self.assertEqual(plan["phase"], "Phase 8L")
        self.assertIn("would_refuse_preflight", plan)

    def test_manifest_shape_secret_flags(self):
        plan = build_dry_run_plan(
            instruments=["EUR_USD"],
            granularities=["M15"],
            days=1,
            output_dir=Path("/tmp/x"),
            max_export_size_bytes=500 * 1024 * 1024,
            credentials_present=True,
        )
        self.assertIn("per_instrument_granularity", plan)

    def test_no_order_execution_imports_in_exporter(self):
        root = Path(__file__).resolve().parents[1]
        src = (root / "scripts" / "phase8l_alpha_export_research_data.py").read_text(encoding="utf-8")
        self.assertNotIn("import v20", src)
        self.assertNotIn("from v20", src)
        self.assertNotIn("oanda.order", src)
        self.assertNotIn("src.core.execution", src)

    @patch("scripts.phase8l_alpha_export_research_data._export_candles_single")
    def test_write_export_manifest_has_no_secret_fields(self, _ex):
        _ex.return_value = {
            "file": "phase8l_candles_EUR_USD_M15_14d.jsonl.gz",
            "path": "/tmp/x",
            "instrument": "EUR_USD",
            "granularity": "M15",
            "candle_count": 2,
            "compressed_size_bytes": 100,
            "sha256": "a" * 64,
            "dataset_start_utc": "2026-01-01T00:00:00Z",
            "dataset_end_utc": "2026-01-02T00:00:00Z",
        }
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            td_path = Path(td)
            old = os.environ.get("OANDA_API_KEY")
            os.environ["OANDA_API_KEY"] = "test-key-not-real"
            try:
                out = run_export(
                    days=14,
                    instruments=["EUR_USD"],
                    granularities=["M15"],
                    output_dir=td_path,
                    max_export_size_bytes=10 * 1024 * 1024,
                    dry_run_plan=False,
                    write_export=True,
                    max_context_rows=5,
                )
                self.assertTrue(out.get("ok"))
                man = json.loads((td_path / "phase8l_alpha_export_manifest.json").read_text(encoding="utf-8"))
                self.assertFalse(man.get("secret_fields_written"))
                self.assertFalse(man.get("order_or_execution_apis_called"))
                blob = (td_path / "phase8l_alpha_export_manifest.json").read_text(encoding="utf-8")
                self.assertNotIn("test-key-not-real", blob)
            finally:
                if old is None:
                    os.environ.pop("OANDA_API_KEY", None)
                else:
                    os.environ["OANDA_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
