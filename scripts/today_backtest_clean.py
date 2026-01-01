#!/usr/bin/env python3
from src.core.settings import settings
"""
Clean Today backtest driver

This is a single-file, minimal backtest runner that:
 - fetches today's M5 candles from OANDA for configured instruments
 - loads strategy instances via StrategyFactory or module getters
 - feeds candles in chronological order and calls strategy.analyze_market()
 - records signals and simulates simple TP/SL exits (look-forward up to 12 candles)
 - exports results to /tmp/today_backtest_results.json

This file is kept intentionally small and self-contained for reliable execution.
"""
from __future__ import annotations
import sys, os, json, urllib.request, urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from src.core.strategy_factory import StrategyFactory
    from src.core.data_feed import MarketData
except Exception:
    StrategyFactory = None
    MarketData = None  # type: ignore

OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE = "https://api-fxpractice.oanda.com"
HEADERS = {"Authorization": f"Bearer {OANDA_API_KEY}", "Content-Type": "application/json"}

ACCOUNT_STRATEGIES = {
    "101-004-30719775-001": {"strategy": "gold_scalping", "profile": "topdown", "instruments": ["XAU_USD"]},
    "101-004-30719775-003": {"strategy": "gold_scalping", "profile": "strict1", "instruments": ["XAU_USD"]},
    "101-004-30719775-004": {"strategy": "gold_scalping", "profile": "winrate", "instruments": ["XAU_USD"]},
    "101-004-30719775-007": {"strategy": "gold_scalping", "profile": "default", "instruments": ["XAU_USD"]},
    "101-004-30719775-005": {"strategy": "optimized_multi_pair_live", "instruments": ["USD_CAD", "NZD_USD", "GBP_USD", "EUR_USD", "XAU_USD", "USD_JPY"]},
    "101-004-30719775-006": {"strategy": "eur_calendar_optimized", "instruments": ["EUR_USD"]},
    "101-004-30719775-008": {"strategy": "momentum_trading", "instruments": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]},
}

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
        spread = 0.5 if c.get("instrument", "").startswith("XAU") else 0.0003
        ask = close + spread / 2.0
        bid = close - spread / 2.0
        series.append({"time": t, "bid": bid, "ask": ask, "mid": close, "high": high, "low": low})
    return series

def instantiate_strategy(strategy_name: str, instruments: List[str], profile: str = None):
    # Try StrategyFactory then fallbacks
    try:
        if StrategyFactory:
            factory = StrategyFactory()
            return factory.get_strategy(strategy_name, {"instruments": instruments})
    except Exception:
        pass
    modname = f"src.strategies.{strategy_name}"
    mod = __import__(modname, fromlist=["*"])
    getter = f"get_{strategy_name}_strategy"
    if hasattr(mod, getter):
        return getattr(mod, getter)()
    # class fallback
    for attr in dir(mod):
        if strategy_name.replace("_", "") in attr.lower():
            cls = getattr(mod, attr)
            return cls(instruments=instruments) if instruments else cls()
    raise RuntimeError("strategy load failed")

def run_today_backtest(output_path: str = "/tmp/today_backtest_results.json"):
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_iso, end_iso = start_of_day.isoformat(), now.isoformat()
    results = {}
    for acct, cfg in ACCOUNT_STRATEGIES.items():
        strategy_name = cfg["strategy"]
        instruments = cfg["instruments"]
        try:
            strat = instantiate_strategy(strategy_name, instruments, cfg.get("profile"))
        except Exception as e:
            results[acct] = {"error": str(e)}
            continue
        # fetch candles
        hist = {}
        for instr in instruments:
            try:
                candles = oanda_get_candles(instr, start_iso, end_iso, "M5", 500)
                hist[instr] = build_market_series(candles)
            except Exception as e:
                hist[instr] = []
        # timeline
        times = sorted({entry["time"] for seq in hist.values() for entry in seq})
        idx = {i: 0 for i in instruments}
        signals = []
        for t in times:
            snapshot = {}
            for inst in instruments:
                seq = hist.get(inst, [])
                while idx[inst] < len(seq) and seq[idx[inst]]["time"] < t:
                    idx[inst] += 1
                if idx[inst] < len(seq) and seq[idx[inst]]["time"] == t:
                    e = seq[idx[inst]]
                    md = MarketData(inst, bid=e["bid"], ask=e["ask"], mid=e["mid"], spread=e["ask"]-e["bid"], timestamp=datetime.fromisoformat(e["time"].replace("Z","+00:00")))
                    snapshot[inst] = md
            if not snapshot:
                continue
            try:
                gen = strat.analyze_market(snapshot)
            except Exception:
                gen = []
            if gen:
                for s in gen:
                    inst = getattr(s,"instrument", None) or getattr(s,"pair", None) or (s.get("instrument") if isinstance(s, dict) else None)
                    entry = getattr(s,"entry_price", None) or getattr(s,"price", None) or (s.get("entry_price") if isinstance(s, dict) else None)
                    sl = getattr(s,"stop_loss", None) or (s.get("stop_loss") if isinstance(s, dict) else None)
                    tp = getattr(s,"take_profit", None) or (s.get("take_profit") if isinstance(s, dict) else None)
                    side = getattr(s,"side", None)
                    signals.append({"time": t, "instrument": inst, "side": str(side), "entry": entry, "sl": sl, "tp": tp})
        # simulate simple fills
        trades = []
        for s in signals:
            instr = s["instrument"]
            seq = hist.get(instr, [])
            inds = [i for i,e in enumerate(seq) if e["time"]==s["time"]]
            if not inds:
                continue
            i = inds[0]
            entry = s["entry"] or seq[i]["mid"]
            sl = s["sl"] or entry*0.997
            tp = s["tp"] or entry*1.003
            outcome = None
            exit_price = None
            for j in range(i+1, min(len(seq), i+13)):
                h = seq[j]["high"]; l = seq[j]["low"]
                if "BUY" in s["side"]:
                    if h >= tp:
                        outcome="win"; exit_price=tp; break
                    if l <= sl:
                        outcome="loss"; exit_price=sl; break
                else:
                    if l <= tp:
                        outcome="win"; exit_price=tp; break
                    if h >= sl:
                        outcome="loss"; exit_price=sl; break
            if outcome is None:
                exit_price = seq[min(i+12,len(seq)-1)]["mid"] if seq else entry
                outcome = "closed"
            pnl_pct = ((exit_price-entry)/entry*100) if "BUY" in s["side"] else ((entry-exit_price)/entry*100)
            trades.append({"instrument": instr, "time": s["time"], "side": s["side"], "entry": entry, "exit": exit_price, "outcome": outcome, "pnl_pct": round(pnl_pct,4)})
        results[acct] = {"signals": len(signals), "trades": trades}
    with open("/tmp/today_backtest_results.json","w") as fh:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, fh, indent=2)
    print("Saved /tmp/today_backtest_results.json")

if __name__ == "__main__":
    run_today_backtest()

