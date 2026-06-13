import ast
import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.phase8l_news_calendar_diagnostics import run_diagnostics
from scripts.local_research.phase8l_news_calendar_fetch import (
    DOCUMENTED_PROVIDER_ENV_NAMES,
    resolve_finnhub_key,
    resolve_newsapi_key,
    resolve_trading_economics_key,
)


class TestPhase8LNewsCalendarDiagnostics(unittest.TestCase):
    def test_no_order_execution_imports_in_diagnostics(self):
        root = Path(__file__).resolve().parents[1]
        src = (root / "scripts" / "phase8l_news_calendar_diagnostics.py").read_text(encoding="utf-8")
        self.assertNotIn("import v20", src)
        self.assertNotIn("from v20", src)
        self.assertNotIn("oanda.order", src)
        self.assertNotIn("src.core.execution", src)

    def test_ast_no_forbidden_imports(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "scripts" / "phase8l_news_calendar_diagnostics.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = {"v20", "src.core.execution"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = (alias.name or "").split(".", 1)[0]
                    self.assertNotIn(base, bad, msg=f"unexpected import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertFalse(
                        node.module.startswith("v20"),
                        msg=f"unexpected from-import {node.module}",
                    )
                    self.assertFalse(
                        node.module.startswith("src.core.execution"),
                        msg=f"unexpected from-import {node.module}",
                    )

    def test_output_contains_no_secret_token_substring(self):
        secret = "sk_test_REPLACE_ME_fake_value_12345"  # fake fixture; REPLACE_ME marks it scanner-safe
        mock_json = {"articles": [{"publishedAt": "2026-04-20T12:00:00Z", "title": "x", "description": "", "url": ""}]}

        def fake_get(url, timeout=15):
            _ = url  # URL contains apiKey client-side; must not appear in diagnostic JSON output.
            r = MagicMock()
            r.status_code = 200
            if "newsapi.org" in url:
                r.json.return_value = mock_json
            elif "tradingeconomics.com" in url:
                r.json.return_value = []
            elif "finnhub.io" in url:
                r.json.return_value = {"economicCalendar": []}
            else:
                raise AssertionError(url)
            return r

        old: dict[str, str | None] = {}
        for k in list(os.environ.keys()):
            if "NEWS" in k or "FINNHUB" in k or "TRADING" in k or "TE_" in k:
                old[k] = os.environ.pop(k, None)
        try:
            os.environ["NEWS_API_KEY"] = secret
            with patch("scripts.phase8l_news_calendar_diagnostics.control_plane_news_probe", return_value={}):
                with patch("scripts.local_research.phase8l_news_calendar_fetch.requests.get", side_effect=fake_get):
                    out = run_diagnostics(
                        instrument="EUR_USD",
                        days=14,
                        start_utc="2026-04-17T00:15:00Z",
                        end_utc="2026-04-30T23:45:00Z",
                        max_rows=10,
                        repo_path="/opt/ai-quant",
                    )
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        blob = json.dumps(out)
        self.assertNotIn(secret, blob)
        self.assertFalse(out.get("secret_values_printed"))
        self.assertGreaterEqual(out["rows_by_provider"]["NewsAPI"], 1)

    def test_missing_key_classification(self):
        old: dict[str, str | None] = {}
        for k in list(os.environ.keys()):
            if "NEWS" in k or "FINNHUB" in k or "TRADING" in k or "TE_" in k:
                old[k] = os.environ.pop(k, None)
        try:
            with patch("scripts.phase8l_news_calendar_diagnostics.control_plane_news_probe", return_value={}):
                with patch("scripts.local_research.phase8l_news_calendar_fetch.requests.get") as mock_get:
                    mock_get.side_effect = AssertionError("HTTP must not be called without keys")
                    out = run_diagnostics(
                        instrument="EUR_USD",
                        days=14,
                        start_utc="2026-04-17T00:15:00Z",
                        end_utc="2026-04-30T23:45:00Z",
                        max_rows=10,
                        repo_path="/opt/ai-quant",
                    )
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.assertEqual(out["rows_by_provider"]["NewsAPI"], 0)
        self.assertIn("PROVIDER_KEYS_MISSING", out["classification"])

    def test_news_api_key_alias_precedence(self):
        old = os.environ.get("NEWSAPI_API_KEY"), os.environ.get("NEWS_API_KEY")
        try:
            os.environ["NEWSAPI_API_KEY"] = "primary"
            os.environ["NEWS_API_KEY"] = "secondary"
            k, name = resolve_newsapi_key()
            self.assertEqual(k, "primary")
            self.assertEqual(name, "NEWSAPI_API_KEY")
        finally:
            if old[0] is None:
                os.environ.pop("NEWSAPI_API_KEY", None)
            else:
                os.environ["NEWSAPI_API_KEY"] = old[0]  # type: ignore[assignment]
            if old[1] is None:
                os.environ.pop("NEWS_API_KEY", None)
            else:
                os.environ["NEWS_API_KEY"] = old[1]  # type: ignore[assignment]

    def test_news_api_key_falls_back_to_news_api_key(self):
        old_primary = os.environ.pop("NEWSAPI_API_KEY", None)
        old_newsapi = os.environ.pop("NEWSAPI_KEY", None)
        old_news = os.environ.get("NEWS_API_KEY")
        try:
            os.environ["NEWS_API_KEY"] = "from_news_api_key"
            k, name = resolve_newsapi_key()
            self.assertEqual(k, "from_news_api_key")
            self.assertEqual(name, "NEWS_API_KEY")
        finally:
            if old_primary is not None:
                os.environ["NEWSAPI_API_KEY"] = old_primary
            if old_newsapi is not None:
                os.environ["NEWSAPI_KEY"] = old_newsapi
            if old_news is None:
                os.environ.pop("NEWS_API_KEY", None)
            else:
                os.environ["NEWS_API_KEY"] = old_news

    def test_newsapi_csv_alias_precedence(self):
        keys = ("NEWSAPI_API_KEYS", "NEWSAPI_API_KEY", "NEWSAPI_KEY", "NEWS_API_KEY")
        saved = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            os.environ["NEWSAPI_API_KEYS"] = "first_key,second_key"
            os.environ["NEWSAPI_API_KEY"] = "single_key"
            key, name = resolve_newsapi_key()
            self.assertEqual(key, "first_key")
            self.assertEqual(name, "NEWSAPI_API_KEYS")
        finally:
            for k in keys:
                os.environ.pop(k, None)
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_finnhub_csv_alias_detection(self):
        keys = ("FINNHUB_API_KEYS", "FINNHUB_API_KEY", "FINNHUB_KEY")
        saved = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            os.environ["FINNHUB_API_KEYS"] = "first_finnhub,second_finnhub"
            key, name = resolve_finnhub_key()
            self.assertEqual(key, "first_finnhub")
            self.assertEqual(name, "FINNHUB_API_KEYS")
        finally:
            for k in keys:
                os.environ.pop(k, None)
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_documented_aliases_include_alpha_news_provider_names(self):
        for name in (
            "NEWSAPI_API_KEYS",
            "FINNHUB_API_KEYS",
            "MARKETAUX_API_KEYS",
            "TRADINGECONOMICS_API_KEYS",
        ):
            self.assertIn(name, DOCUMENTED_PROVIDER_ENV_NAMES)

    def test_trading_economics_alias(self):
        keys = (
            "TRADINGECONOMICS_API_KEYS",
            "TRADINGECONOMICS_KEY",
            "TRADING_ECONOMICS_KEY",
            "TE_API_KEY",
        )
        saved = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            os.environ["TRADINGECONOMICS_API_KEYS"] = "te_primary,te_secondary"
            os.environ["TRADING_ECONOMICS_KEY"] = "te_alias"
            k, name = resolve_trading_economics_key()
            self.assertEqual(k, "te_primary")
            self.assertEqual(name, "TRADINGECONOMICS_API_KEYS")
        finally:
            for k in keys:
                os.environ.pop(k, None)
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
