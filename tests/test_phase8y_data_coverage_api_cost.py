import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase8x_create_batch_jobs import assert_phase8y_preflight
from scripts.phase8y_build_shared_context_pack import build_pack
from scripts.phase8y_estimate_api_cost import estimate_cost
from scripts.phase8y_inventory_data_coverage import build_manifest
from scripts.phase8y_verify_context_pack import verify


class TestPhase8YCoverageAndApiCost(unittest.TestCase):
    def _write_minimum_inputs(self, root: Path) -> None:
        perf = root / "ARTIFACTS" / "performance"
        perf.mkdir(parents=True, exist_ok=True)
        (perf / "latest_calendar_api_usage_report.json").write_text(
            json.dumps(
                {
                    "calendar_calls_this_month": 3,
                    "calendar_budget_remaining": 997,
                    "calendar_cache_hits_month": 2,
                }
            ),
            encoding="utf-8",
        )
        (perf / "latest_calendar_cache_manifest.json").write_text(
            json.dumps({"entries": [{"file": "rapidapi_cache_a.json", "size_bytes": 1000}]}),
            encoding="utf-8",
        )
        (perf / "latest_phase8r_aligned_context_manifest.json").write_text(
            json.dumps(
                {
                    "aligned_window_start_day": "2026-02-01",
                    "aligned_window_end_day": "2026-05-01",
                    "news_rows_count": 120,
                    "calendar_rows_count": 80,
                }
            ),
            encoding="utf-8",
        )
        (perf / "latest_phase8r_provider_capability_report.json").write_text(
            json.dumps(
                {
                    "working_news_providers": ["newsapi"],
                    "working_calendar_providers": ["rapidapi_economic_calendar"],
                    "working_macro_providers": ["fred"],
                    "fred_rows_count": 30,
                    "provider_env_presence": {
                        "NEWSAPI_API_KEYS": True,
                        "FMP_API_KEYS": True,
                        "TRADINGECONOMICS_API_KEYS": False,
                        "FRED_API_KEYS": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        (perf / "latest_phase8o_news_provider_diagnostics.json").write_text(
            json.dumps({"news_rows_count": 120, "calendar_rows_count": 80}),
            encoding="utf-8",
        )
        (perf / "latest_phase8y_context_pack_verification.json").write_text(
            json.dumps({"ok": True, "all_files_verified": True}),
            encoding="utf-8",
        )

    def test_inventory_manifest_contains_required_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_minimum_inputs(root)
            manifest = build_manifest(
                repo_root=root,
                instrument="EUR_USD",
                lookback_days=90,
                granularities=("M15", "M5"),
                max_paid_calendar_calls=1,
                require_news=True,
                require_calendar=True,
                require_macro=False,
            )
            required = (
                "candles_by_instrument_granularity_date_range",
                "news_by_provider_date_range",
                "calendar_by_provider_date_range",
                "macro_by_provider_series_date_range",
                "cache_hits",
                "missing_windows",
                "exact_replay_possible",
                "estimated_api_calls_needed",
                "estimated_paid_calendar_calls_needed",
                "monthly_calendar_calls_used",
                "monthly_calendar_calls_remaining",
                "safe_to_run_batch",
            )
            for key in required:
                self.assertIn(key, manifest)
            # No candle evidence in temp repo should fail closed.
            self.assertFalse(manifest["safe_to_run_batch"])
            self.assertIn("missing_candles", manifest["fail_closed_reasons"])

    def test_cost_estimate_fails_when_budget_too_small(self):
        manifest = {
            "safe_to_run_batch": True,
            "estimated_paid_calendar_calls_needed": 2,
            "estimated_api_calls_needed": 3,
            "monthly_calendar_calls_used": 8,
            "monthly_calendar_calls_remaining": 1,
            "news_by_provider_date_range": {},
            "macro_by_provider_series_date_range": {},
        }
        cost = estimate_cost(manifest, max_paid_calendar_calls=1)
        self.assertFalse(cost["safe_to_run_batch"])
        self.assertFalse(cost["estimated_paid_calls_within_budget"])

    def test_shared_context_pack_verify_detects_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_minimum_inputs(root)
            perf = root / "ARTIFACTS" / "performance"
            coverage = perf / "latest_phase8y_data_coverage_manifest.json"
            coverage.write_text(
                json.dumps(
                    {
                        "safe_to_run_batch": True,
                        "estimated_paid_calendar_calls_needed": 0,
                        "estimated_api_calls_needed": 0,
                        "monthly_calendar_calls_used": 3,
                        "monthly_calendar_calls_remaining": 997,
                    }
                ),
                encoding="utf-8",
            )
            cost = perf / "latest_phase8y_api_cost_estimate.json"
            cost.write_text(json.dumps({"safe_to_run_batch": True}), encoding="utf-8")
            manifest = build_pack(
                root,
                output_dir=perf / "phase8y_shared_context_pack",
                coverage_path=coverage,
                cost_path=cost,
            )
            manifest_path = perf / "latest_phase8y_shared_context_pack_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            ok_result = verify(manifest_path)
            self.assertTrue(ok_result["ok"])

            # Corrupt one staged file and verify fail-closed.
            staged = Path(manifest["pack_dir"]) / "latest_phase8y_api_cost_estimate.json"
            staged.write_text("{}", encoding="utf-8")
            bad_result = verify(manifest_path)
            self.assertFalse(bad_result["ok"])

    def test_phase8x_gate_requires_verified_phase8y(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            perf = root / "ARTIFACTS" / "performance"
            perf.mkdir(parents=True, exist_ok=True)
            (perf / "latest_phase8y_data_coverage_manifest.json").write_text(
                json.dumps(
                    {
                        "safe_to_run_batch": True,
                        "estimated_paid_calendar_calls_needed": 1,
                        "fail_closed_reasons": [],
                    }
                ),
                encoding="utf-8",
            )
            (perf / "latest_phase8y_context_pack_verification.json").write_text(
                json.dumps({"all_files_verified": True}),
                encoding="utf-8",
            )
            got = assert_phase8y_preflight(
                root,
                manifest_path=perf / "latest_phase8y_data_coverage_manifest.json",
                max_additional_paid_calls=1,
            )
            self.assertTrue(got["ok"])
            self.assertTrue(got["context_pack_verified"])


if __name__ == "__main__":
    unittest.main()
