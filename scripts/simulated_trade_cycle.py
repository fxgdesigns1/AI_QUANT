#!/usr/bin/env python3
"""
Run a single simulated trading cycle to force Trade With Pat ORB to emit a signal.
This is a safe demo: no real orders placed — signals are routed to a mock executor.
"""
from datetime import datetime, timedelta
import pandas as pd
import os, sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import importlib.util
from pathlib import Path

# Try to import strategy module from known locations
strategy_paths = [
    os.path.join(project_root, 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system', 'src', 'strategies', 'trade_with_pat_orb_dual.py'),
    os.path.join(project_root, 'src', 'strategies', 'trade_with_pat_orb_dual.py'),
    os.path.join(project_root, 'Strategies here', 'trade_with_pat_orb_dual.py'),
]

strategy_mod = None
for p in strategy_paths:
    if os.path.isfile(p):
        spec = importlib.util.spec_from_file_location('trade_with_pat_orb_dual', p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        strategy_mod = mod
        break

if strategy_mod is None:
    raise RuntimeError('Could not find trade_with_pat_orb_dual.py in known locations')

get_trade_with_pat_orb_dual_strategy = strategy_mod.get_trade_with_pat_orb_dual_strategy
from src.core.account_orchestrator import get_account_orchestrator, route_signal_dict

def build_df(now, bars=20):
    rows = []
    base = 1.1000
    for i in range(bars):
        ts = (now - timedelta(minutes=(bars - i))).isoformat()
        open_p = base + 0.0005 * i
        close = open_p + 0.0004
        high = close + 0.0002
        low = open_p - 0.0002
        rows.append({"timestamp": ts, "open": open_p, "high": high, "low": low, "close": close})
    df = pd.DataFrame(rows)
    return df

def main():
    now = datetime.utcnow()
    strat = get_trade_with_pat_orb_dual_strategy()

    # Build market_data containing DataFrame for one instrument
    df = build_df(now)
    df.name = "EUR_USD"
    market_data = {"EUR_USD": df}

    signals = strat.generate_signals(market_data)
    print("Generated signals:", signals)

    # Route via orchestrator to mock executor
    orc = get_account_orchestrator()
    executed = []
    def mock_exec(sig):
        executed.append(sig)
        return {"status": "mocked", "instrument": sig.get("instrument") if isinstance(sig, dict) else getattr(sig, "instrument", None)}

    orc.register_account("TEST_DEMO", executor=mock_exec)

    # Convert signals to dict if needed and route
    for s in signals:
        if hasattr(s, "instrument"):
            d = {
                "instrument": getattr(s, "instrument"),
                "side": getattr(s, "side"),
                "entry_price": getattr(s, "entry_price"),
                "stop_loss": getattr(s, "stop_loss"),
                "take_profit": getattr(s, "take_profit"),
                "confidence": getattr(s, "confidence"),
                "strategy": getattr(s, "strategy", None),
                "account_id": "TEST_DEMO"
            }
        else:
            d = s
        res = route_signal_dict(d)
        print("Routed result:", res)

    print("Executed:", executed)

if __name__ == "__main__":
    main()


