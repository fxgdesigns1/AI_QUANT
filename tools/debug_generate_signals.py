#!/usr/bin/env python3
"""
Non-invasive debug: fetch dashboard market snapshot and ask each registered
strategy to produce signals (no orders placed). Prints sample signals for
manual inspection.
"""
import requests
import logging
import os
import json
from typing import Any
import sys

# Ensure repository src package is importable when running on the VM
_candidates = [
    os.path.abspath(os.path.join(os.getcwd(), "Sync folder MAC TO PC", "DESKTOP_HANDOFF_PACKAGE", "google-cloud-trading-system")),
    "/opt/quant_system_clean",
    "/opt/quant_system_clean/google-cloud-trading-system",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
]
for p in _candidates:
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_signals")

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://ai-quant-trading.uc.r.appspot.com/api/status")

def fetch_dashboard() -> Any:
    r = requests.get(DASHBOARD_URL, timeout=10)
    r.raise_for_status()
    return r.json()

def instantiate_strategy(raw_key: str):
    try:
        from src.strategies.registry import create_strategy, resolve_strategy_key
        key = resolve_strategy_key(raw_key)
        if not key:
            logger.warning("Could not resolve strategy key: %s", raw_key)
            return None
        return create_strategy(key)
    except Exception as e:
        logger.exception("Error instantiating strategy %s: %s", raw_key, e)
        return None

def call_strategy(strategy, market_data):
    """Call strategy in a safe way and return list of signals (may be empty)."""
    try:
        if strategy is None:
            return []
        # Prefer generate_signals signature
        if hasattr(strategy, "generate_signals"):
            try:
                return strategy.generate_signals(market_data) or []
            except TypeError:
                # Some strategies expect (data, pair) signature - try analyze_market instead
                pass
        if hasattr(strategy, "analyze_market"):
            try:
                return strategy.analyze_market(market_data) or []
            except TypeError:
                return []
        return []
    except Exception as e:
        logger.exception("Strategy call error: %s", e)
        return []

def synthesize_market_objects(raw_market_data):
    """Convert dashboard market_data into strategy-friendly objects."""
    import pandas as pd
    import random
    from datetime import datetime, timedelta, timezone

    class FakeMarket:
        def __init__(self, bid, ask, timestamp, df):
            self.bid = bid
            self.ask = ask
            self.timestamp = timestamp
            self._df = df

        def to_dataframe(self):
            return self._df

        @property
        def candles(self):
            # Some strategies read .candles
            return self._df.to_dict("records")

        def __len__(self):
            return len(self._df)

        def __repr__(self):
            return f"<FakeMarket bid={self.bid} ask={self.ask} ts={self.timestamp}>"

    now = datetime.now(timezone.utc)
    synthesized = {}
    for inst, v in (raw_market_data or {}).items():
        try:
            ask = float(v.get("ask", v.get("last", 0.0)))
            bid = float(v.get("bid", ask))
        except Exception:
            continue
        # Build a simple candle history (50 candles) with small random noise
        candles = []
        price = (ask + bid) / 2.0 if (ask and bid) else ask
        for i in range(50):
            ts = now - timedelta(minutes=(50 - i))
            noise = random.uniform(-0.0005, 0.0005) * max(1.0, price)
            close = price + noise
            high = close + abs(noise) * 0.6 + 0.0001
            low = close - abs(noise) * 0.6 - 0.0001
            open_p = close - noise * 0.2
            candles.append({"timestamp": ts.isoformat(), "open": open_p, "high": high, "low": low, "close": close})
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.name = inst
        fake = FakeMarket(bid=bid, ask=ask, timestamp=now, df=df)
        synthesized[inst] = fake
    return synthesized

def summarize_signals(signals):
    out = []
    for s in (signals or [])[:5]:
        try:
            # Try dataclass/object attributes first
            if hasattr(s, "__dict__"):
                d = {k: (v if not hasattr(v, 'isoformat') else v.isoformat()) for k,v in s.__dict__.items()}
            elif isinstance(s, dict):
                d = s
            else:
                d = str(s)
        except Exception:
            d = str(s)
        out.append(d)
    return out

def main():
    logger.info("Fetching dashboard snapshot from %s", DASHBOARD_URL)
    snapshot = fetch_dashboard()
    market_data = snapshot.get("market_data", {})
    accounts = snapshot.get("accounts", {})

    results = []
    # Create synthesized market objects for strategies (to avoid pandas errors)
    synth_market = synthesize_market_objects(market_data)
    for acct_id, acct in accounts.items():
        acct_name = acct.get("account_name") or acct.get("account_name", acct_id)
        strategy_key = acct.get("strategy_key") or acct.get("strategy") or acct.get("strategy_name")
        if not strategy_key:
            continue
        logger.info("Instantiating strategy for account %s -> %s", acct_id, strategy_key)
        strat = instantiate_strategy(strategy_key)
        signals = call_strategy(strat, synth_market)
        summary = summarize_signals(signals)
        results.append({
            "account_id": acct_id,
            "account_name": acct_name,
            "strategy_key": strategy_key,
            "signals_count": len(signals) if signals is not None else 0,
            "sample_signals": summary,
        })

    print(json.dumps({"generated": results}, indent=2, default=str))

if __name__ == "__main__":
    main()


