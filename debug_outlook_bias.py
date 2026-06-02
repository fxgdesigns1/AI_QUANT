#!/usr/bin/env python3
"""Debug script to check actual price moves vs bias classification"""

import sys
import os
sys.path.append(os.getcwd())

from src.control_plane.outlook_engine import get_outlook_engine
from src.control_plane.market_data_provider import get_candles, get_latest_price

print("=== OUTLOOK BIAS DEBUG ===\n")

engine = get_outlook_engine()

# Check XAU_USD specifically
instrument = "XAU_USD"
print(f"Analyzing {instrument}:\n")

# Get current price
current = get_latest_price(instrument, timeout_s=5.0)
print(f"Current price: {current.mid:.2f}")

# Get daily candles
candles = get_candles(instrument, granularity="D", count=30, timeout_s=10.0)
if len(candles) >= 2:
    # Check last 5 days
    print(f"\nLast 5 days price action:")
    for i in range(max(0, len(candles)-5), len(candles)):
        c = candles[i]
        if i > 0:
            prev = candles[i-1].c
            change = c.c - prev
            change_pct = (change / prev) * 100
            print(f"  Day {i}: {c.c:.2f} ({change_pct:+.2f}%)")
    
    # Current logic check
    lookback = min(5, len(candles) - 1)
    anchor_close = candles[-lookback].c
    price_change = current.mid - anchor_close
    price_change_pct = (price_change / anchor_close) * 100
    
    print(f"\n--- Current Outlook Engine Logic ---")
    print(f"Anchor (5 days ago): {anchor_close:.2f}")
    print(f"Current: {current.mid:.2f}")
    print(f"Change: {price_change:.2f} ({price_change_pct:.2f}%)")
    print(f"\nThreshold check: > 0.5% = BULLISH, < -0.5% = BEARISH, else NEUTRAL")
    print(f"Result: {'BULLISH' if price_change_pct > 0.5 else ('BEARISH' if price_change_pct < -0.5 else 'NEUTRAL')}")
    
    # Check what the actual outlook says
    daily = engine.get_latest("daily")
    if daily:
        for outlook in daily.get("outlooks", []):
            if outlook.get("instrument") == instrument:
                print(f"\nActual outlook bias: {outlook.get('bias')}")
                print(f"Actual confidence: {outlook.get('confidence')}")
                break

print("\n=== DEBUG COMPLETE ===")
