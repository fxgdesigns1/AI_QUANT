"""Phase 8X batch tournament: matrix size, job creation, scoring hooks (no live trading)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.phase8x_create_batch_jobs import (
    SESSION_WINDOW_UTC,
    count_jobs,
    create_jobs,
    iter_job_specs,
)
from scripts.phase8x_score_batch_results import gate_to_score_thresholds

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestPhase8XBatchTournament(unittest.TestCase):
    def test_default_matrix_job_count(self):
        self.assertEqual(
            count_jobs(
                instruments=("EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"),
                granularities=("M5", "M15", "H1"),
                lookbacks=(90, 180, 365),
                sessions=("LONDON_OPEN", "NY_OPEN", "NY_OPEN_SECONDARY_PROPOSED"),
                strategies=(
                    "exact_current_alpha_strategy",
                    "session_breakout_with_news_embargo",
                    "trend_pullback_with_session_filter",
                ),
            ),
            5 * 3 * 3 * 3 * 3,
        )

    def test_session_windows_defined(self):
        for s in ("LONDON_OPEN", "NY_OPEN", "NY_OPEN_SECONDARY_PROPOSED"):
            self.assertIn(s, SESSION_WINDOW_UTC)
            self.assertRegex(SESSION_WINDOW_UTC[s], r"^\d{2}:\d{2}-\d{2}:\d{2}$")

    def test_iter_specs_includes_strategy_and_rr(self):
        spec = next(
            iter_job_specs(
                instruments=("EUR_USD",),
                granularities=("M15",),
                lookbacks=(90,),
                sessions=("NY_OPEN",),
                strategies=("trend_pullback_with_session_filter",),
            )
        )
        self.assertEqual(spec["instrument"], "EUR_USD")
        self.assertEqual(spec["research_strategy_key"], "trend_pullback_with_session_filter")
        self.assertEqual(spec["rr_multiple"], 1.5)

    def test_gate_to_score_thresholds(self):
        t = gate_to_score_thresholds(
            {
                "minimum_trades": 80,
                "minimum_profit_factor": 1.25,
                "minimum_expectancy_r": 0.10,
                "maximum_drawdown_r": -6.0,
                "maximum_loss_streak": 5,
            }
        )
        self.assertEqual(t["minimum_clean_samples_for_review"], 80)
        self.assertEqual(t["minimum_profit_factor_for_review"], 1.25)
        self.assertEqual(t["maximum_loss_streak_for_review"], 5)

    def test_create_jobs_writes_pending(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job_root = root / "ARTIFACTS" / "research_jobs"
            specs = list(
                iter_job_specs(
                    instruments=("EUR_USD",),
                    granularities=("M15",),
                    lookbacks=(14,),
                    sessions=("NY_OPEN_SECONDARY_PROPOSED",),
                    strategies=("exact_current_alpha_strategy",),
                )
            )
            res = create_jobs(
                repo_root=root,
                job_root=job_root,
                specs=specs,
                requested_by="test@test",
                dry_run=False,
            )
            self.assertTrue(res.get("ok"))
            pending = list((job_root / "queue" / "pending").glob("*.json"))
            self.assertEqual(len(pending), 1)
            job = json.loads(pending[0].read_text(encoding="utf-8"))
            self.assertEqual(job.get("job_type"), "phase8l_backtest")
            self.assertEqual((job.get("params") or {}).get("strategy_name"), "exact_current_alpha_strategy")

    def test_target_manifest_out_written(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job_root = root / "ARTIFACTS" / "research_jobs"
            manifest = root / "ARTIFACTS" / "performance" / "phase8x_active_batch_target.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            script = REPO_ROOT / "scripts" / "phase8x_create_batch_jobs.py"
            r = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--repo-root",
                    str(root),
                    "--job-root",
                    str(job_root),
                    "--max-jobs",
                    "1",
                    "--skip-calendar-preflight",
                    "--skip-phase8y-preflight",
                    "--target-manifest-out",
                    str(manifest),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(manifest.is_file())
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("target_total"), 1)
            self.assertEqual(len(payload.get("job_ids") or []), 1)


if __name__ == "__main__":
    unittest.main()
