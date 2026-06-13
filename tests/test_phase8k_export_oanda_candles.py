import ast
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.local_research.oanda_mid_historical_fetch import parse_time_iso_utc
from scripts.phase8k_export_oanda_candles_for_5950x import (
    build_dry_run_plan,
    export_candles_jsonl_gz,
    manifest_path_for_jsonl_gz,
    preflight_refuses,
)


class TestExportScriptNoExecutionImports(unittest.TestCase):
    def test_ast_safe_imports(self):
        root = Path(__file__).resolve().parents[1]
        src = (root / "scripts" / "phase8k_export_oanda_candles_for_5950x.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = (node.module or "").lower()
                for bad in ("src.", "order_manager", "execution", "broker", "oanda.order"):
                    if bad in mod or mod.startswith("src"):
                        self.fail(f"disallowed import_from:{node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in ("src", "v20", "ib_insync"):
                        self.fail(f"disallowed import:{alias.name}")


class TestDryRunPlan(unittest.TestCase):
    def test_build_dry_run_plan_fields(self):
        p = build_dry_run_plan(
            instrument="EUR_USD",
            granularity="M15",
            lookback_days=180,
            output=Path("/tmp/phase8k_EUR_USD_M15.jsonl.gz"),
            max_export_size_bytes=25 * 1024 * 1024,
            credentials_present=False,
        )
        self.assertEqual(p["instrument"], "EUR_USD")
        self.assertIn("expected_candle_count_approx", p)
        self.assertIn("estimated_compressed_bytes_heuristic", p)
        self.assertIn("preflight_compressed_estimate_fits", p)
        self.assertTrue(str(p["output_manifest"]).endswith(".manifest.json"))


class TestManifestPath(unittest.TestCase):
    def test_manifest_path_for_jsonl_gz(self):
        self.assertEqual(
            manifest_path_for_jsonl_gz(Path("/tmp/phase8k_EUR_USD_M15_180d.jsonl.gz")).name,
            "phase8k_EUR_USD_M15_180d.manifest.json",
        )


class TestCompressedSizePreflight(unittest.TestCase):
    def test_extreme_lookback_preflight_refused(self):
        refuse, plan = preflight_refuses(
            lookback_days=80000,
            granularity="M1",
            max_export_size_bytes=25 * 1024 * 1024,
        )
        self.assertTrue(refuse)
        self.assertTrue(plan.get("would_refuse_preflight"))


class TestExportWritesManifest(unittest.TestCase):
    @patch("scripts.phase8k_export_oanda_candles_for_5950x.fetch_oanda_mid_candles_range")
    def test_export_manifest_secret_flag(self, mock_fetch):
        import tempfile

        mock_fetch.return_value = [
            {
                "time": "2026-01-01T12:00:00.000000000Z",
                "complete": True,
                "volume": 1,
                "o": 1.0,
                "h": 1.01,
                "l": 0.99,
                "c": 1.0,
            },
            {
                "time": "2026-01-01T12:15:00.000000000Z",
                "complete": True,
                "volume": 2,
                "o": 1.0,
                "h": 1.02,
                "l": 1.0,
                "c": 1.01,
            },
        ]
        old = os.environ.get("OANDA_API_KEY")
        os.environ["OANDA_API_KEY"] = "test-key-not-a-real-secret"
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "e.jsonl.gz"
                res = export_candles_jsonl_gz(
                    instrument="EUR_USD",
                    granularity="M15",
                    lookback_days=1,
                    output=out,
                    max_export_size_bytes=25 * 1024 * 1024,
                    dry_run_plan=False,
                )
                self.assertTrue(res.get("ok"))
                man = Path(res["manifest"])
                self.assertTrue(man.is_file())
                data = json.loads(man.read_text(encoding="utf-8"))
                self.assertIs(data.get("secret_fields_written"), False)
                self.assertEqual(data.get("candle_count"), 2)
                self.assertIn("sha256", data)
                self.assertEqual(data.get("compressed_size_bytes"), out.stat().st_size)
        finally:
            if old is None:
                os.environ.pop("OANDA_API_KEY", None)
            else:
                os.environ["OANDA_API_KEY"] = old


class TestActualSizeRefused(unittest.TestCase):
    @patch("scripts.phase8k_export_oanda_candles_for_5950x.fetch_oanda_mid_candles_range")
    def test_oversize_gzip_removed(self, mock_fetch):
        import tempfile

        big = "x" * 12000
        rows = [
            {
                "time": f"2026-01-{1 + (i % 28):02d}T12:00:00.000000000Z",
                "complete": True,
                "volume": 1,
                "o": 1.0,
                "h": 1.0,
                "l": 1.0,
                "c": 1.0,
                "pad": big,
            }
            for i in range(400)
        ]
        mock_fetch.return_value = rows
        old = os.environ.get("OANDA_API_KEY")
        os.environ["OANDA_API_KEY"] = "test-key-not-a-real-secret"
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "big.jsonl.gz"
                with self.assertRaises(RuntimeError) as ctx:
                    export_candles_jsonl_gz(
                        instrument="EUR_USD",
                        granularity="M15",
                        lookback_days=1,
                        output=out,
                        max_export_size_bytes=5000,
                        dry_run_plan=False,
                    )
                self.assertIn("EXPORT_SIZE_REFUSED", str(ctx.exception))
                self.assertFalse(out.exists())
        finally:
            if old is None:
                os.environ.pop("OANDA_API_KEY", None)
            else:
                os.environ["OANDA_API_KEY"] = old


class TestOandaParseNanosecondTimestamps(unittest.TestCase):
    def test_parse_time_iso_utc_clamps_oanda_fraction(self):
        dt = parse_time_iso_utc("2026-04-17T00:00:00.123456789Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 4)
        self.assertEqual(dt.day, 17)
        self.assertEqual(dt.microsecond, 123456)


if __name__ == "__main__":
    unittest.main()
