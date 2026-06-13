import ast
import gzip
import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.local_research.phase8k_replay_lib import (
    aggregate_month_by_month,
    build_daily_orb_proxy_trades,
    candle_in_session_window,
    classify_replay_from_handoff_pack,
    drawdown_proxy_r,
    expectancy_r,
    filter_candles_session_window,
    max_loss_streak,
    parse_session_window_utc,
    profit_factor_r,
    simulate_trade_r,
)
from scripts.phase8k_local_ny_eurusd_replay import run_pipeline

UTC = timezone.utc


class TestReplayModeClassification(unittest.TestCase):
    def test_missing_inventory_is_proxy(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pack"
            p.mkdir()
            (p / "manifest.json").write_text("{}", encoding="utf-8")
            ok, mode, notes, cnt = classify_replay_from_handoff_pack(
                p, instrument="EUR_USD", session_bucket_substr="NY_OPEN_SECONDARY"
            )
            self.assertFalse(ok)
            self.assertEqual(mode, "best_available_proxy_reconstruction")
            self.assertIn("missing_inventory", notes)
            self.assertEqual(cnt, 0)

    def test_inventory_exact_fields(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pack"
            inv = (
                p / "ARTIFACTS" / "performance" / "latest_phase8h_archived_candidate_inventory.json"
            )
            inv.parent.mkdir(parents=True)
            inv.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "instrument": "EUR_USD",
                                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                                "entry_time_utc": "2026-01-01T14:00:00Z",
                                "entry_price": 1.1,
                                "stop_loss": 1.09,
                                "take_profit": 1.12,
                                "direction": "BUY",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            ok, mode, notes, cnt = classify_replay_from_handoff_pack(
                p, instrument="EUR_USD", session_bucket_substr="NY_OPEN_SECONDARY"
            )
            self.assertTrue(ok)
            self.assertEqual(mode, "exact_replay_possible")
            self.assertEqual(cnt, 1)

    def test_inventory_partial_fields_blocked(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pack"
            inv = (
                p / "ARTIFACTS" / "performance" / "latest_phase8h_archived_candidate_inventory.json"
            )
            inv.parent.mkdir(parents=True)
            inv.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "instrument": "EUR_USD",
                                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                                "entry_time_utc": "2026-01-01T14:00:00Z",
                                "entry_price": 1.1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            ok, mode, _, cnt = classify_replay_from_handoff_pack(
                p, instrument="EUR_USD", session_bucket_substr="NY_OPEN_SECONDARY"
            )
            self.assertFalse(ok)
            self.assertEqual(cnt, 1)
            self.assertEqual(mode, "best_available_proxy_reconstruction")


class TestSessionWindow(unittest.TestCase):
    def test_parse_window(self):
        a, b = parse_session_window_utc("13:30-16:00")
        self.assertEqual(a, 13 * 60 + 30)
        self.assertEqual(b, 16 * 60)

    def test_candle_in_window(self):
        sm, em = parse_session_window_utc("13:30-16:00")
        t = datetime(2026, 5, 1, 14, 0, tzinfo=UTC)
        self.assertTrue(candle_in_session_window(t, start_minutes=sm, end_minutes=em))
        t2 = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        self.assertFalse(candle_in_session_window(t2, start_minutes=sm, end_minutes=em))

    def test_filter_candles(self):
        sm, em = parse_session_window_utc("13:30-16:00")
        candles = [
            {"time": "2026-05-01T12:00:00.000000000Z"},
            {"time": "2026-05-01T14:00:00.000000000Z"},
        ]
        f = filter_candles_session_window(candles, start_minutes=sm, end_minutes=em)
        self.assertEqual(len(f), 1)


class TestRMultiple(unittest.TestCase):
    def test_long_tp_first_bar(self):
        bars = [{"h": 1.12, "l": 1.095, "c": 1.11}]
        o, ex, r = simulate_trade_r(
            side="BUY",
            entry=1.1,
            stop_loss=1.09,
            take_profit=1.12,
            bars_after_entry=bars,
        )
        self.assertEqual(o, "win")
        self.assertGreater(r, 0)

    def test_same_bar_sl_priority(self):
        bars = [{"h": 1.15, "l": 1.08, "c": 1.09}]
        o, _, r = simulate_trade_r(
            side="BUY",
            entry=1.1,
            stop_loss=1.09,
            take_profit=1.2,
            bars_after_entry=bars,
        )
        self.assertEqual(o, "loss")
        self.assertEqual(r, -1.0)


class TestStreakDrawdownMonth(unittest.TestCase):
    def test_max_loss_streak(self):
        self.assertEqual(max_loss_streak(["win", "loss", "loss", "loss", "win"]), 3)

    def test_drawdown_proxy(self):
        dd = drawdown_proxy_r([1.0, 1.0, -3.0, 1.0])
        self.assertLess(dd, 0)

    def test_expectancy_and_pf(self):
        rs = [1.0, -1.0, 1.0, -1.0, 0.5]
        self.assertAlmostEqual(expectancy_r(rs), 0.1)
        self.assertGreater(profit_factor_r(rs), 1.0)

    def test_monthly(self):
        trades = [
            {"entry_time_utc": "2026-01-15T14:00:00Z", "r_multiple": 1.0},
            {"entry_time_utc": "2026-02-10T14:00:00Z", "r_multiple": -1.0},
        ]
        m = aggregate_month_by_month(trades)
        self.assertEqual(len(m), 2)


class TestCandlesJsonlGzReplay(unittest.TestCase):
    def test_pipeline_reads_gzip_jsonl(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / "pack"
            pack.mkdir()
            (pack / "manifest.json").write_text("{}", encoding="utf-8")
            gz_path = root / "candles.jsonl.gz"
            rows = []
            base = datetime(2026, 3, 1, tzinfo=UTC)
            for d in range(8):
                day = base + timedelta(days=d)
                for hh, mm, cl in ((13, 30, 1.0), (13, 45, 1.01), (14, 0, 1.02)):
                    t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=UTC)
                    rows.append(
                        {
                            "time": t.isoformat().replace("+00:00", "Z"),
                            "o": cl - 0.001,
                            "h": cl + 0.002,
                            "l": cl - 0.002,
                            "c": cl,
                            "complete": True,
                            "volume": 1,
                        }
                    )
            with gzip.open(gz_path, "wt", encoding="utf-8") as gz:
                for r in rows:
                    gz.write(json.dumps(r) + "\n")
            outd = root / "out"
            res = run_pipeline(
                input_pack=pack,
                output_dir=outd,
                instrument="EUR_USD",
                session_window_utc="13:30-16:00",
                lookback_days=30,
                granularity="M15",
                dry_run_plan=False,
                write_result_pack=False,
                fixtures_candles_json=None,
                candles_jsonl_gz=gz_path,
                spread_pips=0.0,
                slippage_pips=0.0,
            )
            self.assertGreater(res["trades_count"], 0)
            self.assertEqual(res["summary"]["data_source"], "alpha_export_jsonl_gz")
            self.assertFalse(res["summary"]["live_permission"])


class TestCliMutualExclusion(unittest.TestCase):
    def test_rejects_fixture_and_gz_together(self):
        import tempfile

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pack"
            p.mkdir()
            (p / "manifest.json").write_text("{}", encoding="utf-8")
            fx = Path(td) / "a.json"
            fx.write_text("[]")
            gz = Path(td) / "b.jsonl.gz"
            gz.write_bytes(gzip.compress(b"{}\n"))
            cmd = [
                sys.executable,
                str(root / "scripts" / "phase8k_local_ny_eurusd_replay.py"),
                "--input-pack",
                str(p),
                "--fixtures-candles-json",
                str(fx),
                "--candles-jsonl-gz",
                str(gz),
            ]
            r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 1)
            self.assertIn("only one of", r.stdout)


class TestOutputSafetyFlags(unittest.TestCase):
    def test_pipeline_summary_flags(self):
        import tempfile

        candles = []
        d0 = datetime(2026, 4, 1, tzinfo=UTC)
        for day in range(5):
            for hm in ((13, 30), (13, 45), (14, 0)):
                t = datetime(d0.year, d0.month, d0.day + day, hm[0], hm[1], tzinfo=UTC)
                candles.append(
                    {
                        "time": t.isoformat().replace("+00:00", "Z"),
                        "o": 1.0,
                        "h": 1.002,
                        "l": 0.998,
                        "c": 1.001,
                        "volume": 1,
                        "complete": True,
                    }
                )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / "pack"
            pack.mkdir()
            (pack / "manifest.json").write_text('{"classification":"RESEARCH_ONLY"}', encoding="utf-8")
            fx = root / "candles.json"
            fx.write_text(json.dumps(candles), encoding="utf-8")
            outd = root / "out"
            res = run_pipeline(
                input_pack=pack,
                output_dir=outd,
                instrument="EUR_USD",
                session_window_utc="13:30-16:00",
                lookback_days=7,
                granularity="M15",
                dry_run_plan=False,
                write_result_pack=False,
                fixtures_candles_json=fx,
                candles_jsonl_gz=None,
                spread_pips=0.0,
                slippage_pips=0.0,
            )
            s = res["summary"]
            self.assertTrue(s["paper_review_only"])
            self.assertFalse(s["live_permission"])
            self.assertFalse(s["ny_live_enabled"])
            self.assertFalse(s["send_trade_unlock_changed"])
            self.assertFalse(s["execution_paths_changed"])


class TestNoBrokerExecutionImports(unittest.TestCase):
    def test_phase8k_ast_imports_are_safe(self):
        root = Path(__file__).resolve().parents[1]
        src = (root / "scripts" / "phase8k_local_ny_eurusd_replay.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        banned_prefixes = (
            "src.",
            "oanda.order",
            "execution",
            "order_manager",
            "broker",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                ml = mod.lower()
                for b in banned_prefixes:
                    if ml.startswith(b) or b in ml:
                        self.fail(f"disallowed_import_from:{mod}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    n = alias.name.split(".")[0].lower()
                    if n in ("oandapy", "v20", "ib_insync"):
                        self.fail(f"disallowed_import:{alias.name}")


class TestOrbProxySmoke(unittest.TestCase):
    def test_orb_produces_trades(self):
        candles = []
        base = datetime(2026, 3, 1, tzinfo=UTC)
        for d in range(10):
            day = base + timedelta(days=d)
            seq = [
                (13, 30, 1.0, 1.01, 0.99, 1.005),
                (13, 45, 1.005, 1.02, 1.0, 1.015),
                (14, 0, 1.015, 1.03, 1.01, 1.025),
            ]
            for hh, mm, o, h, l, c in seq:
                t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=UTC)
                candles.append(
                    {
                        "time": t.isoformat().replace("+00:00", "Z"),
                        "o": o,
                        "h": h,
                        "l": l,
                        "c": c,
                        "complete": True,
                        "volume": 1,
                    }
                )
        sm, em = parse_session_window_utc("13:30-16:00")
        trades = build_daily_orb_proxy_trades(candles, session_start_minutes=sm, session_end_minutes=em)
        self.assertGreater(len(trades), 0)


if __name__ == "__main__":
    unittest.main()
