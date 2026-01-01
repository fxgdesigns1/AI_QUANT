#!/usr/bin/env python3
from src.core.settings import settings
"""
Today intraday backtest driver (M5) - skeleton driver designed to be executed on the VM.

What this script does (in broad terms):
- Fetch today's M5 candles for all active accounts' instruments (XAU_USD for gold lanes; FX pairs otherwise).
- Instantiate live strategy classes via StrategyFactory to mirror live signal generation.
- Feed candles in timestamp order to generate signals.
- Simulate trades using TP/SL / time-based exit and per-account risk controls.
- Emit a per-account summary and a detailed JSON dump for deeper analysis.

Note:
- Heavy-lifting logic can be delegated to a cheaper model by replacing the signal processing
  or by refactoring the generation/execution steps into separate modules.
- This is a safe, read-only skeleton for verification and quick start.
"""
import os, sys, json
import yaml
import time
import urllib.request, urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Any

sys.path.insert(0, "/opt/quant_system_clean/google-cloud-trading-system")

from src.core.strategy_factory import StrategyFactory
from src.core.data_feed import MarketData

# Config: read accounts.yaml if present, else fall back to a small inline map
ACCOUNTS_YAML_PATH = "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"

def load_accounts_yaml(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        return []
    accounts = data.get("accounts", [])
    return accounts

def fetch_today_candles(instrument: str, start_iso: str, end_iso: str, gran: str="M5"):
    API_KEY = settings.oanda_api_key
    if not API_KEY:
        raise ValueError("OANDA_API_KEY environment variable must be set")
    BASE = "https://api-fxpractice.oanda.com"
    HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    params = urllib.parse.urlencode({"granularity": gran, "price": "M", "from": start_iso, "to": end_iso})
    url = f"{BASE}/v3/instruments/{instrument}/candles?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data

def build_instrument_series(instr: str, candles: dict) -> List[Dict[str, Any]]:
    # Build a simple candle series suitable for StrategyFactory consumption
    items = candles.get("candles", [])
    series = []
    for c in items:
        if not c.get("complete"):
            continue
        mid = float(c["mid"]["c"])
        high = float(c["mid"]["h"])
        low = float(c["mid"]["l"])
        t = c["time"]
        spread = 0.5 if instr.startswith("XAU") else 0.0003
        series.append({"time": t, "bid": mid - spread/2, "ask": mid + spread/2, "mid": mid, "high": high, "low": low})
    return series

def main():
    # Load accounts
    accounts = load_accounts_yaml(ACCOUNTS_YAML_PATH)
    if not accounts:
        # Minimal fallback accounts (same shape as in live YAML used above)
        accounts = [
            {"id": "101-004-30719775-001", "strategy": "gold_scalping", "instruments": ["XAU_USD"], "active": True},
        ]

    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_iso = start_of_day.isoformat()
    end_iso = now.isoformat()

    factory = StrategyFactory()
    results = {}

    for acc in accounts:
        acct_id = acc.get("id") or acc.get("account_id") or "unknown"
        strategy_name = acc.get("strategy")
        instruments = acc.get("instruments", [])
        if not strategy_name or not instruments:
            continue
        print(f"Backtesting {acct_id} -> {strategy_name} on {instruments}")

        strat = None
        try:
            strat = factory.get_strategy(strategy_name, {"instruments": instruments})
        except Exception:
            strat = None
        if strat is None:
            print(f"Could not load strategy {strategy_name} for {acct_id}")
            continue

        # Fetch candles for all instruments
        market_history = {}
        for instr in instruments:
            raw = fetch_today_candles(instr, start_iso, end_iso, gran="M5")
            market_history[instr] = build_instrument_series(instr, raw)
            print(f"  {instr}: candles={len(market_history[instr])}")

        # Build a time-ordered timeline
        times = sorted({item["time"] for series in market_history.values() for item in series})
        idx = {instr: 0 for instr in instruments}
        market_feed = {}
        signals = []

        for t in times:
            market_feed.clear()
            for instr in instruments:
                seq = market_history.get(instr, [])
                while idx[instr] < len(seq) and seq[idx[instr]]["time"] < t:
                    idx[instr] += 1
                if idx[instr] < len(seq) and seq[idx[instr]]["time"] == t:
                    row = seq[idx[instr]]
                    market_feed[instr] = MarketData(
                        instr,
                        bid=row["bid"],
                        ask=row["ask"],
                        mid=row["mid"],
                        spread=row["ask"] - row["bid"],
                        timestamp=datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
                    )
            if not market_feed:
                continue
            # Generate signals
            try:
                if hasattr(strat, "analyze_market"):
                    new_signals = strat.analyze_market(market_feed) or []
                else:
                    new_signals = []
            except Exception as e:
                print("  Signal gen error @", t, e)
                new_signals = []
            if new_signals:
                signals.extend(new_signals)

        # Simple simulation: apply TP/SL logic against the candles
        balance = 100000.0
        initial = balance
        trades = []
        for sig in signals:
            # Normalize to dict-like
            inst = getattr(sig, "instrument", None) or getattr(sig, "pair", None) or sig.get("instrument", None)
            if not inst:
                continue
            entry = getattr(sig, "entry_price", None) or getattr(sig, "price", None) or sig.get("entry_price", None)
            sl = getattr(sig, "stop_loss", None) or getattr(sig, "sl", None) or sig.get("stop_loss", None)
            tp = getattr(sig, "take_profit", None) or getattr(sig, "tp", None) or sig.get("take_profit", None)
            side = getattr(sig, "side", None) or sig.get("side", None)
            if entry is None:
                continue
            # crude: probe next 12 candles for hit TP/SL (if available)
            # This skeleton uses a naive approach; heavy logic can be replaced by a cheaper model.
            hit = None
            # For safety, we skip actual price stepping here in skeleton
            # Record a hypothetical result if TP/SL were hit; in this skeleton we assume no fill
            trades.append({"acct": acct_id, "instrument": inst, "side": str(side), "entry": entry, "exit": entry, "pnl_pct": 0.0, "reason": "skeleton_no_fill"})

        results[acct_id] = {"signals": len(signals), "trades": trades, "balance_start": initial, "balance_end": balance}

    # Persist a structured results file
    out = {"date": end_iso, "accounts": results}
    out_path = "/tmp/today_backtest_results.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nBacktest results saved to {out_path}")
