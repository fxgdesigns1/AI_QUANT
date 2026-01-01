#!/usr/bin/env python3
"""
Run a single simulated trading cycle that forces the momentum strategy to emit a signal.
Safe demo: does not place real orders; routes through orchestrator to mock executor.
"""
from datetime import datetime
import sys
import os

# Add project root to sys.path for absolute imports like src.core.*
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.account_orchestrator import get_account_orchestrator
from src.core.order_manager import TradeSignal, OrderSide
import importlib.util
import os

# Load momentum_trading module from 'Strategies here' directory (contains space)
this_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
momentum_path = os.path.join(this_dir, "Strategies here", "momentum_trading.py")
spec = importlib.util.spec_from_file_location("momentum_trading", momentum_path)
momentum_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(momentum_mod)  # type: ignore
momentum_trading = getattr(momentum_mod, "momentum_trading")
MomentumTradingStrategy = getattr(momentum_mod, "MomentumTradingStrategy")


class SimpleMD:
    def __init__(self, bid, ask, volume=1000):
        self.bid = bid
        self.ask = ask
        self.volume = volume


def main():
    strat: MomentumTradingStrategy = momentum_trading
    strat.account_id = "sim-acct-001"

    inst = strat.instruments[0]

    # Fill price history with a clear upward momentum (200 bars)
    base = 1.2000
    prices = [base + i * 0.001 for i in range(200)]
    strat.price_history[inst] = prices.copy()

    # Mock market data at the tail of the series
    last = prices[-1]
    md = SimpleMD(bid=last - 0.0001, ask=last + 0.0001, volume=1000)
    market_data = {inst: md}

    # Prepare orchestrator with mock executor to avoid real orders
    orc = get_account_orchestrator()
    orc._managers.clear()
    orc._executors.clear()

    executed = []

    def mock_exec(sig):
        executed.append(sig)
        return {"status": "mocked", "account": getattr(sig, "account_id", sig.get("account_id", None))}

    orc.register_account("sim-acct-001", executor=mock_exec)

    # Run strategy analysis
    signals = strat.analyze_market(market_data)
    print("Generated signals:", signals)

    # Route signals through orchestrator
    for s in signals:
        res = orc.route_signal(s)
        print("Route result:", res)

    print("Executed captured:", executed)


if __name__ == "__main__":
    main()


