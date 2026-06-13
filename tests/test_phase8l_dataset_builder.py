import gzip
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.local_research.phase8k_replay_lib import (
    candle_in_session_window,
    parse_session_window_utc,
)
from scripts.local_research.phase8l_dataset_builder import build_dataset_from_alpha_export

UTC = timezone.utc


def _write_gz_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as gz:
        for r in rows:
            gz.write(json.dumps(r) + "\n")


class TestPhase8LDatasetBuilder(unittest.TestCase):
    def test_session_window_utc_labeling(self):
        lo, hi = parse_session_window_utc("13:30-16:00")
        t = datetime(2026, 4, 17, 14, 0, tzinfo=UTC)
        self.assertTrue(candle_in_session_window(t, start_minutes=lo, end_minutes=hi))
        t2 = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
        self.assertFalse(candle_in_session_window(t2, start_minutes=lo, end_minutes=hi))

    def test_indicators_deterministic(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            td_path = Path(td)
            t0 = datetime(2026, 1, 1, 13, 30, tzinfo=UTC)
            candles = []
            p = 1.10
            for i in range(60):
                candles.append(
                    {
                        "time": (t0 + timedelta(minutes=15 * i)).isoformat().replace("+00:00", "Z"),
                        "o": p,
                        "h": p + 0.001,
                        "l": p - 0.001,
                        "c": p + 0.0002,
                        "volume": 100,
                    }
                )
                p += 0.0001
            _write_gz_jsonl(td_path / "phase8l_candles_EUR_USD_M15_14d.jsonl.gz", candles)
            _write_gz_jsonl(
                td_path / "phase8l_news_context_14d.jsonl.gz",
                [{"placeholder": True, "reason": "test"}],
            )
            _write_gz_jsonl(
                td_path / "phase8l_calendar_context_14d.jsonl.gz",
                [{"placeholder": True, "reason": "test"}],
            )
            manifest = {
                "days_requested": 14,
                "instruments": ["EUR_USD"],
                "granularities": ["M15"],
                "news_reconstruction_available": False,
                "calendar_reconstruction_available": False,
            }
            (td_path / "phase8l_alpha_export_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            df1, _ = build_dataset_from_alpha_export(export_dir=td_path, primary_granularity="M15")
            df2, _ = build_dataset_from_alpha_export(export_dir=td_path, primary_granularity="M15")
            pd.testing.assert_frame_equal(df1[["rsi_14", "ema_20"]], df2[["rsi_14", "ema_20"]])

    def test_missing_news_calendar_graceful(self):
        with TemporaryDirectory() as td:
            td_path = Path(td)
            t0 = datetime(2026, 1, 3, 13, 30, tzinfo=UTC)
            candles = [
                {
                    "time": (t0 + timedelta(minutes=15 * i)).isoformat().replace("+00:00", "Z"),
                    "o": 1.1,
                    "h": 1.101,
                    "l": 1.099,
                    "c": 1.1005,
                    "volume": 10,
                }
                for i in range(20)
            ]
            _write_gz_jsonl(td_path / "phase8l_candles_EUR_USD_M15_14d.jsonl.gz", candles)
            _write_gz_jsonl(td_path / "phase8l_news_context_14d.jsonl.gz", [])
            _write_gz_jsonl(td_path / "phase8l_calendar_context_14d.jsonl.gz", [])
            (td_path / "phase8l_alpha_export_manifest.json").write_text(
                json.dumps(
                    {
                        "days_requested": 14,
                        "instruments": ["EUR_USD"],
                        "granularities": ["M15"],
                        "news_reconstruction_available": False,
                        "calendar_reconstruction_available": False,
                    }
                ),
                encoding="utf-8",
            )
            df, meta = build_dataset_from_alpha_export(export_dir=td_path)
            self.assertFalse(meta["news_reconstruction_available"])
            self.assertIn("session_label", df.columns)


if __name__ == "__main__":
    unittest.main()
