#!/usr/bin/env python3
"""
Run a single simulated trading cycle (safe demo).
Creates a momentum strategy, pre-fills price history with a trending series,
generates signals and routes them via the orchestrator to mock executors.
"""
from datetime import datetime, timedelta
from src.core.account_orchestrator import get_account_orchestrator
from src.core.order_manager import TradeSignal, OrderSide
from Strategies here.momentum_trading import MomentumTradingStrategy


def make_market_data_for_instrument(price):
    class MD:
        def __init__(self, bid, ask, mid=None, volume=1000):
            self.bid = bid
            self.ask = ask
            self.mid = mid if mid is not None else (bid + ask) / 2
            self.volume = volume
    return MD(price - 0.0001, price + 0.0004, price)


def main():
    orchestrator = get_account_orchestrator()
    orchestrator._managers.clear()
    orchestrator._executors.clear()

    executed = []

    def mock_exec(signal):
        executed.append(signal)
        return {"status": "ok", "instrument": signal.get("instrument") if isinstance(signal, dict) else getattr(signal, "instrument", None)}

    # Register demo account
    orchestrator.register_account("demo-acct", executor=mock_exec)

    # Create strategy and prefill price history
    strat = MomentumTradingStrategy(instruments=['GBP_USD'])
    strat.account_id = "demo-acct"
    # Prefill increasing prices to create bullish momentum
    base = 1.2500
    prices = [base * (1.0005 ** i) for i in range(60)]
    strat.price_history['GBP_USD'] = prices.copy()

    # Build market data snapshot
    market_data = {'GBP_USD': make_market_data_for_instrument(prices[-1])}

    signals = strat._generate_trade_signals(market_data)

    print("Generated signals:", len(signals))
    for s in signals:
        print("Signal:", s.instrument, s.side, getattr(s, 'account_id', None), s.confidence)
        orchestrator.route_signal(s)

    print("Executed via mock_exec:", len(executed))


if __name__ == "__main__":
    main()

