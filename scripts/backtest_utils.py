#!/usr/bin/env python3
"""
Backtest utilities: lightweight helpers to fetch candles (with mock fallback),
build MarketData objects, and run a simple signal-to-trade simulator.

This module is intentionally lightweight so a cheaper model can implement
the heavy lifting later. It provides clear entry points and typings.
"""
from __future__ import annotations
from src.core.settings import settings

import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests

import sys
import os
sys.path.insert(0, "/opt/quant_system_clean/google-cloud-trading-system")
from src.core.data_feed import MarketData

# Simple, deterministic mock candles (used if live fetch is unavailable)
def generate_mock_candles(start_price: float, count: int, interval_minutes: int = 5) -> List[Dict]:
    """Return a list of mock candle dictionaries with times in UTC ascending order."""
    candles = []
    price = start_price
    base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for i in range(count):
        # small random walk
        delta = (random.random() - 0.5) * 0.0008
        mid = max(0.0001, price + delta)
        bid = mid - 0.00004
        ask = mid + 0.00004
        t = base_time + timedelta(minutes=i * interval_minutes)
        candles.append({"time": t.isoformat(), "mid": mid, "bid": bid, "ask": ask, "high": mid * (1 + 0.0005),
                        "low": mid * (1 - 0.0005)})
        price = mid
    return candles

def fetch_candles_live(instrument: str, since_iso: str, end_iso: str, granularity: str = "M5") -> List[Dict]:
    """Fetch candles from OANDA (practice) if available; otherwise raise an exception."""
    api_key = os.environ.get("OANDA_API_KEY", "")
    if not api_key:
        raise RuntimeError("OANDA API key not configured")
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
    params = {
        "granularity": granularity,
        "count": 200,
        "price": "M",
        "from": since_iso,
        "to": end_iso,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("candles", [])

def to_market_data_for_instrument(instr: str, candles: List[Dict]) -> List[MarketData]:
    """Convert candle dicts into MarketData objects for a single instrument."""
    market_points: List[MarketData] = []
    for c in candles:
        mid = c.get("mid", {})
        timestamp = None
        if "time" in c:
            try:
                timestamp = datetime.fromisoformat(c["time"].replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        bid = c.get("bid", mid.get("c", 0.0)) if isinstance(mid, dict) else c.get("bid", 0.0)
        ask = c.get("ask", mid.get("c", 0.0)) if isinstance(mid, dict) else c.get("ask", 0.0)
        if "high" in c and "low" in c:
            high = c["high"]
            low = c["low"]
        else:
            high = mid.get("h", mid if isinstance(mid, float) else 0.0)
            low = mid.get("l", mid if isinstance(mid, float) else 0.0)
        market_points.append(MarketData(instr, bid=bid, ask=ask, mid=mid if isinstance(mid, (int, float)) else None, spread=(ask - bid), timestamp=timestamp, volume=0.0))
    return market_points

def synth_mock_market(instrument: str, candle_count: int = 200) -> List[MarketData]:
    """Return a list of synthetic MarketData objects for an instrument."""
    candles = generate_mock_candles(1.2000, candle_count)
    m = []
    for c in candles:
        m.append(MarketData(
            instrument=instrument,
            bid=c["bid"],
            ask=c["ask"],
            mid=c["mid"],
            spread=c["spread"],
            timestamp=datetime.fromisoformat(c["time"]),
            volume=0.0
        ))
    return m


