#!/usr/bin/env python3
"""
Debug: Track EXACTLY why signals are being rejected
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.core.data_feed import MarketData
from datetime import datetime
import numpy as np

print("🔍 DEBUGGING WHY SIGNALS ARE REJECTED")
print("="*80)

# Get data
fetcher = get_historical_fetcher()
instruments = ['XAU_USD']  # Focus on Gold - it had 774 passing moments!

print("📥 Fetching 24 hours of Gold data...\n")
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=24)

# Load strategy
strategy = get_momentum_trading_strategy()

# Reset daily limits for testing
strategy.daily_trade_count = 0
strategy.max_trades_per_day = 100  # Don't let this block us

print(f"Strategy Settings:")
print(f"  min_momentum: {strategy.min_momentum*100:.2f}%")
print(f"  min_adx: {strategy.min_adx}")
print(f"  min_volume: {strategy.min_volume}")
print(f"  min_quality_score: {strategy.min_quality_score}")
print(f"  momentum_period: {strategy.momentum_period} bars")
print()

# Build price history first
instrument = 'XAU_USD'
candles = historical_data[instrument]

# Initialize price history for Gold
if instrument not in strategy.price_history:
    strategy.price_history[instrument] = []

# Feed first 30 candles to build history
for candle in candles[:30]:
    strategy.price_history[instrument].append(candle['close'])

print(f"Processing {len(candles)-30} candles...")
print()

rejection_reasons = {
    'price_history_too_short': 0,
    'momentum_too_weak': 0,
    'adx_too_low': 0,
    'volume_too_low': 0,
    'quality_too_low': 0,
    'passed_all_filters': 0
}

passed_details = []

# Process each candle
for i in range(30, min(len(candles), 130)):  # Check 100 candles
    candle = candles[i]
    
    # Add to price history
    strategy.price_history[instrument].append(candle['close'])
    
    # Get recent prices
    prices = list(strategy.price_history[instrument])
    
    if len(prices) < 30:
        rejection_reasons['price_history_too_short'] += 1
        continue
    
    # Calculate momentum (same as strategy does)
    recent_prices = prices[-strategy.momentum_period:]
    momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
    
    if abs(momentum) < strategy.min_momentum:
        rejection_reasons['momentum_too_weak'] += 1
        continue
    
    # Calculate ATR
    atr = 0
    for j in range(1, min(strategy.momentum_period, len(prices))):
        high_low = abs(prices[-j] - prices[-j-1])
        atr += high_low
    atr = atr / min(strategy.momentum_period, len(prices)-1) if len(prices) > 1 else 0
    
    # Calculate ADX (simplified)
    adx = 0
    if len(prices) >= 14:
        moves = [abs(prices[k] - prices[k-1]) for k in range(-14, 0)]
        adx = (sum(moves) / 14 / prices[-1]) * 10000  # Rough approximation
    
    if adx < strategy.min_adx:
        rejection_reasons['adx_too_low'] += 1
        continue
    
    # Calculate volume score (simplified - we don't have real volume data)
    volume_score = 1.5  # Assume passes
    
    if volume_score < strategy.min_volume:
        rejection_reasons['volume_too_low'] += 1
        continue
    
    # Calculate quality score
    abs_momentum = abs(momentum)
    quality = 0
    
    # ADX
    if adx >= 30:
        quality += 30
    elif adx >= 25:
        quality += 25
    elif adx >= 20:
        quality += 20
    elif adx >= 15:
        quality += 15
    elif adx >= 12:
        quality += 10
    
    # Momentum
    if abs_momentum >= 0.010:
        quality += 30
    elif abs_momentum >= 0.006:
        quality += 25
    elif abs_momentum >= 0.004:
        quality += 20
    elif abs_momentum >= 0.002:
        quality += 10
    
    # Volume
    quality += 15  # Assume passes
    
    if quality < strategy.min_quality_score:
        rejection_reasons['quality_too_low'] += 1
        continue
    
    # PASSED ALL FILTERS!
    rejection_reasons['passed_all_filters'] += 1
    passed_details.append({
        'candle': i,
        'momentum': momentum,
        'adx': adx,
        'quality': quality
    })

print("REJECTION ANALYSIS (100 candles):")
print("-"*80)
for reason, count in rejection_reasons.items():
    pct = (count / 100) * 100
    print(f"  {reason}: {count} ({pct:.0f}%)")

print()
print(f"✅ PASSED ALL FILTERS: {rejection_reasons['passed_all_filters']}")
print()

if passed_details:
    print("Sample of passing setups:")
    for detail in passed_details[:5]:
        print(f"  Candle {detail['candle']}: momentum={detail['momentum']*100:.2f}%, "
              f"ADX={detail['adx']:.1f}, quality={detail['quality']:.0f}")
else:
    print("❌ NO setups passed all filters!")
    print()
    print("Most common rejection:")
    max_reason = max(rejection_reasons.items(), key=lambda x: x[1] if x[0] != 'passed_all_filters' else 0)
    print(f"  → {max_reason[0]}: {max_reason[1]}/{100}")

print()
print("="*80)

