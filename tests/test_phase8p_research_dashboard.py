import json
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.phase8p_build_research_dashboard import build_dashboard, render_html
from scripts.phase8p_index_research_results import build_index, write_index
from scripts.phase8p_retention_cleanup import cleanup
from scripts.phase8p_score_and_label_results import (
    BLOCK,
    CONTINUE,
    DEMOTE,
    FAIL_CLOSED,
    PROMOTE,
    WATCH,
    score_row,
)


def _base_row(**overrides):
    row = {
        "run_id": "run-1",
        "job_id": "job-1",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8O",
        "strategy_name": "phase8o_exact_replay",
        "instrument": "EUR_USD",
        "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
        "session_window_utc": "13:30-16:00",
        "granularity": "M15",
        "lookback_days": 90,
        "replay_mode": "exact_strategy_replay",
        "exact_strategy_replay": True,
        "candidate_count": 120,
        "clean_sample_count": 120,
        "win_rate": 0.55,
        "expectancy_r": 0.2,
        "profit_factor_r": 1.4,
        "max_loss_streak": 3,
        "drawdown_proxy_r": -3.0,
        "news_reconstruction_available": True,
        "calendar_reconstruction_available": True,
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    row.update(overrides)
    return row


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _write_phase8m_import(repo: Path, *, job_id: str = "job-m", expectancy: float = 0.2):
    import_dir = repo / "ARTIFACTS/performance/imports/research_jobs" / job_id
    summary = {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "job_id": job_id,
        "phase": "Phase 8M",
        "job_type": "phase8l_backtest",
        "classification": "RESEARCH_JOB_RESULT",
        "machine_role": "5950X",
        "instrument": "EUR_USD",
        "granularity": "M15",
        "lookback_days": 90,
        "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
        "session_window_utc": "13:30-16:00",
        "replay_mode": "best_available_proxy_reconstruction",
        "candidate_count": 80,
        "expectancy_r": expectancy,
        "profit_factor_r": 1.25,
        "max_loss_streak": 3,
        "drawdown_proxy_r": -2.0,
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "news_reconstruction_available": True,
        "calendar_reconstruction_available": True,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    manifest = {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8M",
        "classification": "IMPORTED_RESEARCH_JOB_RESULT",
        "job_id": job_id,
        "job_type": "phase8l_backtest",
        "result_pack_size_bytes": 1234,
        "summary": summary,
        "recommendation": {
            "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        },
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    _write_json(import_dir / "phase8m_import_manifest.json", manifest)


def _write_phase8o_import(repo: Path, *, name: str = "phase8o_import_1", classification: str = "PASS_EXACT_REPLAY"):
    import_dir = repo / "ARTIFACTS/performance/imports/phase8o" / name
    summary = _base_row(classification=classification)
    summary.pop("run_id", None)
    _write_json(
        import_dir / "phase8o_alpha_import_manifest.json",
        {
            "generated_at_utc": "2026-01-01T00:00:00Z",
            "phase": "Phase 8O",
            "classification": "IMPORTED_PHASE8O_EXACT_REPLAY_RESULT",
            "result_pack_size_bytes": 2345,
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        },
    )
    _write_json(import_dir / "phase8o_backtest_summary.json", summary)
    _write_json(import_dir / "phase8o_recommendation.json", {"recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW"})


class TestPhase8PResearchDashboard(unittest.TestCase):
    def test_scorer_promotes_only_when_thresholds_and_exact_context_pass(self):
        scored = score_row(_base_row())
        self.assertEqual(scored["promotion_label"], PROMOTE)

        no_news = score_row(_base_row(news_reconstruction_available=False))
        self.assertEqual(no_news["promotion_label"], CONTINUE)
        self.assertIn("news_calendar_unavailable", no_news["decision_reason"])

    def test_scorer_blocks_demotes_watches_and_fails_closed(self):
        self.assertEqual(score_row(_base_row(drawdown_proxy_r=-7.0))["promotion_label"], BLOCK)
        self.assertEqual(score_row(_base_row(expectancy_r=-0.1))["promotion_label"], DEMOTE)
        self.assertEqual(score_row(_base_row(expectancy_r=0.08, profit_factor_r=1.08, clean_sample_count=40))["promotion_label"], WATCH)
        self.assertEqual(score_row(_base_row(live_permission=True))["promotion_label"], FAIL_CLOSED)

    def test_index_reads_phase8m_and_phase8o_imports(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            _write_phase8o_import(repo)
            index = build_index(repo)
            self.assertEqual(index["row_count"], 2)
            self.assertEqual(index["live_permission"], False)
            labels = {row["promotion_label"] for row in index["rows"]}
            self.assertIn(PROMOTE, labels)
            self.assertIn(CONTINUE, labels)

    def test_index_handles_phase8o_fail_closed_result(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8o_import(repo, classification="FAIL_CLOSED_DATA_INCOMPLETE")
            index = build_index(repo)
            self.assertEqual(index["rows"][0]["promotion_label"], FAIL_CLOSED)

    def test_dashboard_merges_calendar_usage_when_repo_root_provided(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            _write_phase8o_import(repo)
            perf = repo / "ARTIFACTS/performance"
            perf.mkdir(parents=True, exist_ok=True)
            (perf / "latest_calendar_api_usage_report.json").write_text(
                json.dumps(
                    {
                        "calendar_calls_this_month": 3,
                        "calendar_budget_remaining": 997,
                        "calendar_cache_hit_rate": 0.5,
                        "last_calendar_api_call_utc": "2026-05-01T12:00:00Z",
                        "calendar_budget_monthly_cap": 1000,
                        "next_paid_call_allowed": True,
                        "budget_decision_reason": "within_budget",
                    }
                ),
                encoding="utf-8",
            )
            index = build_index(repo)
            dashboard = build_dashboard(index, repo_root=repo)
            self.assertEqual(dashboard.get("calendar_calls_this_month"), 3)
            self.assertEqual(dashboard.get("calendar_budget_remaining"), 997)
            self.assertTrue(dashboard.get("calendar_usage_report_present"))

    def test_dashboard_json_has_required_tables_and_html_rows(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            _write_phase8o_import(repo)
            index = build_index(repo)
            dashboard = build_dashboard(index)
            for key in (
                "latest_research_runs",
                "strategy_leaderboard",
                "pair_session_leaderboard",
                "promotion_candidates",
                "demoted_blocked_candidates",
                "fail_closed_data_incomplete_runs",
                "news_calendar_provider_status",
                "weekly_diary_summary",
            ):
                self.assertIn(key, dashboard)
            html = render_html(dashboard)
            self.assertIn("<table>", html)
            self.assertIn("Phase 8P Research Dashboard", html)

    def test_write_index_and_dashboard_caps_are_compact_for_fixture(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            _write_phase8m_import(repo)
            index = build_index(repo)
            result = write_index(index, repo / "ARTIFACTS/performance/research_results_index.json", repo / "ARTIFACTS/performance/research_results_index.jsonl")
            self.assertLess(result["index_jsonl_size_bytes"], 25 * 1024 * 1024)

    def test_retention_cleanup_does_not_delete_latest_pointer(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            old_dir = repo / "ARTIFACTS/performance/imports/research_jobs/old-job"
            old_dir.mkdir(parents=True)
            (old_dir / "phase8m_import_manifest.json").write_text("{}", encoding="utf-8")
            latest = repo / "ARTIFACTS/performance/latest_research_job_result.json"
            latest.parent.mkdir(parents=True, exist_ok=True)
            latest.write_text("{}", encoding="utf-8")
            old_time = time.time() - (181 * 86400)
            os.utime(old_dir, (old_time, old_time))
            report = cleanup(repo_root=repo, retain_alpha_imports_days=180)
            self.assertEqual(report["retention_deleted_count"], 1)
            self.assertTrue(latest.exists())
            self.assertFalse(old_dir.exists())

    def test_phase8p_scripts_do_not_touch_blocked_runtime_operations(self):
        root = Path(__file__).resolve().parents[1]
        for script in root.glob("scripts/phase8p_*"):
            text = script.read_text(encoding="utf-8").lower()
            self.assertNotIn("runtime/config.yaml", text)
            self.assertNotIn("ai-quant-runner", text)
            self.assertNotIn("mt5", text)
            self.assertNotIn("send_trade_unlock_changed = $true", text)
            self.assertNotIn('"live_permission": true', text)

    def test_scheduler_is_local_weekend_task(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts/phase8p_install_weekend_scheduler.ps1").read_text(encoding="utf-8")
        self.assertIn("Saturday", text)
        self.assertIn("phase8p_weekend_research_cycle.ps1", text)
        self.assertIn("do_not_schedule_on_alpha", text)


if __name__ == "__main__":
    unittest.main()
