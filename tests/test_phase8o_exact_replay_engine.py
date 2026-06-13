import json
import unittest
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.local_research.phase8k_replay_lib import simulate_trade_r
from scripts.phase8o_run_exact_strategy_replay import run_replay
from scripts.phase8o_verify_exact_replay_result import verify_result_pack

UTC = timezone.utc


def _dataset() -> pd.DataFrame:
    t0 = datetime(2026, 1, 5, 13, 30, tzinfo=UTC)
    rows = []
    p = 1.1
    for i in range(8):
        rows.append(
            {
                "time_utc": t0 + timedelta(minutes=15 * i),
                "o": p,
                "h": p + 0.002,
                "l": p - 0.0002,
                "c": p + 0.001,
                "volume": 100,
                "instrument": "EUR_USD",
                "granularity": "M15",
                "pip_size": 0.0001,
                "news_embargo_adjacent": False,
                "calendar_high_impact_adjacent": False,
            }
        )
        p += 0.0001
    return pd.DataFrame(rows)


class TestPhase8OExactReplayEngine(unittest.TestCase):
    def test_same_bar_sl_before_tp_conservative_assumption(self):
        outcome, _, r_mult = simulate_trade_r(
            side="BUY",
            entry=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            bars_after_entry=[{"h": 1.2, "l": 0.8, "c": 1.0}],
        )
        self.assertEqual(outcome, "loss")
        self.assertEqual(r_mult, -1.0)

    def test_exact_candidate_replay_uses_archived_entry_sl_tp_and_verifies_pack(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            data_path = root / "dataset.pkl"
            _dataset().to_pickle(data_path)
            manifest_path = root / "dataset_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "dataset_start_utc": "2026-01-05T13:30:00Z",
                        "dataset_end_utc": "2026-01-05T15:15:00Z",
                        "news_reconstruction_available": True,
                        "calendar_reconstruction_available": True,
                    }
                ),
                encoding="utf-8",
            )
            discovery_path = root / "discovery.json"
            discovery_path.write_text(
                json.dumps({"exact_replay_possible": True, "strategy_paths_found": [{"path": "fixture"}]}),
                encoding="utf-8",
            )
            cand_path = root / "candidates.json"
            cand_path.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "generated_at_utc": "2026-01-05T13:30:00Z",
                                "instrument": "EUR_USD",
                                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                                "side": "BUY",
                                "entry": 1.1,
                                "stop_loss": 1.099,
                                "take_profit": 1.101,
                                "score": 91.0,
                                "grade": "A",
                                "pair_session_policy_class": "ALLOW",
                                "news_gate_status": "CLEAR",
                                "preflight_state": "RESEARCH_ONLY",
                                "candidate_source": "fixture",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out_dir = root / "outputs"
            result = run_replay(
                dataset_path=data_path,
                dataset_manifest=manifest_path,
                discovery_report=discovery_path,
                candidate_archive=cand_path,
                out_dir=out_dir,
                instrument="EUR_USD",
                granularity="M15",
                lookback_days=90,
                session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                spread_pips=0.0,
                slippage_pips=0.0,
                write_result_pack=True,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["summary"]["classification"], "PASS_EXACT_CANDIDATE_REPLAY_COMPLETE")
            self.assertTrue(result["summary"]["exact_strategy_replay"])
            self.assertEqual(result["summary"]["candidate_count"], 1)
            pack = Path(result["result_pack"])
            verify = verify_result_pack(pack)
            self.assertTrue(verify.ok)

            summary_path = out_dir / "phase8o_backtest_summary.json"
            bad_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            bad_summary["live_permission"] = True
            summary_path.write_text(json.dumps(bad_summary), encoding="utf-8")
            bad_pack = root / "bad_result_pack.tar.gz"
            with tarfile.open(bad_pack, mode="w:gz") as tf:
                for name in [
                    "phase8o_backtest_summary.json",
                    "phase8o_recommendation.json",
                    "phase8o_monthly_persistence.json",
                    "phase8o_daily_persistence.json",
                    "phase8o_run_manifest.json",
                    "phase8o_replay_samples_compact.jsonl",
                    "checksums.sha256",
                ]:
                    tf.add(out_dir / name, arcname=name)
            with self.assertRaisesRegex(Exception, "live_permission"):
                verify_result_pack(bad_pack)

    def test_no_proxy_replay_runs_when_exact_logic_missing(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            discovery_path = root / "discovery.json"
            discovery_path.write_text(
                json.dumps({"exact_replay_possible": False, "missing_logic": ["entry_logic_path"]}),
                encoding="utf-8",
            )
            result = run_replay(
                dataset_path=None,
                dataset_manifest=None,
                discovery_report=discovery_path,
                candidate_archive=None,
                out_dir=root / "outputs",
                instrument="EUR_USD",
                granularity="M15",
                lookback_days=90,
                session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                spread_pips=0.0,
                slippage_pips=0.0,
                write_result_pack=True,
            )
            self.assertEqual(result["summary"]["classification"], "FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND")
            self.assertFalse(result["summary"]["exact_strategy_replay"])
            samples = (root / "outputs" / "phase8o_replay_samples_compact.jsonl").read_text(encoding="utf-8")
            self.assertEqual(samples, "")


if __name__ == "__main__":
    unittest.main()
