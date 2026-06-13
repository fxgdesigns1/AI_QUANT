import unittest

import pandas as pd
from datetime import datetime, timedelta, timezone

from scripts.local_research.phase8k_replay_lib import simulate_trade_r
from scripts.local_research.phase8l_replay_engine import run_full_replay

UTC = timezone.utc


def _fixture_df():
    t0 = datetime(2026, 1, 5, 13, 30, tzinfo=UTC)
    rows = []
    p = 1.10
    for i in range(40):
        rows.append(
            {
                "time_utc": t0 + timedelta(minutes=15 * i),
                "o": p,
                "h": p + 0.002,
                "l": p - 0.002,
                "c": p + 0.0001,
                "volume": 10,
                "instrument": "EUR_USD",
                "granularity": "M15",
                "news_embargo_adjacent": False,
                "calendar_high_impact_adjacent": False,
            }
        )
        p += 0.00005
    return pd.DataFrame(rows)


class TestPhase8LReplayEngine(unittest.TestCase):
    def test_proxy_replay_classification(self):
        df = _fixture_df()
        df["pip_size"] = 0.0001
        df["session_label"] = "NY_OPEN_SECONDARY_PROPOSED"
        df["session_day_utc"] = df["time_utc"].dt.date
        df["news_embargo_adjacent"] = False
        df["calendar_high_impact_adjacent"] = False
        df["embargo_or_degraded"] = False
        res = run_full_replay(
            dataset=df,
            input_pack=None,
            instrument="EUR_USD",
            granularity="M15",
            spread_pips=1.0,
            slippage_pips=0.5,
            rr_multiple=2.0,
        )
        self.assertIn("ny_session", res)
        self.assertEqual(res["ny_session"]["meta"]["replay_mode"], "best_available_proxy_reconstruction")

    def test_same_bar_sl_before_tp_long(self):
        bars = [
            {"o": 1.0, "h": 1.2, "l": 0.8, "c": 1.1},
        ]
        outcome, _, rmul = simulate_trade_r(
            side="BUY",
            entry=1.0,
            stop_loss=0.85,
            take_profit=1.15,
            bars_after_entry=bars,
            spread_half=0.0,
            slippage=0.0,
        )
        self.assertEqual(outcome, "loss")
        self.assertEqual(rmul, -1.0)

    def test_r_multiple_win(self):
        bars = [
            {"o": 1.0, "h": 1.12, "l": 0.99, "c": 1.11},
        ]
        outcome, _, rmul = simulate_trade_r(
            side="BUY",
            entry=1.0,
            stop_loss=0.95,
            take_profit=1.10,
            bars_after_entry=bars,
            spread_half=0.0,
            slippage=0.0,
        )
        self.assertEqual(outcome, "win")
        self.assertGreater(rmul, 0)


if __name__ == "__main__":
    unittest.main()
