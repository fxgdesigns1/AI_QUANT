#!/usr/bin/env python3
"""
Debug: See actual momentum values the strategy is seeing
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.strategies.momentum_trading import get_momentum_trading_strategy
import numpy as np

print("🔍 DEBUGGING MOMENTUM VALUES")
print("="*80)

# Get data
fetcher = get_historical_fetcher()
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']

print("📥 Fetching 96 hours...\n")
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=96)

# Load strategy
strategy = get_momentum_trading_strategy()

print("Strategy Settings:")
print(f"  min_momentum: {strategy.min_momentum} ({strategy.min_momentum*100:.2f}%)")
print(f"  momentum_period: {strategy.momentum_period} bars ({strategy.momentum_period*15} minutes)")
print()

for instrument in instruments:
    if instrument not in historical_data or not historical_data[instrument]:
        continue
    
    candles = historical_data[instrument]
    closes = [c['close'] for c in candles]
    
    print(f"{instrument}:")
    print(f"  Total candles: {len(closes)}")
    print(f"  Price range: {min(closes):.5f} - {max(closes):.5f}")
    
    # Calculate momentum at different points
    momentum_values = []
    passing_moments = []
    
    for i in range(strategy.momentum_period, len(closes)):
        lookback_prices = closes[i-strategy.momentum_period:i]
        momentum = (lookback_prices[-1] - lookback_prices[0]) / lookback_prices[0]
        momentum_values.append(momentum)
        
        if abs(momentum) >= strategy.min_momentum:
            passing_moments.append((i, momentum))
    
    if momentum_values:
        print(f"  Momentum over {strategy.momentum_period} bars:")
        print(f"    Min: {min(momentum_values)*100:.3f}%")
        print(f"    Max: {max(momentum_values)*100:.3f}%")
        print(f"    Avg: {np.mean([abs(m) for m in momentum_values])*100:.3f}%")
        print(f"    Moments passing threshold (>{strategy.min_momentum*100:.2f}%): {len(passing_moments)}/{len(momentum_values)}")
        
        if passing_moments:
            print(f"    Best momentum: {max(passing_moments, key=lambda x: abs(x[1]))[1]*100:.3f}%")
        else:
            print(f"    ❌ NO moments passed threshold!")
    
    # Now calculate momentum over LONGER periods
    print(f"  Momentum over different timeframes:")
    
    # 1 hour (4 bars)
    if len(closes) >= 4:
        mom_1h = (closes[-1] - closes[-4]) / closes[-4]
        print(f"    1 hour (4 bars): {mom_1h*100:.3f}%")
    
    # 4 hours (16 bars)
    if len(closes) >= 16:
        mom_4h = (closes[-1] - closes[-16]) / closes[-16]
        print(f"    4 hours (16 bars): {mom_4h*100:.3f}%")
    
    # 24 hours (96 bars)
    if len(closes) >= 96:
        mom_24h = (closes[-1] - closes[-96]) / closes[-96]
        print(f"    24 hours (96 bars): {mom_24h*100:.3f}%")
    
    # Full week
    mom_week = (closes[-1] - closes[0]) / closes[0]
    print(f"    Full week: {mom_week*100:.3f}% ← THIS IS WHAT YOU SEE!")
    
    print()

print("="*80)
print("DIAGNOSIS:")
print("-"*80)
print("Strategy looks at 3.5-hour momentum (14 × 15min bars)")
print("But weekly candle shows CUMULATIVE move over 4 DAYS!")
print()
print("Solutions:")
print("1. Lower min_momentum to catch smaller 3.5h moves")
print("2. Increase momentum_period to look at longer timeframes")
print("3. Use multiple timeframe momentum (M15 + H1 + H4)")
print("="*80)


















