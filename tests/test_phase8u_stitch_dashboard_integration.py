import unittest

from scripts.phase8u_build_stitch_dashboard_payload import build_payload
from scripts.phase8u_open_stitch_dashboard_preview import (
    BANNER_MAIN,
    BANNER_NOT_FALLBACK,
    build_preview_html,
)
from scripts.phase8u_validate_stitch_dashboard_integration import validate_payload, validate_stitch_snapshot


class TestPhase8UStitchDashboardIntegration(unittest.TestCase):
    def _dashboard_fixture(self):
        return {
            "generated_at_utc": "2026-05-03T12:00:00Z",
            "latest_research_runs": [
                {
                    "instrument": "EUR_USD",
                    "session_bucket": "NY_OPEN",
                    "granularity": "M15",
                    "promotion_label": "PROMOTE_REVIEW_CANDIDATE",
                    "replay_mode": "exact_strategy_replay",
                    "decision_reason": "",
                }
            ],
            "promotion_candidates": [
                {
                    "instrument": "EUR_USD",
                    "promotion_label": "PROMOTE_REVIEW_CANDIDATE",
                    "replay_mode": "exact_strategy_replay",
                }
            ],
            "continue_forward_candidates": [],
            "watch_only_candidates": [],
            "demoted_blocked_candidates": [],
            "fail_closed_rows": [],
            "proxy_rows": [],
            "result_rows_indexed": 1,
            "calendar_budget_remaining": 997,
            "calendar_calls_this_month": 3,
            "providers_working": ["rapidapi_economic_calendar"],
            "providers_blocked": [],
            "calendar_cache_hit_rate": 0.2,
            "last_calendar_api_call_utc": "2026-05-03T12:15:40Z",
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
            "stitch_mcp_contract_health": {"contract_version": "phase8t_v1"},
            "alpha_latest_pointers": {"latest_research_dashboard": "ARTIFACTS/performance/latest_research_dashboard.json"},
            "latest_phase8o_classification": "PASS_EXACT_REPLAY",
            "exact_strategy_replay": True,
            "news_reconstruction_available": True,
            "calendar_reconstruction_available": True,
        }

    def test_build_payload_enforces_separation_and_decision_reason(self):
        dashboard = self._dashboard_fixture()
        dashboard["promotion_candidates"].append(
            {
                "instrument": "EUR_USD",
                "promotion_label": "PROMOTE_REVIEW_CANDIDATE",
                "replay_mode": "best_available_proxy_reconstruction",
            }
        )
        payload = build_payload(dashboard, {"contract_version": "phase8t_v1"})
        self.assertEqual(len(payload["tables"]["promotion_candidates"]), 1)
        self.assertTrue(payload["tables"]["promotion_candidates"][0]["decision_reason"])

    def test_build_payload_includes_phase8x_from_dashboard(self):
        dashboard = self._dashboard_fixture()
        dashboard["phase8x_batch_progress_present"] = True
        dashboard["phase8x_batch_progress"] = {
            "pending": 3,
            "running": 0,
            "done": 7,
            "failed": 0,
            "total": 10,
            "percent_complete": 70.0,
            "current_job_id": None,
            "stop_reason": "RUNNING",
        }
        payload = build_payload(dashboard, {"contract_version": "phase8t_v1"})
        self.assertIsInstance(payload.get("phase8x_batch_progress"), dict)
        self.assertEqual(payload["summary_cards"].get("phase8x_pending"), 3)
        self.assertEqual(payload["summary_cards"].get("phase8x_percent_complete"), 70.0)

    def test_validate_payload_fails_when_promotion_contains_proxy(self):
        payload = {
            "ok": True,
            "generated_at_utc": "2026-05-03T12:00:00Z",
            "source": {},
            "contract_version": "phase8t_v1",
            "freshness": {"stale": False},
            "summary_cards": {},
            "tables": {
                "latest_runs": [],
                "promotion_candidates": [
                    {
                        "promotion_label": "PROMOTE_REVIEW_CANDIDATE",
                        "replay_mode": "best_available_proxy_reconstruction",
                        "decision_reason": "x",
                    }
                ],
                "continue_forward": [],
                "watch_only": [],
                "demoted_blocked": [],
                "fail_closed": [],
                "proxy_research": [],
            },
            "filters": {},
            "warnings": [],
            "safety": {
                "live_permission": False,
                "ny_live_enabled": False,
                "send_trade_unlock_changed": False,
                "execution_paths_changed": False,
            },
            "alpha_pointers": {},
            "provider_capability": {"providers_working": [], "providers_blocked": []},
            "calendar_budget": {"calendar_budget_remaining": 1, "calendar_calls_this_month": 2},
        }
        errors, _warnings = validate_payload(payload)
        self.assertIn("promotion_contains_proxy_row", errors)

    def test_validate_stitch_snapshot_flags_tournament_title(self):
        snap = {
            "target_project_id": "123",
            "projects": [{"name": "projects/123"}],
            "screens": [{"title": "Tournament Results"}],
        }
        errors, _warnings = validate_stitch_snapshot(snap)
        self.assertIn("stitch_screen_titles_contain_mock_or_tournament_text", errors)

    def test_build_preview_html_contains_banners_and_sections(self):
        dashboard = self._dashboard_fixture()
        payload = build_payload(dashboard, {"contract_version": "phase8t_v1"})
        html_out = build_preview_html(payload)
        self.assertIn(BANNER_MAIN, html_out)
        self.assertIn(BANNER_NOT_FALLBACK, html_out)
        self.assertIn("contract_version", html_out)
        self.assertIn("calendar_budget_remaining", html_out)
        self.assertIn("Promotion Candidates", html_out)
        self.assertIn("Proxy Research Rows", html_out)
        self.assertIn("Fail-Closed", html_out)
        self.assertNotIn("tournament", html_out.lower())

    def test_build_preview_html_blocks_without_tables(self):
        html_out = build_preview_html({"summary_cards": {}, "tables": None})
        self.assertIn("BLOCKED", html_out)
        self.assertIn(BANNER_MAIN, html_out)


if __name__ == "__main__":
    unittest.main()
