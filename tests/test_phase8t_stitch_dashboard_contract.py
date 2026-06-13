import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.phase8p_build_research_dashboard import build_dashboard
from scripts.phase8p_index_research_results import build_index
from scripts.phase8t_validate_stitch_dashboard_contract import (
    REQUIRED_DASHBOARD_FIELDS,
    build_stitch_contract_document,
    compute_freshness_seconds,
    validate_dashboard_payload,
)
from tests.test_phase8p_research_dashboard import _write_phase8m_import, _write_phase8o_import


class TestPhase8TStitchDashboardContract(unittest.TestCase):
    def test_required_fields_list_matches_runtime_dashboard_with_repo_root(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            _write_phase8o_import(repo)
            perf = repo / "ARTIFACTS/performance"
            perf.mkdir(parents=True, exist_ok=True)
            (perf / "latest_calendar_api_usage_report.json").write_text(
                json.dumps(
                    {
                        "calendar_calls_this_month": 1,
                        "calendar_budget_remaining": 999,
                        "calendar_cache_hit_rate": 0.0,
                        "last_calendar_api_call_utc": "2026-05-01T12:00:00Z",
                        "calendar_budget_monthly_cap": 1000,
                        "next_paid_call_allowed": True,
                        "budget_decision_reason": "within_budget",
                    }
                ),
                encoding="utf-8",
            )
            (perf / "latest_phase8r_provider_capability_report.json").write_text(
                json.dumps(
                    {
                        "working_news_providers": [],
                        "working_calendar_providers": [],
                        "working_macro_providers": [],
                        "probe_news": [],
                        "probe_calendar": [],
                    }
                ),
                encoding="utf-8",
            )
            index = build_index(repo)
            dash = build_dashboard(index, repo_root=repo)
            for key in REQUIRED_DASHBOARD_FIELDS:
                self.assertIn(key, dash, msg=f"missing {key}")

    def test_validator_fails_if_proxy_in_promotion_candidates(self):
        bad = {
            "generated_at_utc": "2026-05-01T00:00:00Z",
            "dashboard_freshness_seconds": 0,
            "result_rows_indexed": 1,
            "promotion_candidates": [{"replay_mode": "best_available_proxy_reconstruction", "promotion_label": "PROMOTE_REVIEW_CANDIDATE"}],
            "proxy_rows": [],
            "fail_closed_rows": [],
            "providers_working": [],
            "providers_blocked": [],
            "calendar_calls_this_month": 0,
            "calendar_budget_remaining": 100,
            "calendar_cache_hit_rate": 0.0,
            "latest_phase8o_classification": None,
            "exact_strategy_replay": False,
            "news_reconstruction_available": False,
            "calendar_reconstruction_available": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        }
        err, _warn = validate_dashboard_payload(bad)
        self.assertTrue(any("invalid_replay_mode" in e for e in err))

    def test_contract_builder_emits_json(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            doc = build_stitch_contract_document(root)
            self.assertEqual(doc.get("phase"), "Phase 8T")
            self.assertIn("required_top_level_fields", doc.get("primary_payload") or {})

    def test_freshness_seconds_non_negative(self):
        d = {"generated_at_utc": "2026-05-01T00:00:00Z"}
        self.assertGreaterEqual(compute_freshness_seconds(d), 0)

    def test_phase8p_promotion_candidates_exclude_continue_proxy_only_promote_or_empty(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            _write_phase8o_import(repo)
            perf = repo / "ARTIFACTS/performance"
            perf.mkdir(parents=True, exist_ok=True)
            (perf / "latest_calendar_api_usage_report.json").write_text(
                json.dumps(
                    {
                        "calendar_calls_this_month": 0,
                        "calendar_budget_remaining": 1000,
                        "calendar_cache_hit_rate": 0.0,
                        "calendar_budget_monthly_cap": 1000,
                        "next_paid_call_allowed": True,
                        "budget_decision_reason": "within_budget",
                    }
                ),
                encoding="utf-8",
            )
            (perf / "latest_phase8r_provider_capability_report.json").write_text(
                json.dumps(
                    {
                        "working_news_providers": [],
                        "working_calendar_providers": [],
                        "working_macro_providers": [],
                        "probe_news": [],
                        "probe_calendar": [],
                    }
                ),
                encoding="utf-8",
            )
            index = build_index(repo)
            dash = build_dashboard(index, repo_root=repo)
            for row in dash.get("promotion_candidates") or []:
                self.assertNotEqual(
                    str(row.get("replay_mode") or ""),
                    "best_available_proxy_reconstruction",
                )
            self.assertTrue(len(dash.get("continue_forward_candidates") or []) >= 1)


if __name__ == "__main__":
    unittest.main()
