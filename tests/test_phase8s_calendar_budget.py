import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from scripts.local_research.calendar_budgeted_client import fetch_calendar_with_budget
from scripts.local_research.rapidapi_economic_calendar_client import fetch_tradingview_events
from scripts.phase8s_calendar_budget_guard import (
    ABSOLUTE_STOP_CALLS,
    BudgetDecision,
    append_ledger,
    request_fingerprint,
    write_usage_report,
)


class TestPhase8SCalendarBudget(unittest.TestCase):
    def test_cache_hit_does_not_invoke_inner(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            fp = request_fingerprint("p1", "2026-01-01", "2026-01-31", "US")
            cache_dir = root / "ARTIFACTS" / "performance" / "calendar_http_cache"
            cache_dir.mkdir(parents=True)
            cache_dir.joinpath(f"p1_{fp}.json").write_text(
                json.dumps({"rows": [{"id": "e1"}], "saved": True}),
                encoding="utf-8",
            )
            def _inner_must_not_run():
                raise AssertionError("inner must not run")

            rows, meta = fetch_calendar_with_budget(
                repo_root=root,
                provider="p1",
                date_from="2026-01-01",
                date_to="2026-01-31",
                countries="US",
                session_remaining_paid_calls=[5],
                inner=_inner_must_not_run,
            )
            self.assertTrue(meta.get("cache_hit"))
            self.assertEqual(rows, [{"id": "e1"}])

    def test_budget_blocked_skips_inner(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            calls = []

            def _inner():
                calls.append(1)
                return [{"x": 1}], {"http_status": 200}

            def _blocked(_repo):
                return BudgetDecision(False, "hard_stop_exceeded", ABSOLUTE_STOP_CALLS)

            with patch(
                "scripts.local_research.calendar_budgeted_client.evaluate_budget",
                side_effect=_blocked,
            ):
                rows, meta = fetch_calendar_with_budget(
                    repo_root=root,
                    provider="p1",
                    date_from="2026-02-01",
                    date_to="2026-02-28",
                    countries="US",
                    session_remaining_paid_calls=[5],
                    inner=_inner,
                )
            self.assertEqual(calls, [])
            self.assertEqual(rows, [])
            self.assertTrue(meta.get("budget_blocked"))

    def test_ledger_lines_contain_no_secret_literals(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            append_ledger(
                root,
                {
                    "event": "paid_calendar_call",
                    "provider": "rapidapi_economic_calendar",
                    "fingerprint": "abc123",
                    "http_status": 200,
                },
            )
            ledger = (
                root / "ARTIFACTS" / "performance" / "calendar_api_usage_ledger.jsonl"
            ).read_text(encoding="utf-8")
            lowered = ledger.lower()
            self.assertNotIn("rapidapi-key", lowered)
            self.assertNotIn("x-rapidapi-key", lowered)
            self.assertNotIn("secret", lowered)

    def test_write_usage_report_has_expected_keys(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            write_usage_report(root)
            p = root / "ARTIFACTS" / "performance" / "latest_calendar_api_usage_report.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            for key in (
                "calendar_calls_this_month",
                "calendar_budget_remaining",
                "calendar_cache_hit_rate",
                "next_paid_call_allowed",
            ):
                self.assertIn(key, data)

    @patch("scripts.local_research.rapidapi_economic_calendar_client.requests.get")
    def test_fetch_tradingview_events_params(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        fetch_tradingview_events(countries="US,GB", date_from="2026-04-01", date_to="2026-05-01", api_key="REPLACE_ME")
        mock_get.assert_called_once()
        _args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["countries"], "US,GB")
        self.assertEqual(kwargs["params"]["from"], "2026-04-01")
        self.assertEqual(kwargs["params"]["to"], "2026-05-01")


if __name__ == "__main__":
    unittest.main()
