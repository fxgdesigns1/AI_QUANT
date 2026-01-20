#!/usr/bin/env python3
"""Quick verification script to test 006's relaxed alignment logic"""

import sys
import os
sys.path.append(os.getcwd())

from src.strategies.session_execution_strategy import SessionExecutionStrategy
from src.control_plane.market_data_provider import get_latest_price

print("=== 006 TRADING VERIFICATION ===\n")

strategy = SessionExecutionStrategy()

# Test alignment logic with current outlook
instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]

print("Testing roadmap alignment for 006:")
print("-" * 60)

for symbol in instruments:
    is_aligned, bias, data = strategy._check_roadmap_alignment(symbol)
    daily = data.get("daily_bias", "UNKNOWN")
    weekly = data.get("weekly_bias", "UNKNOWN")
    effective = data.get("effective_bias", "N/A")
    
    status = "✅ ALIGNED" if is_aligned else "❌ BLOCKED"
    print(f"{symbol:10} | {status:12} | Daily: {daily:8} | Weekly: {weekly:8} | Effective: {effective}")
    
    if is_aligned:
        print(f"           → Would trade in {effective} direction (if other filters pass)")

print("\n" + "-" * 60)
print("\nCurrent UTC hour:", __import__("datetime").datetime.now(__import__("datetime").timezone.utc).hour)
print("Session window (6-16 UTC):", 6 <= __import__("datetime").datetime.now(__import__("datetime").timezone.utc).hour < 16)

print("\n=== VERIFICATION COMPLETE ===")
