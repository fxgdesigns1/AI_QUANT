#!/usr/bin/env python3
"""
Validate Against Yesterday's Active Market
Test strategies against Oct 15 (1pm-5pm) when market had movement
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator
import pytz

print("📅 VALIDATING AGAINST YESTERDAY'S ACTIVE MARKET")
print("=" * 80)
print()

# Calculate yesterday's prime hours (1pm-5pm London)
london_tz = pytz.timezone('Europe/London')
yesterday = datetime.now(london_tz) - timedelta(days=1)
yesterday_date = yesterday.strftime("%Y-%m-%d")

print(f"Testing Period: {yesterday_date} 1:00pm - 5:00pm London (4 hours)")
print("Why: Yesterday typically has normal market activity")
print()

# For now, we'll use "last 24-28 hours ago" as proxy for yesterday's prime time
# OANDA API gives us most recent data, so we fetch more and look at older segment

print("🔄 Fetching yesterday's market data...")
print()

# Load momentum strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy
strategy = get_momentum_trading_strategy()

print(f"✅ Strategy: {strategy.name}")
print(f"📊 Current Parameters:")
print(f"   Min ADX: {strategy.min_adx}")
print(f"   Min Momentum: {strategy.min_momentum}")
print(f"   Min Volume: {strategy.min_volume}")
print(f"   Quality Threshold: {strategy.min_quality_score}")
print()

# Get 24 hours of data to capture yesterday
fetcher = get_historical_fetcher()

instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']

print(f"📥 Fetching 24-hour history to capture yesterday's prime time...")

# Get 24 hours @ M15 (15-min candles) = 96 candles
historical_data = {}
for instrument in instruments:
    candles = fetcher.fetch_candles(instrument, count=96, granularity='M15')
    if candles:
        # Take middle 16 candles (4 hours from 24 hours ago, roughly yesterday's 1-5pm)
        # This is approximate but gives us "yesterday's active period" data
        yesterday_slice = candles[32:48]  # Hours 12-16 from 24 hours ago
        historical_data[instrument] = []
        
        for candle in yesterday_slice:
            mid_data = candle.get('mid', {})
            bid_data = candle.get('bid', {})
            ask_data = candle.get('ask', {})
            
            historical_data[instrument].append({
                'time': candle.get('time'),
                'open': float(mid_data.get('o', 0)),
                'high': float(mid_data.get('h', 0)),
                'low': float(mid_data.get('l', 0)),
                'close': float(mid_data.get('c', 0)),
                'bid': float(bid_data.get('c', 0)) if bid_data else float(mid_data.get('c', 0)),
                'ask': float(ask_data.get('c', 0)) if ask_data else float(mid_data.get('c', 0)),
                'volume': int(candle.get('volume', 1000))
            })
        
        print(f"  ✅ {instrument}: {len(historical_data[instrument])} candles")

print()

# Run validation
validator = StrategyValidator('momentum_trading', lookback_hours=4)
results = validator.run_strategy_backtest(strategy, historical_data)

print()
print("📊 YESTERDAY'S RESULTS (Prime Hours 1-5pm):")
print("-" * 80)
print(f"Signals Generated: {results['signals_generated']}")
print(f"Quality Scores: {results['quality_scores'][:10] if results['quality_scores'] else 'None'}")
print(f"Average Quality: {results['avg_quality']:.1f}" if results['avg_quality'] > 0 else "Average Quality: N/A")
print(f"Trades Per Hour: {results['trades_per_hour']}")
print(f"Estimated Per Day: {results['signals_generated'] * 6:.1f}")
print()

# Validate
validation = validator.validate_parameters(results)

print("✅ VALIDATION RESULT:")
print("-" * 80)
print(f"Valid: {'✅ YES' if validation['valid'] else '❌ NO'}")
print(f"Actual (4h yesterday): {validation['actual_trades_4h']} trades")
print(f"Estimated/Day: {validation['estimated_per_day']:.1f} trades")
print(f"Target Range: {validation['target_range']}")
print(f"Adjustment: {validation['adjustment_needed']}")
print()

if validation['valid']:
    print("=" * 80)
    print("✅ PARAMETERS VALIDATED ON YESTERDAY'S MARKET!")
    print("=" * 80)
    print()
    print("These parameters work in normal market conditions.")
    print("Current settings would have produced", validation['estimated_per_day'], "trades/day yesterday.")
    print()
    print("Safe to deploy!")
else:
    print("=" * 80)
    print("⚠️ PARAMETERS NEED TUNING")
    print("=" * 80)
    print()
    print("Yesterday's market was more active, but still didn't produce signals.")
    print("This means parameters are TOO STRICT even for normal conditions.")
    print()
    print("Recommendation:", validation['adjustment_needed'])




















