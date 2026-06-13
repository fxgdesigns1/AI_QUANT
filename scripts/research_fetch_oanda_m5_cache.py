#!/usr/bin/env python3
"""
Fetch OANDA mid M5 candles into ARTIFACTS-style cache files (research-only).
Loads .env from repo root for OANDA_API_KEY / OANDA_ENV (optional).
Paginates using the `to` parameter until --max-bars or no more data.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _base_url() -> str:
    env = (_env("OANDA_ENV", "practice") or "practice").lower()
    if env == "live":
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def _headers() -> Dict[str, str]:
    key = _env("OANDA_API_KEY")
    if not key:
        raise SystemExit("Missing OANDA_API_KEY (set in environment or .env)")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _normalize_candle(c: Dict[str, Any]) -> Dict[str, Any]:
    mid = c.get("mid") or {}
    return {
        "time": str(c.get("time")),
        "complete": bool(c.get("complete", False)),
        "volume": int(c.get("volume") or 0),
        "o": float(mid.get("o") or 0),
        "h": float(mid.get("h") or 0),
        "l": float(mid.get("l") or 0),
        "c": float(mid.get("c") or 0),
    }


def fetch_m5_history(
    instrument: str,
    *,
    max_bars: int,
    page_size: int,
    timeout_s: float,
    sleep_s: float,
) -> List[Dict[str, Any]]:
    url = f"{_base_url()}/v3/instruments/{instrument}/candles"
    merged: List[Dict[str, Any]] = []
    to_param: Optional[str] = None

    while len(merged) < max_bars:
        params: Dict[str, str] = {
            "granularity": "M5",
            "price": "M",
            "count": str(min(page_size, max_bars - len(merged))),
        }
        if to_param:
            params["to"] = to_param

        r = requests.get(url, headers=_headers(), params=params, timeout=timeout_s)
        if r.status_code != 200:
            raise RuntimeError(f"OANDA {instrument} HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        batch = data.get("candles") or []
        if not batch:
            break

        norm = [_normalize_candle(c) for c in batch]
        merged = norm + merged
        to_param = batch[0].get("time")
        if sleep_s > 0:
            time.sleep(sleep_s)

        if len(batch) < int(params["count"]):
            break

    # Chronological ascending; keep the most recent max_bars (current window).
    if len(merged) > max_bars:
        merged = merged[-max_bars:]
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch OANDA M5 candles into backtest cache JSON files.")
    parser.add_argument("--out", type=Path, required=True, help="Cache directory (cleared before write)")
    parser.add_argument(
        "--instruments",
        nargs="+",
        default=["EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD"],
    )
    parser.add_argument("--max-bars", type=int, default=8000, help="Max candles per instrument (approx window)")
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep", type=float, default=0.15, help="Seconds between pagination requests")
    args = parser.parse_args()

    if load_dotenv:
        load_dotenv(REPO_ROOT / ".env")

    out = args.out.expanduser().resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid.uuid4())
    generated = datetime.now(timezone.utc).isoformat()
    env_label = (_env("OANDA_ENV", "practice") or "practice").lower()

    summary: Dict[str, Any] = {
        "schema": "fxg.research.cache_manifest.v1",
        "dataset_id": dataset_id,
        "generated_at_utc": generated,
        "source": f"oanda_{env_label}",
        "granularity": "M5",
        "instruments": list(args.instruments),
        "max_bars_requested": args.max_bars,
        "rows_complete_only": True,
        "instruments_detail": {},
        "parse_errors": 0,
        "monotonic_errors_total": 0,
    }

    total_rows = 0
    mono_total = 0

    for inst in args.instruments:
        raw = fetch_m5_history(
            inst,
            max_bars=args.max_bars,
            page_size=args.page_size,
            timeout_s=args.timeout,
            sleep_s=args.sleep,
        )
        complete_only = [c for c in raw if c.get("complete")]
        mono_err = 0
        prev_t: Optional[str] = None
        for c in complete_only:
            t = c.get("time")
            if prev_t is not None and t <= prev_t:
                mono_err += 1
            prev_t = t
        mono_total += mono_err

        payload = {
            "instrument": inst,
            "granularity": "M5",
            "count": len(complete_only),
            "generated_at": generated,
            "dataset_id": dataset_id,
            "source": summary["source"],
            "coverage_start": complete_only[0]["time"] if complete_only else None,
            "coverage_end": complete_only[-1]["time"] if complete_only else None,
            "candles": complete_only,
        }
        out_file = out / f"{inst}_M5.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        total_rows += len(complete_only)
        summary["instruments_detail"][inst] = {
            "file": str(out_file.name),
            "rows": len(complete_only),
            "coverage_start": payload["coverage_start"],
            "coverage_end": payload["coverage_end"],
            "monotonic_timestamp_errors": mono_err,
        }

    summary["total_candle_rows"] = total_rows
    summary["candle_file_count"] = len(args.instruments)
    summary["monotonic_errors_total"] = mono_total
    summary["ready_for_backtest"] = total_rows > 0 and mono_total == 0
    (out / "cache_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if summary["ready_for_backtest"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
