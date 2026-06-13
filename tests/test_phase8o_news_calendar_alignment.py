import gzip
import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import requests

from scripts.phase8o_alpha_export_exact_replay_data import provider_diagnostics
from scripts.phase8o_build_exact_replay_dataset import build_dataset_from_phase8o_export

UTC = timezone.utc


def _write_gz_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as gz:
        for row in rows:
            gz.write(json.dumps(row) + "\n")


class TestPhase8ONewsCalendarAlignment(unittest.TestCase):
    def test_provider_diagnostics_report_presence_without_secret_values(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict("os.environ", {"NEWSAPI_API_KEY": "super-secret-value"}, clear=True):
                with patch("scripts.local_research.phase8l_news_calendar_fetch.requests.get") as mock_get:
                    mock_get.side_effect = requests.exceptions.ConnectionError("network disabled in unit test")
                    news_rows, calendar_rows, diag = provider_diagnostics(
                        start_day="2026-01-01",
                        end_day="2026-01-02",
                        max_rows=10,
                        repo_root=root,
                        probe_control_plane=False,
                    )
        self.assertEqual(news_rows, [])
        self.assertEqual(calendar_rows, [])
        dumped = json.dumps(diag)
        self.assertNotIn("super-secret-value", dumped)
        self.assertTrue(diag["provider_env_presence_without_values"]["NewsAPI"]["NEWSAPI_API_KEY"])

    def test_control_plane_current_news_classifies_historical_gap(self):
        def fake_provider_get(url, timeout=15):
            _ = timeout
            response = requests.Response()
            response.status_code = 200
            if "newsapi.org" in url:
                response._content = b'{"articles":[]}'
            elif "tradingeconomics.com" in url:
                response._content = b"[]"
            elif "finnhub.io" in url:
                response._content = b'{"economicCalendar":[]}'
            else:
                raise AssertionError(url)
            return response

        control_probe = {
            "status_endpoint_ok": True,
            "provider_status_endpoint_ok": True,
            "assess_news_count": 10,
            "news_count": 10,
            "providers_used": ["marketaux", "polygon", "newsapi"],
            "source_mode": "snapshot",
        }
        with TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict("os.environ", {"NEWSAPI_API_KEYS": "secret-one,secret-two"}, clear=True):
                with patch("scripts.local_research.phase8l_news_calendar_fetch.requests.get", side_effect=fake_provider_get):
                    with patch(
                        "scripts.phase8o_alpha_export_exact_replay_data.control_plane_news_probe",
                        return_value=control_probe,
                    ):
                        news_rows, calendar_rows, diag = provider_diagnostics(
                            start_day="2026-01-01",
                            end_day="2026-01-02",
                            max_rows=10,
                            repo_root=root,
                        )
        self.assertEqual(news_rows, [])
        self.assertEqual(calendar_rows, [])
        self.assertEqual(
            diag["news_unavailable_classification"],
            "PROVIDER_CURRENT_NEWS_AVAILABLE_HISTORICAL_RECONSTRUCTION_UNAVAILABLE",
        )
        dumped = json.dumps(diag)
        self.assertNotIn("secret-one", dumped)
        self.assertTrue(diag["documented_provider_env_presence_without_values"]["NEWSAPI_API_KEYS"])

    def test_utc_events_align_to_candles_and_embargo_windows_apply(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            t0 = datetime(2026, 1, 5, 13, 30, tzinfo=UTC)
            candles = []
            p = 1.1
            for i in range(12):
                candles.append(
                    {
                        "time": (t0 + timedelta(minutes=15 * i)).isoformat().replace("+00:00", "Z"),
                        "o": p,
                        "h": p + 0.001,
                        "l": p - 0.001,
                        "c": p + 0.0001,
                        "volume": 100,
                    }
                )
                p += 0.0001
            _write_gz_jsonl(root / "phase8o_candles_EUR_USD_M15_90d.jsonl.gz", candles)
            _write_gz_jsonl(
                root / "phase8o_news_context_90d.jsonl.gz",
                [{"published_at": (t0 + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"), "source": "fixture"}],
            )
            _write_gz_jsonl(
                root / "phase8o_calendar_context_90d.jsonl.gz",
                [{"time": (t0 + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"), "impact": "high"}],
            )
            (root / "phase8o_alpha_export_manifest.json").write_text(
                json.dumps(
                    {
                        "days_requested": 90,
                        "instruments": ["EUR_USD"],
                        "granularities": ["M15"],
                        "news_reconstruction_available": True,
                        "calendar_reconstruction_available": True,
                        "news_rows_count": 1,
                        "calendar_rows_count": 1,
                    }
                ),
                encoding="utf-8",
            )
            df, meta = build_dataset_from_phase8o_export(export_dir=root, primary_granularity="M15")
            self.assertTrue(meta["news_reconstruction_available"])
            self.assertTrue(meta["calendar_reconstruction_available"])
            self.assertGreater(int(df["news_embargo_adjacent"].sum()), 0)
            self.assertGreater(int(df["calendar_high_impact_adjacent"].sum()), 0)
            self.assertGreater(meta["events_aligned_to_candles"], 0)

    def test_missing_news_calendar_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "phase8o_alpha_export_manifest.json").write_text(
                json.dumps(
                    {
                        "days_requested": 90,
                        "instruments": ["EUR_USD"],
                        "granularities": ["M15"],
                        "news_reconstruction_available": False,
                        "calendar_reconstruction_available": False,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "NEWS_CALENDAR"):
                build_dataset_from_phase8o_export(export_dir=root, primary_granularity="M15")


class TestPhase8OAlphaExporterImports(unittest.TestCase):
    """ALPHA runs `python scripts/phase8o_alpha_export_exact_replay_data.py` with cwd = repo root."""

    def test_exporter_help_imports_full_dependency_chain(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "phase8o_alpha_export_exact_replay_data.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
