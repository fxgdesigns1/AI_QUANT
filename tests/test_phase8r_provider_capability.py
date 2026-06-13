import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.phase8r_provider_capability import (
    PHASE8R_PROVIDER_ENV_NAMES,
    load_env_file,
    run_capability,
)


class TestPhase8RProviderCapability(unittest.TestCase):
    def test_phase8r_env_name_list_matches_contract(self):
        expected = (
            "NEWSAPI_API_KEYS",
            "NEWSAPI_API_KEY",
            "FINNHUB_API_KEYS",
            "FINNHUB_API_KEY",
            "TRADINGECONOMICS_API_KEYS",
            "TRADINGECONOMICS_API_KEY",
            "MARKETAUX_API_KEYS",
            "MARKETAUX_API_KEY",
            "POLYGON_API_KEYS",
            "ALPHAVANTAGE_API_KEYS",
            "FRED_API_KEYS",
            "FMP_API_KEYS",
        )
        self.assertEqual(tuple(PHASE8R_PROVIDER_ENV_NAMES), expected)

    def test_load_env_file_no_echo(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".env", encoding="utf-8") as tmp:
            tmp.write("NEWSAPI_API_KEY=secret_value_must_not_appear_in_report\n")
            tmp.write("# comment\n")
            path = Path(tmp.name)
        try:
            n = load_env_file(path, override=True)
            self.assertGreaterEqual(n, 1)
            self.assertEqual(os.environ.get("NEWSAPI_API_KEY"), "secret_value_must_not_appear_in_report")
        finally:
            os.environ.pop("NEWSAPI_API_KEY", None)
            path.unlink(missing_ok=True)

    @patch("scripts.phase8r_provider_capability.requests.get")
    @patch("scripts.phase8r_provider_capability.fetch_newsapi_forex_rows")
    @patch("scripts.phase8r_provider_capability.fetch_tradingeconomics_calendar_rows")
    def test_run_capability_pass_when_news_and_calendar_rows(self, mock_te, mock_news, mock_http):
        def _deny_live_http(*args, **kwargs):
            m = MagicMock()
            m.status_code = 401
            m.json.return_value = {}
            return m

        mock_http.side_effect = _deny_live_http
        mock_news.return_value = ([{"source": "newsapi"}], {"http_status": 200, "parser_ok": True})
        mock_te.return_value = ([{"source": "te"}], {"http_status": 200, "parser_ok": True})
        old = {k: os.environ.pop(k, None) for k in ("NEWSAPI_API_KEY", "TRADINGECONOMICS_API_KEY")}
        try:
            os.environ["NEWSAPI_API_KEY"] = "k1"
            os.environ["TRADINGECONOMICS_API_KEY"] = "k2"
            with tempfile.TemporaryDirectory() as td:
                repo_root = Path(td)
                report, code = run_capability(
                    instrument="EUR_USD",
                    lookback_days=14,
                    max_probe_rows=5,
                    env_file_lines_applied=0,
                    repo_root=repo_root,
                    max_calendar_paid_calls=50,
                    provider_filter="legacy_calendar",
                    rapidapi_countries="US,GB,EU",
                )
            self.assertEqual(code, 0)
            self.assertEqual(report["classification"], "PASS_PROVIDER_CAPABILITY")
            self.assertIn("newsapi", report["working_news_providers"])
            blob = json.dumps(report)
            self.assertNotIn("k1", blob)
            self.assertNotIn("k2", blob)
            self.assertFalse(report.get("secrets_exposed"))
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

    def test_main_writes_report_without_secret_literal(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rep, code = run_capability(
                instrument="EUR_USD",
                lookback_days=1,
                max_probe_rows=1,
                env_file_lines_applied=0,
                repo_root=td_path,
                max_calendar_paid_calls=5,
                provider_filter="legacy_calendar",
                rapidapi_countries="US,GB,EU",
            )
            out = td_path / "out.json"
            out.write_text(json.dumps(rep), encoding="utf-8")
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("classification", data)


if __name__ == "__main__":
    unittest.main()
