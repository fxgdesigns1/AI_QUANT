#!/usr/bin/env python3
"""
Run a single simulated trading cycle that forces a strategy to emit a signal (safe demo).
This script:
 - Loads the 'momentum_trading' strategy via registry
 - Seeds its price_history with synthetic trending data
 - Calls analyze_market() with simplified MarketData-like objects
 - Routes any generated signals via the AccountOrchestrator to a mock executor
"""
from datetime import datetime
from types import SimpleNamespace
from src.core.account_orchestrator import get_account_orchestrator
from src.strategies.registry import create_strategy
from src.core.order_manager import OrderSide


def make_md(bid, ask, volume=1000.0):
    return SimpleNamespace(bid=bid, ask=ask, mid=(bid + ask) / 2.0, volume=volume)


def main():
    strategy = create_strategy("momentum_trading")
    if strategy is None:
        print("Could not create momentum_trading strategy via registry")
        return

    # ensure account context
    strategy.account_id = "demo-acct-1"

    # Seed price history with an uptrend for GBP_USD (momentum)
    inst = "GBP_USD"
    prices = [1.2000 + i * 0.001 for i in range(200)]  # gentle uptrend
    if hasattr(strategy, "price_history") and inst in strategy.price_history:
        strategy.price_history[inst] = prices.copy()
    else:
        try:
            strategy.price_history = {inst: prices.copy()}
        except Exception:
            strategy.price_history = {inst: prices.copy()}

    # Build market_data for analyze_market: object with bid/ask
    market_data = {inst: make_md(prices[-1] - 0.0002, prices[-1] + 0.0003, volume=2000.0)}

    # Register mock executor on orchestrator
    orchestrator = get_account_orchestrator()
    executed = []

    def mock_exec(sig):
        executed.append(sig)
        return {"status": "queued", "instrument": sig.get("instrument") if isinstance(sig, dict) else getattr(sig, "instrument", None)}

    orchestrator.register_account("demo-acct-1", executor=mock_exec)

    # Run analysis
    signals = strategy.analyze_market(market_data)
    print("Generated signals count:", len(signals))
    for s in signals:
        print("Signal:", getattr(s, "instrument", None), getattr(s, "strategy_name", None), getattr(s, "account_id", None))
        # route via orchestrator
        res = orchestrator.route_signal(s)
        print("Routed result:", res)

    print("Mock executed list:", executed)


if __name__ == "__main__":
    main()


