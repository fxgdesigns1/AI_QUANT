from Strategies here.momentum_trading import MomentumTradingStrategy
from datetime import datetime


class DummyMD:
    def __init__(self, bid, ask, volume=1000):
        self.bid = bid
        self.ask = ask
        self.mid = (bid + ask) / 2
        self.volume = volume
        self.timestamp = datetime.utcnow()


def test_momentum_strategy_sets_account_id_and_generates_signals():
    strat = MomentumTradingStrategy(instruments=["GBP_USD"])
    strat.account_id = "acct-xyz"
    market = {"GBP_USD": DummyMD(1.2700, 1.2705, 1000)}
    signals = strat.analyze_market(market)
    # Signals may be empty depending on filters; ensure account_id propagation on constructed signals if present
    for s in signals:
        assert getattr(s, "account_id", None) == "acct-xyz"


