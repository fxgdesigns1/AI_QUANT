#!/usr/bin/env python3
"""
W23 Signal Forensics — week of 2-6 June 2026.

Cross-references every signal in logs/signals*.jsonl against the hardcoded
W23 news calendar and reports:
  - Whether the signal fell inside an embargo window (EMBARGO_HIT / CLEAR)
  - Which event caused the hit and what the affected currencies are
  - Whether the signal direction agreed with the event's expected market move
    (WITH_NEWS / AGAINST_NEWS / NEUTRAL)

No API calls — uses the static calendar only.

Usage:
    python scripts/probes/w23_signal_forensics.py
    python scripts/probes/w23_signal_forensics.py --signal-file logs/signals.jsonl
    python scripts/probes/w23_signal_forensics.py --json-out ARTIFACTS/w23_forensics.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Static W23 news calendar  (no API — authoritative for this analysis)
# ---------------------------------------------------------------------------
# Each entry: (datetime_str_utc, embargo_minutes_each_side, affected_currencies,
#              impact, description, usd_direction)
# usd_direction: "BULLISH" | "BEARISH" | "NEUTRAL"
#   BULLISH  → USD strengthens → SELL quote-USD pairs (EUR_USD, GBP_USD, XAU_USD)
#                               → BUY base-USD pairs  (USD_JPY, USD_CAD, USD_CHF)
#   BEARISH  → USD weakens    → BUY quote-USD pairs / SELL base-USD pairs
#   NEUTRAL  → ambiguous / currency-specific, treat as NEUTRAL

_W23_EVENTS_RAW: List[Tuple] = [
    ("2026-06-02 15:00:00", 30, ["USD"],                                                          "MEDIUM",  "ISM Manufacturing PMI",         "NEUTRAL"),
    ("2026-06-04 13:15:00", 30, ["USD"],                                                          "MEDIUM",  "ADP Employment Change",         "NEUTRAL"),
    ("2026-06-05 12:15:00", 45, ["EUR"],                                                          "HIGH",    "ECB Interest Rate Decision",    "NEUTRAL"),
    ("2026-06-05 13:30:00", 30, ["USD"],                                                          "MEDIUM",  "US Initial Jobless Claims",     "NEUTRAL"),
    ("2026-06-06 13:30:00", 60, ["USD","JPY","AUD","GBP","CHF","CAD","NZD"],                     "EXTREME", "NFP - 172k vs 88k expected, massive beat, dollar surge", "BULLISH"),
]


def _parse_w23_calendar():
    events = []
    for raw in _W23_EVENTS_RAW:
        dt_str, embargo_m, currencies, impact, desc, usd_dir = raw
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        events.append({
            "event_utc": dt,
            "embargo_seconds": embargo_m * 60,
            "currencies": [c.upper() for c in currencies],
            "impact": impact,
            "description": desc,
            "usd_direction": usd_dir,
        })
    return events


W23_CALENDAR = _parse_w23_calendar()

# ---------------------------------------------------------------------------
# Instrument → currencies it contains
# ---------------------------------------------------------------------------
_PAIR_CURRENCIES: Dict[str, List[str]] = {
    "EUR_USD": ["EUR", "USD"],
    "GBP_USD": ["GBP", "USD"],
    "XAU_USD": ["XAU", "USD"],
    "USD_JPY": ["USD", "JPY"],
    "USD_CAD": ["USD", "CAD"],
    "USD_CHF": ["USD", "CHF"],
    "AUD_USD": ["AUD", "USD"],
    "NZD_USD": ["NZD", "USD"],
    "EUR_GBP": ["EUR", "GBP"],
    "EUR_JPY": ["EUR", "JPY"],
    "GBP_JPY": ["GBP", "JPY"],
}

# Pairs where USD is the QUOTE currency (price falls when USD strengthens)
_USD_QUOTE_PAIRS = {"EUR_USD", "GBP_USD", "XAU_USD", "AUD_USD", "NZD_USD"}
# Pairs where USD is the BASE currency (price rises when USD strengthens)
_USD_BASE_PAIRS  = {"USD_JPY", "USD_CAD", "USD_CHF"}


def _instrument_currencies(instrument: str) -> List[str]:
    instr = instrument.upper().replace("/", "_").replace("-", "_")
    if instr in _PAIR_CURRENCIES:
        return _PAIR_CURRENCIES[instr]
    # Fallback: split on _ or / and take first two 3-char tokens
    parts = re.split(r"[/_-]", instr)
    return [p for p in parts if len(p) == 3][:2]


def _direction_alignment(instrument: str, side: str, event: Dict[str, Any]) -> str:
    """
    Returns WITH_NEWS | AGAINST_NEWS | NEUTRAL based on whether the signal
    direction agrees with the event's expected USD move.
    """
    usd_dir = event["usd_direction"]
    if usd_dir == "NEUTRAL":
        return "NEUTRAL"
    side = (side or "").upper()
    if side not in ("BUY", "SELL"):
        return "NEUTRAL"

    instr = instrument.upper().replace("/", "_").replace("-", "_")

    if usd_dir == "BULLISH":
        # USD strengthens → SELL on quote-USD pairs is correct; BUY on base-USD pairs is correct
        if instr in _USD_QUOTE_PAIRS:
            return "WITH_NEWS" if side == "SELL" else "AGAINST_NEWS"
        if instr in _USD_BASE_PAIRS:
            return "WITH_NEWS" if side == "BUY"  else "AGAINST_NEWS"
        return "NEUTRAL"

    if usd_dir == "BEARISH":
        if instr in _USD_QUOTE_PAIRS:
            return "WITH_NEWS" if side == "BUY"  else "AGAINST_NEWS"
        if instr in _USD_BASE_PAIRS:
            return "WITH_NEWS" if side == "SELL" else "AGAINST_NEWS"
        return "NEUTRAL"

    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Core cross-reference
# ---------------------------------------------------------------------------

def cross_reference_signal(
    signal_ts_utc: datetime,
    instrument: str,
    side: str,
) -> Dict[str, Any]:
    """
    Returns a dict:
        status        : "EMBARGO_HIT" | "CLEAR"
        hits          : list of matching event dicts (empty when CLEAR)
        direction     : "WITH_NEWS" | "AGAINST_NEWS" | "NEUTRAL" | None
    """
    sig_currencies = set(_instrument_currencies(instrument))
    hits = []

    for ev in W23_CALENDAR:
        ev_ts = ev["event_utc"]
        window = ev["embargo_seconds"]
        diff = abs((signal_ts_utc - ev_ts).total_seconds())
        if diff > window:
            continue
        # Embargo window match — now check currency overlap
        if not sig_currencies.intersection(ev["currencies"]):
            continue
        direction = _direction_alignment(instrument, side, ev)
        hits.append({
            "event": ev["description"],
            "event_utc": ev_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "impact": ev["impact"],
            "embargo_minutes": ev["embargo_seconds"] // 60,
            "seconds_from_event": round((signal_ts_utc - ev_ts).total_seconds()),
            "affected_currencies": ev["currencies"],
            "usd_direction": ev["usd_direction"],
            "signal_direction_alignment": direction,
        })

    if hits:
        # Pick the worst alignment to surface (AGAINST > NEUTRAL > WITH)
        rank = {"AGAINST_NEWS": 2, "NEUTRAL": 1, "WITH_NEWS": 0}
        top = max(hits, key=lambda h: rank.get(h["signal_direction_alignment"], 0))
        return {
            "status": "EMBARGO_HIT",
            "hits": hits,
            "direction": top["signal_direction_alignment"],
        }

    return {"status": "CLEAR", "hits": [], "direction": None}


# ---------------------------------------------------------------------------
# Signal timestamp extraction
# ---------------------------------------------------------------------------

def _parse_signal_ts(signal: Dict[str, Any]) -> Optional[datetime]:
    """Try to extract a UTC datetime from the signal dict."""
    # Look for explicit timestamp fields
    for key in ("timestamp", "ts", "ts_utc", "time", "created_at", "signal_time"):
        v = signal.get(key)
        if not v:
            continue
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        if isinstance(v, str):
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    return datetime.strptime(v.rstrip("Z"), fmt.rstrip("Z")).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    # Fallback: try to parse from signal_id (e.g. trace_20260606135500)
    sid = signal.get("signal_id", "")
    m = re.search(r"(\d{14})", sid)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Load signals from jsonl file(s)
# ---------------------------------------------------------------------------

def load_signals(paths: List[Path]) -> List[Dict[str, Any]]:
    signals = []
    for p in paths:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    signals.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return signals


# ---------------------------------------------------------------------------
# Load signals from backtest CSV
# ---------------------------------------------------------------------------
# Expected columns: strategy, instrument, signal_date, signal_time_utc,
#                   direction, entry_price, stop_loss, take_profit,
#                   outcome, r_achieved

_DIRECTION_MAP = {
    "buy": "BUY", "long": "BUY",
    "sell": "SELL", "short": "SELL",
}

_TIME_FMTS = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]


def _parse_direction(raw: str) -> str:
    return _DIRECTION_MAP.get(raw.strip().lower(), raw.strip().upper())


def _parse_csv_ts(date_str: str, time_str: str) -> Optional[datetime]:
    date_str = date_str.strip()
    time_str = time_str.strip()
    for date_fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        for time_fmt in _TIME_FMTS:
            try:
                return datetime.strptime(
                    f"{date_str} {time_str}", f"{date_fmt} {time_fmt}"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def load_signals_csv(path: Path) -> List[Dict[str, Any]]:
    """Read backtest CSV and return normalised signal dicts compatible with filter_w23()."""
    signals: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):  # row 1 = header
            date_str = row.get("signal_date", "").strip()
            time_str = row.get("signal_time_utc", "").strip()
            ts = _parse_csv_ts(date_str, time_str)
            instrument = row.get("instrument", "").strip()
            side = _parse_direction(row.get("direction", ""))
            signals.append({
                # Fields used by filter_w23 / analyse
                "timestamp":  ts.strftime("%Y-%m-%d %H:%M:%S") if ts else None,
                "instrument": instrument,
                "side":       side,
                "strategy":   row.get("strategy", "").strip(),
                # Pass-through extras for JSON output
                "entry_price": row.get("entry_price", ""),
                "stop_loss":   row.get("stop_loss", ""),
                "take_profit": row.get("take_profit", ""),
                "outcome":     row.get("outcome", ""),
                "r_achieved":  row.get("r_achieved", ""),
                # signal_id not in CSV; use row number as fallback
                "signal_id":  f"csv_row_{i}",
                "_csv_row":   i,
            })
    return signals


# ---------------------------------------------------------------------------
# Filter signals to W23 window
# ---------------------------------------------------------------------------

W23_START = datetime(2026, 6, 2, 0, 0, 0, tzinfo=timezone.utc)
W23_END   = datetime(2026, 6, 6, 23, 59, 59, tzinfo=timezone.utc)


def filter_w23(signals: List[Dict[str, Any]]) -> Tuple[List, List]:
    """Returns (w23_signals, no_ts_signals)."""
    w23, no_ts = [], []
    for s in signals:
        ts = _parse_signal_ts(s)
        if ts is None:
            no_ts.append(s)
            continue
        if W23_START <= ts <= W23_END:
            w23.append((ts, s))
    return w23, no_ts


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyse(
    signal_files: List[Path],
    pre_loaded: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    raw = pre_loaded if pre_loaded is not None else load_signals(signal_files)
    w23_pairs, no_ts = filter_w23(raw)

    results = []
    for ts, sig in sorted(w23_pairs, key=lambda x: x[0]):
        instrument = sig.get("symbol") or sig.get("instrument") or "UNKNOWN"
        side       = sig.get("side") or sig.get("direction") or ""
        xref       = cross_reference_signal(ts, instrument, side)

        results.append({
            "signal_id":   sig.get("signal_id", ""),
            "strategy":    sig.get("strategy", ""),
            "symbol":      instrument,
            "side":        side,
            "signal_ts":   ts.strftime("%Y-%m-%d %H:%M:%S"),
            **xref,
        })

    # Summary stats
    total   = len(results)
    hits    = [r for r in results if r["status"] == "EMBARGO_HIT"]
    against = [r for r in hits if r["direction"] == "AGAINST_NEWS"]
    with_n  = [r for r in hits if r["direction"] == "WITH_NEWS"]
    neutral = [r for r in hits if r["direction"] == "NEUTRAL"]

    summary = {
        "total_w23_signals": total,
        "embargo_hits":      len(hits),
        "hit_rate_pct":      round(100 * len(hits) / max(1, total), 1),
        "against_news":      len(against),
        "with_news":         len(with_n),
        "neutral_hits":      len(neutral),
        "no_timestamp":      len(no_ts),
    }

    return {"summary": summary, "signals": results}


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

def _print_report(data: Dict[str, Any], source: str = "log files") -> None:
    s = data["summary"]
    print("\n=== W23 NEWS EMBARGO FORENSICS ===")
    print(f"  Source              : {source}")
    print(f"  W23 signals found   : {s['total_w23_signals']}")
    print(f"  Embargo hits        : {s['embargo_hits']}  ({s['hit_rate_pct']}%)")
    print(f"    -> Against news   : {s['against_news']}")
    print(f"    -> With news      : {s['with_news']}")
    print(f"    -> Neutral        : {s['neutral_hits']}")
    print(f"  No-timestamp skips  : {s['no_timestamp']}")

    if not data["signals"]:
        print(f"\nNo W23 signals found in {source}.")
        if source == "log files":
            print("(Check that signal_id encodes a timestamp or add a 'timestamp' field.)")
        return

    print("\n--- EMBARGO HITS ---")
    hits = [r for r in data["signals"] if r["status"] == "EMBARGO_HIT"]
    if not hits:
        print("  None")
    for r in hits:
        alignment = r["direction"]
        flag = {"AGAINST_NEWS": "[!] AGAINST", "WITH_NEWS": "[+] WITH", "NEUTRAL": "[~] NEUTRAL"}.get(alignment, alignment)
        print(f"\n  [{r['signal_ts']}] {r['symbol']} {r['side']}  strategy={r['strategy']}")
        print(f"    Status   : EMBARGO_HIT  Direction: {flag}")
        for h in r["hits"]:
            print(f"    Event    : {h['event']}  ({h['impact']})")
            print(f"    Window   : +/-{h['embargo_minutes']}m  |  {h['seconds_from_event']:+.0f}s from event")

    print("\n--- CLEAR SIGNALS ---")
    clears = [r for r in data["signals"] if r["status"] == "CLEAR"]
    if not clears:
        print("  None")
    for r in clears[:10]:
        print(f"  [{r['signal_ts']}] {r['symbol']} {r['side']}  CLEAR")
    if len(clears) > 10:
        print(f"  ... and {len(clears)-10} more CLEAR signals")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_signal_files() -> List[Path]:
    root = Path(__file__).parents[2]
    logs = root / "logs"
    return [
        logs / "signals.jsonl",
        logs / "signals_ftmo_demo2.jsonl",
    ]


def main():
    ap = argparse.ArgumentParser(description="W23 news embargo signal forensics")
    ap.add_argument("--signal-file", nargs="*", help="Path(s) to signal .jsonl files")
    ap.add_argument(
        "--csv",
        metavar="PATH",
        help=(
            "Backtest CSV file (columns: strategy, instrument, signal_date, "
            "signal_time_utc, direction, entry_price, stop_loss, take_profit, "
            "outcome, r_achieved). Takes precedence over --signal-file."
        ),
    )
    ap.add_argument("--json-out", help="Write full JSON report to this path")
    args = ap.parse_args()

    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"ERROR: CSV file not found: {csv_path}")
            sys.exit(1)
        pre_loaded = load_signals_csv(csv_path)
        source = f"CSV ({csv_path.name})"
        data = analyse([], pre_loaded=pre_loaded)
    else:
        files = [Path(f) for f in args.signal_file] if args.signal_file else _default_signal_files()
        source = "log files"
        data = analyse(files)

    _print_report(data, source=source)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        print(f"\nJSON report written -> {out}")


if __name__ == "__main__":
    main()
