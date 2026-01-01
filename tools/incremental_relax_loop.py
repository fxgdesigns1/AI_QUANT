#!/usr/bin/env python3
"""
Incremental relax-and-check loop (non-invasive).

Behavior:
 - Instantiates each registered strategy.
 - Attempts up to N relaxation steps per strategy by lowering thresholds
   (min_volatility, min_atr_for_entry, min_quality_score, min_confirmations).
 - After each step calls strategy.generate_signals(...) with synthesized market data.
 - Stops when ANY strategy produces >= trigger_signals signals.
 - Does NOT place orders.
 - Saves a JSON report to /tmp/incremental_relax_report.json
"""
import logging
import os
import sys
import json
import random
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incremental_relax")

# Make repo importable when run on VM
_candidates = [
    os.path.abspath(os.path.join(os.getcwd(), "Sync folder MAC TO PC", "DESKTOP_HANDOFF_PACKAGE", "google-cloud-trading-system")),
    "/opt/quant_system_clean",
    "/opt/quant_system_clean/google-cloud-trading-system",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
]
for p in _candidates:
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

from src.strategies.registry import available_strategies, resolve_strategy_key, create_strategy

def fetch_dashboard():
    import requests
    url = os.getenv("DASHBOARD_URL", "https://ai-quant-trading.uc.r.appspot.com/api/status")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def synthesize_market_objects(raw_market_data):
    import pandas as pd
    from datetime import datetime, timedelta, timezone

    class FakeMarket:
        def __init__(self, bid, ask, ts, df):
            self.bid = bid
            self.ask = ask
            self.timestamp = ts
            self._df = df
        def to_dataframe(self):
            return self._df
        @property
        def candles(self):
            return self._df.to_dict("records")
        def __len__(self):
            return len(self._df)

    now = datetime.now(timezone.utc)
    synthesized = {}
    for inst, v in (raw_market_data or {}).items():
        try:
            ask = float(v.get("ask", v.get("last", 0.0)))
            bid = float(v.get("bid", ask))
        except Exception:
            continue
        price = (ask + bid) / 2.0 if (ask and bid) else ask
        candles = []
        for i in range(50):
            ts = now - timedelta(minutes=(50 - i))
            noise = random.uniform(-0.0005, 0.0005) * max(1.0, price)
            close = price + noise
            high = close + abs(noise)*0.6 + 0.0001
            low = close - abs(noise)*0.6 - 0.0001
            open_p = close - noise*0.2
            candles.append({"timestamp": ts.isoformat(), "open": open_p, "high": high, "low": low, "close": close})
        df = __import__("pandas").DataFrame(candles)
        df["timestamp"] = __import__("pandas").to_datetime(df["timestamp"])
        df.name = inst
        synthesized[inst] = FakeMarket(bid=bid, ask=ask, ts=now, df=df)
    return synthesized

def try_relax_and_signal(strategy_key, market):
    """Try incremental relax steps on a single strategy object. Return signals if any."""
    logger.info("Testing strategy %s", strategy_key)
    strat = create_strategy(strategy_key)
    if strat is None:
        return {"status": "no_factory", "signals": []}

    # Parameter names we may attempt to relax if present
    relax_params = [
        ("min_volatility", [0.8,0.6,0.4,0.2,0.0]),
        ("min_atr_for_entry", [0.8,0.6,0.4,0.2,0.0]),
        ("min_quality_score", [0.9,0.75,0.6,0.4,0.0]),
        ("min_confirmations", [1,1,0,0,0]),
    ]

    # Capture original values
    orig = {}
    for name, _ in relax_params:
        orig[name] = getattr(strat, name, None)

    steps = max(len(vals) for _, vals in relax_params)
    for step in range(steps):
        # Apply relaxations for this step
        for name, vals in relax_params:
            if step < len(vals):
                val = vals[step]
                # If param is multiplicative (vol/atr), apply factor
                if name in ("min_volatility","min_atr_for_entry"):
                    orig_val = orig.get(name) or 0.0
                    new = orig_val * val if orig_val is not None else 0.0
                    setattr(strat, name, new)
                else:
                    # direct set (quality/confirms)
                    if orig.get(name) is None:
                        # try alternative attribute names
                        if name == "min_quality_score" and hasattr(strat, "min_quality_score"):
                            setattr(strat, "min_quality_score", int(val*100) if val>1 else int(val*100))
                        continue
                    setattr(strat, name, int(val) if isinstance(orig.get(name), int) else val)

        # Call generate_signals with synthesized market
        try:
            if hasattr(strat, "generate_signals"):
                signals = strat.generate_signals(market)
            elif hasattr(strat, "analyze_market"):
                signals = strat.analyze_market(market)
            else:
                signals = []
        except Exception as e:
            logger.exception("Error calling strategy %s: %s", strategy_key, e)
            signals = []

        if signals:
            return {"status": "signals", "signals": signals, "step": step}

    # restore original attributes
    for k,v in orig.items():
        if v is not None:
            setattr(strat, k, v)
    return {"status": "no_signals", "signals": []}

def main():
    dashboard = fetch_dashboard()
    market_raw = dashboard.get("market_data", {})
    market = synthesize_market_objects(market_raw)

    # Determine strategies to test from dashboard accounts
    accounts = dashboard.get("accounts", {}) or {}
    tested = {}
    for acct_id, acct in accounts.items():
        strategy_key = acct.get("strategy_key") or acct.get("strategy")
        if not strategy_key:
            continue
        if strategy_key in tested:
            continue
        res = try_relax_and_signal(strategy_key, market)
        tested[strategy_key] = res
        logger.info("Result for %s: %s", strategy_key, res.get("status"))
        if res.get("status") == "signals":
            break

    out = {"timestamp": datetime.now(timezone.utc).isoformat(), "results": tested}
    with open("/tmp/incremental_relax_report.json", "w") as fh:
        fh.write(json.dumps(out, default=str, indent=2))
    print(json.dumps(out, default=str, indent=2))

if __name__ == "__main__":
    main()
































