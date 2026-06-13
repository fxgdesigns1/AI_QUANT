"""
OANDA v3 mid-candle historical fetch (read-only HTTP).

Used by Phase 8K local replay and Phase 8K-DATA ALPHA export. No execution/order imports.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

UTC = timezone.utc


def oanda_env_base_url() -> str:
    env = (os.getenv("OANDA_ENV") or "practice").lower()
    if env == "live":
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def oanda_headers_from_env() -> Dict[str, str]:
    key = os.getenv("OANDA_API_KEY")
    if not key:
        raise RuntimeError("Missing OANDA_API_KEY (environment only; do not hard-code)")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _clamp_iso8601_fractional_seconds(s: str) -> str:
    """OANDA returns nanoseconds; Python 3.9 fromisoformat accepts at most 6 fractional digits."""
    m = re.match(r"^(.+T\d{2}:\d{2}:\d{2})(\.\d+)((?:Z)|(?:[+-]\d{2}:\d{2})|(?:[+-]\d{4}))$", s)
    if not m or not m.group(2):
        return s
    frac = m.group(2)  # includes leading dot
    digits = frac[1:]
    if len(digits) <= 6:
        return s
    return f"{m.group(1)}.{digits[:6]}{m.group(3)}"


def parse_time_iso_utc(s: Any) -> Optional[datetime]:
    if s is None or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = _clamp_iso8601_fractional_seconds(s)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def normalize_oanda_mid_candle(c: Dict[str, Any]) -> Dict[str, Any]:
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


def granularity_minutes(granularity: str) -> int:
    g = granularity.upper().strip()
    mapping = {"M5": 5, "M15": 15, "M30": 30, "H1": 60}
    if g in mapping:
        return mapping[g]
    if g.startswith("M") and g[1:].isdigit():
        return int(g[1:])
    if g.startswith("H") and g[1:].isdigit():
        return int(g[1:]) * 60
    return 15


def expected_candle_count_full_clock(lookback_days: int, granularity: str) -> int:
    m = granularity_minutes(granularity)
    return int(lookback_days * 24 * (60 / m))


def estimate_jsonl_raw_bytes(candle_count: int, bytes_per_line: int = 140) -> int:
    """Upper-bound style estimate for uncompressed JSONL (one candle per line)."""
    return int(candle_count * bytes_per_line)


def estimate_gzip_compressed_bytes_heuristic(raw_bytes: int, ratio: float = 0.35) -> int:
    """Heuristic: JSONL of floats often compresses well; ratio = compressed/raw."""
    return int(raw_bytes * ratio)


def fetch_oanda_mid_candles_range(
    instrument: str,
    granularity: str,
    t_from: datetime,
    t_to: datetime,
    *,
    page_size: int = 500,
    timeout_s: float = 45.0,
    sleep_s: float = 0.12,
) -> List[Dict[str, Any]]:
    """Fetch [t_from, t_to] ascending mid candles (paginates with from + count)."""
    url = f"{oanda_env_base_url()}/v3/instruments/{instrument}/candles"
    merged: List[Dict[str, Any]] = []
    cursor_from = t_from.astimezone(UTC)
    end = t_to.astimezone(UTC)
    headers = oanda_headers_from_env()

    while cursor_from < end:
        params: Dict[str, str] = {
            "granularity": granularity,
            "price": "M",
            "from": cursor_from.isoformat().replace("+00:00", "Z"),
            "count": str(page_size),
        }
        r = requests.get(url, headers=headers, params=params, timeout=timeout_s)
        if r.status_code != 200:
            raise RuntimeError(f"OANDA {instrument} HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        batch = data.get("candles") or []
        if not batch:
            break
        norm = [normalize_oanda_mid_candle(c) for c in batch if c.get("complete", True)]
        merged.extend(norm)
        last_t = parse_time_iso_utc(norm[-1]["time"])
        if last_t is None:
            break
        nxt = last_t + timedelta(seconds=1)
        if nxt <= cursor_from:
            break
        cursor_from = nxt
        if last_t >= end:
            break
        if sleep_s > 0:
            time.sleep(sleep_s)
        if len(batch) < page_size:
            break

    merged.sort(key=lambda x: parse_time_iso_utc(x["time"]) or datetime.min.replace(tzinfo=UTC))
    seen = set()
    out: List[Dict[str, Any]] = []
    t0 = t_from.astimezone(UTC)
    t1 = t_to.astimezone(UTC)
    for c in merged:
        t = c.get("time")
        if t in seen:
            continue
        seen.add(str(t))
        ct = parse_time_iso_utc(str(t))
        if ct is not None and t0 <= ct <= t1:
            out.append(c)
    return out
