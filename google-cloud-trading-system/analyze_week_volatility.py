#!/usr/bin/env python3
"""
Analyze actual market volatility this past week
See if market was flat or if strategy is just too strict
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
import numpy as np

print("📊 ANALYZING PAST WEEK'S MARKET VOLATILITY")
print("="*80)

fetcher = get_historical_fetcher()
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']

print("📥 Fetching 96 hours of data...\n")
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=96)

for instrument, candles in historical_data.items():
    if not candles:
        continue
    
    # Calculate actual moves
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    
    week_high = max(highs)
    week_low = min(lows)
    start_price = closes[0]
    end_price = closes[-1]
    
    # Calculate metrics
    total_range_pct = ((week_high - week_low) / week_low) * 100
    net_move_pct = ((end_price - start_price) / start_price) * 100
    
    # Calculate average 15-min moves
    moves_15min = []
    for i in range(1, len(closes)):
        move = abs((closes[i] - closes[i-1]) / closes[i-1]) * 100
        moves_15min.append(move)
    
    avg_15min_move = np.mean(moves_15min)
    max_15min_move = max(moves_15min)
    
    # Count significant moves (>0.1%)
    significant_moves = sum(1 for m in moves_15min if m > 0.1)
    
    # Calculate volatility
    volatility = np.std(moves_15min)
    
    print(f"{instrument}:")
    print(f"  Total Range: {total_range_pct:.2f}%")
    print(f"  Net Move: {net_move_pct:+.2f}%")
    print(f"  Avg 15min Move: {avg_15min_move:.3f}%")
    print(f"  Max 15min Move: {max_15min_move:.3f}%")
    print(f"  Significant Moves (>0.1%): {significant_moves}/{len(moves_15min)}")
    print(f"  Volatility (σ): {volatility:.4f}")
    
    # Assessment
    if total_range_pct > 2.0:
        print(f"  📈 HIGH VOLATILITY - many opportunities!")
    elif total_range_pct > 1.0:
        print(f"  📊 MODERATE VOLATILITY - some opportunities")
    else:
        print(f"  📉 LOW VOLATILITY - few opportunities")
    
    print()

print("="*80)
print("CONCLUSION:")
print("-"*80)
print("If most pairs show HIGH/MODERATE volatility but strategy found only 1 trade/day,")
print("then parameters are STILL TOO STRICT.")
print()
print("If most pairs show LOW volatility, then last week was genuinely flat,")
print("and we should test against a more volatile period.")
print("="*80)














