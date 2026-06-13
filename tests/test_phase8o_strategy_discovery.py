import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.phase8o_find_exact_strategy_logic import discover


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestPhase8OStrategyDiscovery(unittest.TestCase):
    def test_fails_closed_when_required_logic_missing(self):
        with TemporaryDirectory() as td:
            report = discover(Path(td))
            self.assertEqual(report["classification"], "FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND")
            self.assertFalse(report["exact_replay_possible"])
            self.assertTrue(report["missing_logic"])
            self.assertTrue(report["no_assumptions"])

    def test_records_exact_paths_when_fixture_provides_them(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _write(
                root / "working_trading_system.py",
                "signals = strategy.analyze_market(market_data)\n"
                "selected = self.trade_selector.select_trades(signals, {}, {})\n"
                "fetch_news_with_registry(); is_embargo = True\n",
            )
            _write(
                root / "src" / "core" / "trade_selector.py",
                "class TradeSelector:\n"
                "    def calculate_score(self, signal): return 1\n",
            )
            _write(
                root / "src" / "strategies" / "fixture_strategy.py",
                "class FixtureStrategy:\n"
                "    def analyze_market(self, market_data, news_data=None):\n"
                "        entry_price = 1.1\n"
                "        stop_loss = 1.0\n"
                "        take_profit = 1.3\n"
                "        return [TradeSignal(entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit)]\n",
            )
            _write(
                root / "scripts" / "local_research" / "phase8l_dataset_builder.py",
                "def add_indicators(df):\n"
                "    df['atr_14'] = 1\n"
                "    df['rsi_14'] = 50\n",
            )
            _write(
                root / "scripts" / "local_research" / "phase8l_news_calendar_fetch.py",
                "def fetch_tradingeconomics_calendar_rows(): pass\n"
                "def fetch_finnhub_calendar_rows(): pass\n",
            )
            _write(
                root / "src" / "strategies" / "session_regime_aligned.py",
                "def should_allow_trade(symbol, market_data, news_context, timestamp_utc):\n"
                "    return _classify_session(timestamp_utc)\n",
            )
            _write(
                root / "src" / "control_plane" / "strategy_registry.py",
                "STRATEGIES = {'x': {'session_preference': 'ny', 'instruments': ['EUR_USD']}}\n",
            )
            _write(root / "docs" / "focus.md", "A+ FOCUS classification is documented here.\n")
            report = discover(root)
            self.assertEqual(report["classification"], "PASS_EXACT_LOGIC_DISCOVERY_COMPLETE")
            self.assertTrue(report["exact_replay_possible"])
            self.assertEqual(report["missing_logic"], [])
            self.assertIn("working_trading_system.py", report["candidate_generation_path"])


if __name__ == "__main__":
    unittest.main()