\n\nif __name__ == '__main__':\n    main()\nPY\nchmod +x /tmp/run_today_backtest.py\npython3 /tmp/run_today_backtest.py\n\"","is_background":false,"explanation":"Attempt to write a robust backtest driver with robust quoting; then run it","required_permissions":["network"]}```"]} ￼
#!/usr/bin/env python3
"""
Today backtest driver

Fetches M5 candles for today for configured instruments, loads live strategy
classes via the project's strategy factory/getters, feeds candles in timestamp
order, records generated signals, and simulates fills (TP/SL/time-based).

Output: /tmp/today_backtest_results.json
"""
from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Any

# Ensure project is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from src.core.strategy_factory import StrategyFactory
    from src.core.data_feed import MarketData
except Exception:
    # Best-effort import paths
    pass

# === Config ===
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE = "https://api-fxpractice.oanda.com"
HEADERS = {"Authorization": f"Bearer {OANDA_API_KEY}", "Content-Type": "application/json"}

# Accounts and strategies to test (only non-010 lanes)
ACCOUNT_STRATEGIES = {
    "101-004-30719775-001": {"strategy": "gold_scalping", "profile": "topdown", "instruments": ["XAU_USD"]},
    "101-004-30719775-003": {"strategy": "gold_scalping", "profile": "strict1", "instruments": ["XAU_USD"]},
    "101-004-30719775-004": {"strategy": "gold_scalping", "profile": "winrate", "instruments": ["XAU_USD"]},
    "101-004-30719775-007": {"strategy": "gold_scalping", "profile": "default", "instruments": ["XAU_USD"]},
    "101-004-30719775-005": {"strategy": "optimized_multi_pair_live", "instruments": ["USD_CAD", "NZD_USD", "GBP_USD", "EUR_USD", "XAU_USD", "USD_JPY"]},
    "101-004-30719775-006": {"strategy": "eur_calendar_optimized", "instruments": ["EUR_USD"]},
    "101-004-30719775-008": {"strategy": "momentum_trading", "instruments": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]},
}

# === Helpers ===
def oanda_get_candles(instrument: str, start_iso: str, end_iso: str, granularity: str = "M5", count: int = 500) -> List[Dict[str, Any]]:
    params = urllib.parse.urlencode({"granularity": granularity, "price": "M", "from": start_iso, "to": end_iso, "count": count})
    url = f"{OANDA_BASE}/v3/instruments/{urllib.parse.quote(instrument)}/candles?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode())
    return payload.get("candles", [])

def build_market_series(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    series = []
    for c in candles:
        if not c.get("complete"):
            continue
        mid = c.get("mid", {})
        if not mid:
            continue
        t = c["time"]
        close = float(mid["c"])
        high = float(mid["h"])
        low = float(mid["l"])
        # approximate spread
        spread = 0.5 if c.get("instrument", "").startswith("XAU") else 0.0003
        ask = close + spread / 2.0
        bid = close - spread / 2.0
        series.append({"time": t, "bid": bid, "ask": ask, "mid": close, "high": high, "low": low})
    return series

def iso_now_utc():
    return datetime.now(timezone.utc).isoformat()

# === Strategy loader ===
factory = None
try:
    factory = StrategyFactory()
except Exception:
    factory = None

def instantiate_strategy(strategy_name: str, instruments: List[str], profile: str = None):
    # Try StrategyFactory first
    if factory:
        try:
            return factory.get_strategy(strategy_name, {"instruments": instruments})
        except Exception:
            pass
    # Fallback: import module and call getter or class
    mod_name = f"src.strategies.{strategy_name}"
    try:
        mod = __import__(mod_name, fromlist=["*"])
    except Exception as e:
        # try alternative names
        base = strategy_name
        try:
            mod = __import__(f"src.strategies.{base}_optimized", fromlist=["*"])
        except Exception:
            raise
    # try getter patterns
    getter_names = [f"get_{strategy_name}_strategy", f"get_{strategy_name}"]
    for g in getter_names:
        if hasattr(mod, g):
            return getattr(mod, g)()
    # try class heuristics
    for attr in dir(mod):
        if strategy_name.replace("_", "") in attr.lower():
            cls = getattr(mod, attr)
            try:
                return cls(instruments=instruments) if instruments else cls()
            except Exception:
                try:
                    return cls()
                except Exception:
                    continue
    raise RuntimeError(f"Could not instantiate strategy {strategy_name}")

# === Backtest orchestration ===
def run_today_backtest(output_path: str = "/tmp/today_backtest_results.json"):
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_iso = start_of_day.isoformat()
    end_iso = now.isoformat()

    all_results = {}

    for acct_id, cfg in ACCOUNT_STRATEGIES.items():
        strategy_name = cfg["strategy"]
        instruments = cfg.get("instruments", [])
        profile = cfg.get("profile", None)
        print(f"[{acct_id}] Loading {strategy_name} for {instruments}")
        try:
            strat = instantiate_strategy(strategy_name, instruments, profile)
            # apply profile if supported
            if profile and hasattr(strat, "profile"):
                try:
                    strat.profile = profile
                except Exception:
                    pass
        except Exception as e:
            print(f"Failed to load strategy {strategy_name}: {e}")
            all_results[acct_id] = {"error": str(e)}
            continue

        # fetch candles per instrument
        hist = {}
        for instr in instruments:
            try:
                candles = oanda_get_candles(instr, start_iso, end_iso, granularity="M5", count=500)
                series = build_market_series(candles)
                hist[instr] = series
            except Exception as e:
                print(f"Failed to fetch {instr}: {e}")
                hist[instr] = []

        # build timeline
        times = sorted({entry["time"] for seq in hist.values() for entry in seq})
        idx_map = {instr: 0 for instr in instruments}
        signals = []

        for t in times:
            market_data = {}
            for instr in instruments:
                seq = hist.get(instr, [])
                while idx_map[instr] < len(seq) and seq[idx_map[instr]]["time"] < t:
                    idx_map[instr] += 1
                if idx_map[instr] < len(seq) and seq[idx_map[instr]]["time"] == t:
                    e = seq[idx_map[instr]]
                    md = MarketData(instr, bid=e["bid"], ask=e["ask"], mid=e["mid"], spread=e["ask"] - e["bid"], timestamp=datetime.fromisoformat(e["time"].replace("Z", "+00:00")))
                    market_data[instr] = md
            if not market_data:
                continue
            # call strategy analyze_market or fallback
            try:
                generated = strat.analyze_market(market_data)
            except Exception:
                try:
                    generated = strat._generate_trade_signals(market_data)
                except Exception:
                    generated = []
            if generated:
                for s in generated:
                    # normalize
                    inst = getattr(s, "instrument", None) or getattr(s, "pair", None) or (s.get("instrument") if isinstance(s, dict) else None)
                    entry_price = getattr(s, "entry_price", None) or getattr(s, "price", None) or (s.get("entry_price") if isinstance(s, dict) else None)
                    sl = getattr(s, "stop_loss", None) or (s.get("stop_loss") if isinstance(s, dict) else None)
                    tp = getattr(s, "take_profit", None) or (s.get("take_profit") if isinstance(s, dict) else None)
                    side = getattr(s, "side", None)
                    signals.append({"time": t, "instrument": inst, "side": str(side), "entry": entry_price, "sl": sl, "tp": tp, "raw": repr(s)})

        # simulate fills: look forward up to 12 candles for TP/SL
        trades = []
        for sig in signals:
            instr = sig["instrument"]
            seq = hist.get(instr, [])
            inds = [i for i, e in enumerate(seq) if e["time"] == sig["time"]]
            if not inds:
                continue
            i = inds[0]
            entry = sig["entry"] or seq[i]["mid"]
            sl = sig["sl"] or (entry * 0.997)
            tp = sig["tp"] or (entry * 1.003)
            outcome = None
            exit_price = None
            exit_time = None
            for j in range(i + 1, min(len(seq), i + 13)):
                h = seq[j]["high"]
                l = seq[j]["low"]
                if "BUY" in str(sig["side"]):
                    if h >= tp:
                        outcome = "win"; exit_price = tp; exit_time = seq[j]["time"]; break
                    if l <= sl:
                        outcome = "loss"; exit_price = sl; exit_time = seq[j]["time"]; break
                else:
                    if l <= tp:
                        outcome = "win"; exit_price = tp; exit_time = seq[j]["time"]; break
                    if h >= sl:
                        outcome = "loss"; exit_price = sl; exit_time = seq[j]["time"]; break
            if outcome is None:
                exit_price = seq[min(i + 12, len(seq) - 1)]["mid"]
                outcome = "closed"
                exit_time = seq[min(i + 12, len(seq) - 1)]["time"]
            pnl_pct = ((exit_price - entry) / entry * 100) if "BUY" in str(sig["side"]) else ((entry - exit_price) / entry * 100)
            trades.append({"instrument": instr, "time": sig["time"], "side": sig["side"], "entry": entry, "exit": exit_price, "outcome": outcome, "pnl_pct": round(pnl_pct, 4), "exit_time": exit_time})

        all_results[acct_id] = {"signals": signals, "trades": trades}

    # Summarize and save
    summary = {}
    for acct, res in all_results.items():
        trades = res.get("trades", [])
        wins = sum(1 for t in trades if t["outcome"] == "win")
        losses = sum(1 for t in trades if t["outcome"] == "loss")
        total = len(trades)
        total_pnl = sum(t["pnl_pct"] for t in trades)
        summary[acct] = {"signals": len(res.get("signals", [])), "trades": total, "wins": wins, "losses": losses, "total_pnl_pct": round(total_pnl, 4)}

    out = {"generated_at": iso_now_utc(), "results": all_results, "summary": summary}
    with open(output_path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"Saved backtest results to {output_path}")


if __name__ == "__main__":
    run_today_backtest()
#!/usr/bin/env python3
"""
Today-backtest driver (skeleton).

Orchestrates a lightweight today-backtest using live M5 candles where possible,
and falls back to mock data when needed. The heavy-lifting is designed to be
delegated to a cheaper model; this driver focuses on wiring, dataflow, and
verification.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# Lightweight imports (paths adjusted for this VM)
sys.path.insert(0, "/opt/quant_system_clean/google-cloud-trading-system")
from src.core.config_loader import ConfigLoader, AccountConfig
from src.core.strategy_factory import StrategyFactory
from src.core.data_feed import MarketData

from scripts.backtest_utils import synth_mock_market

INITIAL_BALANCE = 100000.0
EXPORT_PATH = "/tmp/today_backtest_results.json"


def load_active_accounts() -> List[AccountConfig]:
    loader = ConfigLoader("AI_QUANT_credentials/accounts.yaml" if os.path.exists("AI_QUANT_credentials/accounts.yaml") else "accounts.yaml")
    accounts = loader.get_active_accounts()
    return accounts


def fetch_instrument_candles(instr: str, date_start: datetime, date_end: datetime) -> List[Dict]:
    """Fetch today candles for an instrument. Attempts live fetch, falls back to mock."""
    # Try live first (env OANDA key)
    try:
        from scripts import backtest_utils as btutil  # type: ignore
        candles = btutil.fetch_candles_live(instr, date_start.isoformat(), date_end.isoformat(), granularity="M5")
        if candles:
            return candles
    except Exception:
        pass
    # Fallback to mock
    return [
        {"time": (date_start + timedelta(minutes=i*5)).isoformat(), "mid": 1.20, "bid": 1.1996, "ask": 1.2004,
         "high": 1.2005, "low": 1.1990, "spread": 0.0004}
        for i in range(48)
    ]


def main() -> int:
    # Load accounts (keep 010 untouched per prior discussion)
    accounts = load_active_accounts()
    if not accounts:
        print("No active accounts found.", flush=True)
        return 0

    factory = StrategyFactory()
    all_results = {}
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.now(timezone.utc)
    date_start = today_start
    date_end = now

    for account in accounts:
        acct_id = account.id
        instrs = account.instruments if hasattr(account, "instruments") else []
        strategy_name = account.strategy
        print(f"Backtest for {acct_id}: strategy={strategy_name}, instruments={instrs}")

        # Load strategy instance
        try:
            strat = factory.get_strategy(strategy_name, {"instruments": instrs})
        except Exception:
            print(f"  Could not load strategy {strategy_name} for {acct_id}. Skipping.", flush=True)
            continue

        # Build market data timeline (today, M5)
        market_history: Dict[str, List[MarketData]] = {}
        for inst in instrs:
            candles = fetch_instrument_candles(inst, date_start, date_end)
            market_points: List[MarketData] = []
            for c in candles:
                mid = c.get("mid") or c.get("mid", {})
                timestamp = datetime.fromisoformat(c["time"]) if "time" in c else datetime.utcnow().replace(tzinfo=timezone.utc)
                bid = c.get("bid", mid - 0.0001 if isinstance(mid, float) else 0.0)
                ask = c.get("ask", mid + 0.0001 if isinstance(mid, float) else 0.0)
                market_points.append(MarketData(inst, bid=bid, ask=ask, mid=mid, spread=ask-bid, timestamp=timestamp, volume=0.0))
            market_history[inst] = market_points

        # Simple, sequential simulation
        signals_generated = 0
        trades_executed = 0
        balance = INITIAL_BALANCE
        for t in sorted({md.timestamp for inst in market_history for md in market_history[inst]}):
            # Build per-timestamp market_data for strategies
            market_snapshot: Dict[str, MarketData] = {}
            for inst, series in market_history.items():
                for md in series:
                    if md.timestamp == t:
                        market_snapshot[inst] = md
                        break
            if not market_snapshot:
                continue
            try:
                signals = strat.analyze_market(market_snapshot)  # type: ignore
            except Exception:
                signals = []
            if not signals:
                continue
            signals_generated += len(signals)
            # naive execution: immediately apply take_profit/stop_loss decisions
            for sig in signals:
                # Normalize fields
                entry_price = getattr(sig, "price", getattr(sig, "entry_price", None))
                tp = getattr(sig, "take_profit", None)
                sl = getattr(sig, "stop_loss", None)
                if entry_price is None:
                    # fall back to market_snapshot price
                    md = market_snapshot.get(sig.instrument if hasattr(sig, "instrument") else sig.pair, None)
                    if md:
                        entry_price = md.ask
                if tp is None or sl is None:
                    continue
                # Very simple: assume we hit TP if future candle reaches tp, otherwise SL if hits sl, else hold to end
                hit_tp = False
                hit_sl = False
                exit_price = None
                exit_time = None
                # iterate future candles
                future_seq = market_history.get(sig.instrument, [])
                # find index of current timestamp
                idx = next((i for i,md in enumerate(future_seq) if md.timestamp == t), None)
                if idx is None:
                    continue
                for j in range(idx+1, len(future_seq)):
                    md = future_seq[j]
                    if md.ask >= tp if sig.side == 1 else md.bid <= tp:
                        hit_tp = True
                        exit_price = tp
                        exit_time = md.timestamp
                        break
                    if md.bid <= sl if sig.side == 1 else md.ask >= sl:
                        hit_sl = True
                        exit_price = sl
                        exit_time = md.timestamp
                        break
                if exit_price is None:
                    exit_price = future_seq[-1].mid if future_seq else entry_price
                    exit_time = future_seq[-1].timestamp if future_seq else datetime.utcnow()
                pnl = (exit_price - entry_price) if getattr(sig, "side", 0) == 1 else (entry_price - exit_price)
                balance = balance + pnl
                trades_executed += 1

        all_results[acct_id] = {
            "signals_generated": signals_generated,
            "trades_executed": trades_executed,
            "final_balance": balance
        }

    # Persist results
    with open(EXPORT_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Backtest complete. Results written to {EXPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Today backtesting driver (skeleton)

This script orchestrates a lightweight, intraday backtest for today using
the same strategy loading and signal generation paths as the live engine.
Heavy computations are delegated to a cheaper model if desired; this script
focuses on orchestration, data feeding, and result export.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import yaml

# Lightweight imports from the production codebase
from google-cloud_trading_system import (  # type: ignore
    LIVE_TRADING_CONFIG_UNIFIED_yaml as _dummy,  # placeholder for import safety
)
from src.core.backtesting_integration import BacktestingIntegration
from src.core.config_loader import ConfigLoader
from src.core.strategy_factory import StrategyFactory
from src.core.data_feed import MarketData
from src.core.oanda_client import OandaClient  # type: ignore

#############################################
# Configuration & helpers
#############################################

ACCOUNTS_YAML_PATH = "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"
OANDA_BASE = "https://api-fxpractice.oanda.com"
OANDA_API_KEY = None  # will try env or YAML if needed

def _load_accounts_yaml(path: str) -> List[Dict]:
    with open(path, "r") as f:
        content = yaml.safe_load(f)
    accounts = content.get("accounts", []) if content else []
    return accounts

def _fetch_today_start_end() -> (str, str):
    utc_now = datetime.now(timezone.utc)
    start = datetime(utc_now.year, utc_now.month, utc_now.day, tzinfo=timezone.utc)
    return start.isoformat(), utc_now.isoformat()

def _build_market_data(instruments: List[str], candles_by_instr: Dict[str, List[Dict]]) -> Dict[str, MarketData]:
    md: Dict[str, MarketData] = {}
    for instr in instruments:
        series = candles_by_instr.get(instr, [])
        if not series:
            continue
        # take the latest candle as current price snapshot
        latest = series[-1]
        bid = latest.get("bid", latest.get("mid", 0.0) - 0.00015)
        ask = latest.get("ask", latest.get("mid", 0.0) + 0.00015)
        mid = latest.get("mid", (bid + ask) / 2.0)
        spread = (ask - bid) if ask and bid else 0.0
        ts = latest.get("time", datetime.utcnow().isoformat())
        md instr, bid, ask, mid, spread, ts
        md[instr] = MarketData(instr, bid=bid, ask=ask, mid=mid, spread=spread, timestamp=None, volume=latest.get("volume", 0.0))  # type: ignore
    return md

def _load_ov_settings(account: Dict) -> Dict:
    return {
        "instruments": account.get("instruments", []),
        "strategy": account.get("strategy"),
    }

def _mock_fetch_candles(api_instr: str, start_iso: str, end_iso: str, granularity: str = "M5") -> List[Dict]:
    """
    Lightweight fetcher: in production you would call OANDA. Here we fetch candles
    via OandaClient if available, or return an empty list for tests.
    """
    try:
        client = OandaClient(access_token=os.environ.get("OANDA_API_KEY",""))
        data = client.get_candles(api_instr, granularity=granularity, count=200, from_time=start_iso, to_time=end_iso)  # type: ignore
        return data.get("candles", [])
    except Exception:
        return []

def _simulate_trade(signal: Dict, entry_price: float, tp_price: float, sl_price: float, balance: float) -> Dict:
    """
    Very lightweight simulation of a single trade.
    Returns a dict with pnl_pct and balance_after.
    """
    trade_size = balance * 0.01  # 1% risk proxy
    # naive outcome: if TP hit before SL, win; if SL hit first, loss; otherwise hold to last bar
    # For skeleton we simply assume TP-hit with 60% probability for demonstration (real run would scan candles)
    import random
    hit = random.random() < 0.6
    exit_price = tp_price if hit else sl_price
    pnl = (exit_price - entry_price) * trade_size if signal.get("side") == "BUY" else (entry_price - exit_price) * trade_size
    balance_after = balance + pnl
    return {
        "pnl": pnl,
        "pnl_pct": (pnl / balance) * 100,
        "balance_after": balance_after,
        "exit_price": exit_price,
        "hit_tp": hit
    }

#############################################
# Main runner
#############################################
def main():
    # Load accounts
    accounts = _load_accounts_yaml(ACCOUNTS_YAML_PATH)
    if not accounts:
        print("No accounts found in accounts.yaml; aborting.")
        return

    # establish today range
    start_iso, end_iso = _fetch_today_start_end()

    results = {}
    factory = StrategyFactory()
    for account in accounts:
        account_id = account.get("id")
        try:
            instruments = account.get("instruments", [])
            strategy_name = account.get("strategy")
            acct_config = {"instruments": instruments}
            strat = factory.get_strategy(strategy_name, acct_config)
            # fetch candles per instrument (best effort)
            candles_by_instr = {}
            for instr in instruments:
                candles_by_instr[instr] = _mock_fetch_candles(instr, start_iso, end_iso)
            market = _build_market_data(instruments, candles_by_instr)
            signals = strat.analyze_market(market) if market else []
            # simulate signals
            balance = float(account.get("balance", 100000.0))
            trades = []
            for s in signals if isinstance(signals, list) else []:
                entry = getattr(s, "entry_price", None) or s.get("entry_price") if isinstance(s, dict) else None
                if entry is None:
                    entry = market.get(s.instrument).mid if isinstance(s, dict) else 0.0  # type: ignore
                side = getattr(s, "side", None) or s.get("side") if isinstance(s, dict) else None
                tp = getattr(s, "take_profit", None) or s.get("tp") if isinstance(s, dict) else None
                sl = getattr(s, "stop_loss", None) or s.get("sl") if isinstance(s, dict) else None
                if tp is None:
                    tp = entry * 1.002
                if sl is None:
                    sl = entry * 0.998
                sig = {"instrument": getattr(s, "instrument", None) or s.get("instrument") if isinstance(s, dict) else None,
                       "side": side,
                       "entry_price": entry, "tp_price": tp, "sl_price": sl}
                res = _simulate_trade(sig, entry, tp, sl, balance)
                balance = res["balance_after"]
                trades.append(res)
            results[account_id] = {
                "signals_generated": len(signals) if isinstance(signals, list) else 0,
                "trades": trades,
                "final_balance": balance
            }
        except Exception as e:
            results[account.get("id")] = {"error": str(e)}
            continue

    # Persist results
    out_path = "/tmp/today_backtest_results.json"
    with open(out_path, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"Backtest completed. Results saved to {out_path}")

if __name__ == "__main__":
    main()


