"""
W24 strategy research — fetch missing instrument candles into C:/FXG/backtest_cache.

Reuses the existing canonical ranged fetcher (oanda_mid_historical_fetch) — no
parallel downloader (FXG universal-fix rule). Writes NEW files only, suffix
"_research", never touching existing cache files.

Usage: set OANDA_API_KEY in env, then
  python scripts/local_research/w24_fetch_research_candles.py
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oanda_mid_historical_fetch import fetch_oanda_mid_candles_range

CACHE = Path("C:/FXG/backtest_cache")
INSTRUMENTS = ["USD_JPY", "XAU_USD"]
GRANULARITIES = ["M15", "H1"]
T_FROM = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)
T_TO = datetime(2026, 6, 10, 0, 0, tzinfo=timezone.utc)


def main() -> int:
    if not os.getenv("OANDA_API_KEY"):
        print("ERROR: OANDA_API_KEY not set")
        return 1
    for inst in INSTRUMENTS:
        for gran in GRANULARITIES:
            out = CACHE / f"{inst}_{gran}_research.csv"
            if out.exists():
                print(f"SKIP {out.name} (exists)")
                continue
            print(f"FETCH {inst} {gran} {T_FROM.date()} -> {T_TO.date()} ...")
            candles = fetch_oanda_mid_candles_range(inst, gran, T_FROM, T_TO)
            with out.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["time", "o", "h", "l", "c", "volume"])
                for c in candles:
                    w.writerow([c["time"], c["o"], c["h"], c["l"], c["c"], c["volume"]])
            print(f"  wrote {len(candles)} rows -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
