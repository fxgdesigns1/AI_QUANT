#!/usr/bin/env python3
"""
fxg_research_backtest_v1.py — 2026-06-12 strategy research runner.

NEW FILE. Reuses the canonical engine (C:\\FXG\\backtest_cache\\fxg_lon_momentum_engine.py)
via import — the engine is NOT modified (FXG universal fix rule). Layers on top:
  - per-trade spread/slippage costs (no zero-cost backtests)
  - live position_sizer validation (sub-minimum SL ⇒ trade REJECTED, not resized)
  - effective-risk USD P&L (lot caps reduce risk below $300, matching live)
  - train/test split bookkeeping and per-month P&L

Candidates (grids frozen in FXG_STRATEGY_RESEARCH_2026-06-12.md BEFORE execution):
  A: ny_open_momentum_v1      — canonical engine, window 13:30-14:00 UTC, RR [2,3,4]
  B: xauusd_session_champion_v1 — trend_pullback_v1 logic on XAU_USD, ATR mult [1.0,1.5,2.0] x 2 sessions
  C: best_family_extension_v1 — trend_pullback_v1#11 exact params on GBP_USD, USD_JPY (LON_FLOW)

Canonical order everywhere: filter (window + setup conditions) FIRST, then dedupe.
Same-bar SL/TP ambiguity: SL-first (conservative), matching the canonical engine.

Usage:
  python fxg_research_backtest_v1.py            # full grid run
  python fxg_research_backtest_v1.py --variant <variant_id>   # single variant (reproducibility re-run)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CACHE = Path(r"C:\FXG\backtest_cache")
OUT_DIR = CACHE / "research_20260612"

sys.path.insert(0, str(REPO_ROOT))
from src.core.position_sizer import calculate_lots  # live-ALPHA-synced

# canonical engine, imported (not copied, not modified)
_spec = importlib.util.spec_from_file_location(
    "fxg_lon_momentum_engine", str(CACHE / "fxg_lon_momentum_engine.py"))
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)

RISK_USD = 300.0
TRAIN_END = "2026-04-24"   # signal date <= TRAIN_END -> train; else test (frozen)

# Round-trip costs in price units (frozen; from env audit CHECK 6)
COSTS = {
    "EUR_USD": 0.8 * 0.0001, "GBP_USD": 0.8 * 0.0001,
    "AUD_JPY": 1.2 * 0.01, "NZD_JPY": 1.2 * 0.01, "USD_JPY": 1.2 * 0.01,
    "EUR_AUD": 1.0 * 0.0001, "NZD_USD": 1.0 * 0.0001,
    "XAU_USD": 0.35,
}

# Session windows UTC in minutes (frozen; parity-checked against live)
WINDOWS = {
    "NY_SIGNAL": (13 * 60 + 30, 14 * 60),      # candidate A signal window
    "LON_OPEN": (8 * 60, 9 * 60 + 30),         # candidate B
    "NY_OVERLAP": (13 * 60, 16 * 60),          # candidate B
    "LON_FLOW": (8 * 60 + 30, 10 * 60),        # candidate C (live trend_pullback tuple)
}


def load(inst: str, gran: str) -> list[dict]:
    return engine._read_csv(str(CACHE / f"{inst}_{gran}_canon.csv"))


# ---------------------------------------------------------------------------
# trend_pullback_v1 replication (mirrors /opt/ai-quant/src/strategies/backtested/
# trend_pullback_v1.py exactly: EMA 8/20 bias on M15 window, prev-24h-high pullback
# trigger, ATR(14) stop, LONG only, entry at signal close. entry_step is unused by
# the live file and therefore unused here.)
# ---------------------------------------------------------------------------

def _ema(prices: list[float], period: int) -> float:
    if len(prices) < period:
        return sum(prices) / len(prices)
    mult = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * mult + ema * (1 - mult)
    return ema


def _atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / min(len(trs), period)


def trend_pullback_signals(m15: list[dict], window: tuple[int, int],
                           pullback_pct: float, stop_atr_mult: float,
                           rr: float) -> list[dict]:
    """Canonical order: window filter -> setup conditions -> dedupe (first per day)."""
    w_start, w_end = window
    day_seen: set = set()
    out = []
    for i in range(199, len(m15)):
        bar = m15[i]
        t = bar["time"]
        hour, minute = int(t[11:13]), int(t[14:16])
        hm = hour * 60 + minute
        # 1. window filter
        if not (w_start <= hm < w_end):
            continue
        win = m15[i - 199: i + 1]  # live uses count=200 ending at current bar
        closes = [c["c"] for c in win]
        # 2a. bias filter (EMA 8 > EMA 20 over the 200-bar window, live logic)
        if _ema(closes, 8) <= _ema(closes, 20):
            continue
        # 2b. prev-24h-high pullback trigger (live: window[-96:-48])
        rng = win[-96:-48]
        prev_high = max(c["h"] for c in rng)
        trigger = prev_high * (1.0 - pullback_pct)
        if not (bar["l"] <= trigger <= bar["h"]):
            continue
        # 2c. ATR stop
        atr = _atr(win, 14)
        if atr <= 0:
            continue
        date_str = t[:10]
        # 3. dedupe — first QUALIFYING signal per day
        if date_str in day_seen:
            continue
        day_seen.add(date_str)
        entry = bar["c"]
        risk = stop_atr_mult * atr
        out.append({
            "date": date_str, "time": t, "side": "LONG",
            "entry": entry, "sl": entry - risk, "tp": entry + rr * risk,
            "risk": risk,
        })
    return out


def evaluate_holdbars(signals: list[dict], m15: list[dict], rr: float,
                      max_hold_bars: int) -> list[dict]:
    """SL-first conservative; timeout exits at close after max_hold_bars (live max_hold semantics)."""
    t_index = {row["time"]: i for i, row in enumerate(m15)}
    results = []
    for sig in signals:
        si = t_index.get(sig["time"])
        if si is None:
            continue
        entry, sl, tp, risk = sig["entry"], sig["sl"], sig["tp"], sig["risk"]
        outcome, pnl_r = "TIMEOUT", 0.0
        last_j = min(si + max_hold_bars, len(m15) - 1)
        for j in range(si + 1, last_j + 1):
            bar = m15[j]
            if bar["l"] <= sl:          # SL first (conservative)
                outcome, pnl_r = "LOSS", -1.0
                break
            if bar["h"] >= tp:
                outcome, pnl_r = "WIN", rr
                break
        if outcome == "TIMEOUT":
            pnl_r = (m15[last_j]["c"] - entry) / risk
        results.append({**sig, "outcome": outcome, "pnl_r": round(pnl_r, 4)})
    return results


# ---------------------------------------------------------------------------
# Post-processing: sizer rejection, costs, effective-risk USD
# ---------------------------------------------------------------------------

def apply_sizer_and_costs(results: list[dict], instrument: str) -> list[dict]:
    cost_price = COSTS[instrument]
    out = []
    for r in results:
        sizing = calculate_lots(instrument, r["entry"], r["sl"], RISK_USD)
        if not sizing.valid:
            out.append({**r, "rejected": True, "reject_reason": sizing.rejection_reason,
                        "pnl_r_net": 0.0, "pnl_usd_net": 0.0})
            continue
        risk_eff = min(RISK_USD, sizing.lots * sizing.risk_per_lot)
        cost_r = cost_price / r["risk"]
        pnl_r_net = r["pnl_r"] - cost_r
        out.append({**r, "rejected": False, "lots": sizing.lots,
                    "risk_eff_usd": round(risk_eff, 2),
                    "cost_r": round(cost_r, 4),
                    "pnl_r_net": round(pnl_r_net, 4),
                    "pnl_usd_net": round(pnl_r_net * risk_eff, 2)})
    return out


def metrics(trades: list[dict]) -> dict:
    tr = [t for t in trades if not t["rejected"]]
    n = len(tr)
    if n == 0:
        return {"trades": 0}
    gross_win = sum(t["pnl_usd_net"] for t in tr if t["pnl_usd_net"] > 0)
    gross_loss = -sum(t["pnl_usd_net"] for t in tr if t["pnl_usd_net"] < 0)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    # max drawdown on cumulative USD equity, chronological
    eq, peak, mdd = 0.0, 0.0, 0.0
    for t in sorted(tr, key=lambda x: x["time"]):
        eq += t["pnl_usd_net"]
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    monthly = defaultdict(float)
    for t in tr:
        monthly[t["date"][:7]] += t["pnl_usd_net"]
    return {
        "trades": n,
        "rejected": sum(1 for t in trades if t["rejected"]),
        "wins": sum(1 for t in tr if t["outcome"] == "WIN"),
        "win_rate": round(sum(1 for t in tr if t["outcome"] == "WIN") / n, 3),
        "net_r": round(sum(t["pnl_r_net"] for t in tr), 2),
        "net_usd": round(sum(t["pnl_usd_net"] for t in tr), 2),
        "expectancy_usd": round(sum(t["pnl_usd_net"] for t in tr) / n, 2),
        "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
        "max_dd_usd": round(mdd, 2),
        "monthly_usd": {k: round(v, 2) for k, v in sorted(monthly.items())},
    }


def split(trades: list[dict]) -> tuple[list[dict], list[dict]]:
    train = [t for t in trades if t["date"] <= TRAIN_END]
    test = [t for t in trades if t["date"] > TRAIN_END]
    return train, test


# ---------------------------------------------------------------------------
# Variant runners
# ---------------------------------------------------------------------------

def run_variant(variant_id: str) -> dict:
    """variant_id formats:
       A|<INST>|rr<RR>          e.g. A|EUR_USD|rr3.0
       B|XAU_USD|<SESSION>|atr<MULT>  e.g. B|XAU_USD|LON_OPEN|atr1.5
       C|<INST>                 e.g. C|GBP_USD
    """
    parts = variant_id.split("|")
    cand = parts[0]
    if cand == "A":
        inst, rr = parts[1], float(parts[2][2:])
        m15, h1 = load(inst, "M15"), load(inst, "H1")
        params = {**engine.DEFAULT_PARAMS,
                  "window_start_hm": WINDOWS["NY_SIGNAL"][0],
                  "window_end_hm": WINDOWS["NY_SIGNAL"][1],
                  "rr": rr}
        sigs = engine.generate_signals(m15, h1, params)          # filter -> dedupe canonical
        raw = engine.evaluate(sigs, m15, rr, RISK_USD)
    elif cand == "B":
        inst, session, mult = "XAU_USD", parts[2], float(parts[3][3:])
        m15 = load(inst, "M15")
        sigs = trend_pullback_signals(m15, WINDOWS[session],
                                      pullback_pct=0.0005, stop_atr_mult=mult, rr=3.0)
        raw = evaluate_holdbars(sigs, m15, 3.0, max_hold_bars=48)
    elif cand == "C":
        inst = parts[1]
        m15 = load(inst, "M15")
        sigs = trend_pullback_signals(m15, WINDOWS["LON_FLOW"],
                                      pullback_pct=0.0005, stop_atr_mult=1.25, rr=3.0)
        raw = evaluate_holdbars(sigs, m15, 3.0, max_hold_bars=48)
    else:
        raise ValueError(variant_id)

    trades = apply_sizer_and_costs(raw, inst)
    train, test = split(trades)
    return {
        "variant_id": variant_id,
        "instrument": inst,
        "full": metrics(trades),
        "train": metrics(train),
        "test": metrics(test),
        "trades": trades,
    }


GRID = (
    [f"A|{i}|rr{r}" for i in ("EUR_USD", "USD_JPY", "XAU_USD") for r in (2.0, 3.0, 4.0)]
    + [f"B|XAU_USD|{s}|atr{m}" for s in ("LON_OPEN", "NY_OVERLAP") for m in (1.0, 1.5, 2.0)]
    + ["C|GBP_USD", "C|USD_JPY"]
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", help="single variant id (reproducibility re-run)")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    ids = [args.variant] if args.variant else GRID
    all_out = {}
    for vid in ids:
        res = run_variant(vid)
        all_out[vid] = res
        f = res["full"]; te = res["test"]
        print(f"{vid:32s} full: n={f.get('trades',0):3d} PF={f.get('profit_factor','-'):>7} "
              f"netUSD={f.get('net_usd',0):>10} ddUSD={f.get('max_dd_usd',0):>8} | "
              f"test: n={te.get('trades',0):3d} PF={te.get('profit_factor','-'):>7} "
              f"expUSD={te.get('expectancy_usd',0):>7}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"single_{args.variant.replace('|','_').replace('.','p')}" if args.variant else "grid"
    out_path = OUT_DIR / f"results_{suffix}_{stamp}.json"
    out_path.write_text(json.dumps(all_out, indent=1), encoding="utf-8")
    print(f"\nresults -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
