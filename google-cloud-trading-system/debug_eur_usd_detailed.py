#!/usr/bin/env python3
"""
Deep debug EUR_USD to find what filter blocks it after passing momentum
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🔍 DEEP DEBUG: EUR_USD")
print("="*100)
print("EUR_USD passes momentum but generates 0 signals - WHY?")
print("="*100)

# Get data
fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['EUR_USD'], hours=168)
candles = historical_data['EUR_USD']

print(f"\n✅ Retrieved {len(candles)} EUR_USD candles")

# Load strategy
strategy = get_momentum_trading_strategy()

# Clear prefill
strategy.price_history['EUR_USD'] = []
strategy.min_time_between_trades_minutes = 0

print(f"\n⚙️  Strategy Config:")
print(f"   momentum_period: {strategy.momentum_period}")
print(f"   trend_period: {strategy.trend_period}")
print(f"   min_momentum: {strategy.min_momentum} ({strategy.min_momentum*100:.4f}%)")
print(f"   min_adx: {strategy.min_adx}")

# Test last 50 candles and log EVERY rejection reason
print(f"\n🎯 Testing Last 50 Candles:")
print("="*100)

test_candles = candles[-200:]  # Use 200 to build history, test last 50

signals_generated = 0
rejection_counts = {}

for idx, candle in enumerate(test_candles):
    close_price = float(candle['close'])
    
    market_data = MarketData(
        pair='EUR_USD',
        bid=close_price,
        ask=close_price + 0.00001,
        timestamp=candle['time'],
        is_live=False,
        data_source='OANDA_Historical',
        spread=0.00001,
        last_update_age=0
    )
    
    # Only start checking after we have enough history
    if idx < 100:
        # Just build history
        strategy.analyze_market({'EUR_USD': market_data})
        continue
    
    # Now test and capture logs
    import io
    import logging
    
    # Create string buffer to capture logs
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    # Get the strategy logger
    strat_logger = logging.getLogger('src.strategies.momentum_trading')
    original_handlers = strat_logger.handlers[:]
    strat_logger.handlers = [handler]
    
    signals = strategy.analyze_market({'EUR_USD': market_data})
    
    # Restore handlers
    strat_logger.handlers = original_handlers
    
    # Get log output
    log_output = log_capture.getvalue()
    
    if signals:
        signals_generated += 1
        if idx >= len(test_candles) - 50:  # Last 50
            print(f"✅ Candle {idx-99}: SIGNAL - Price: {close_price:.4f}")
    else:
        if idx >= len(test_candles) - 50:  # Last 50
            # Parse rejection reason from logs
            reason = "Unknown"
            if "ADX too weak" in log_output:
                reason = "ADX too weak"
            elif "momentum too weak" in log_output:
                reason = "Momentum too weak"
            elif "volume too low" in log_output:
                reason = "Volume too low"
            elif "quality" in log_output:
                reason = "Quality score"
            elif "trend not continuing" in log_output:
                reason = "Trend not continuing"
            elif "momentum vs trend mismatch" in log_output:
                reason = "Trend mismatch"
            
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            
            print(f"❌ Candle {idx-99}: {reason} - Price: {close_price:.4f}")

print(f"\n{'='*100}")
print("SUMMARY:")
print(f"{'='*100}\n")

print(f"Signals generated (last 50 candles): {signals_generated}")
print(f"\nRejection Reasons:")
for reason, count in sorted(rejection_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"   {reason}: {count} times")

print(f"\n{'='*100}")
print("CONCLUSION:")
print(f"{'='*100}\n")

if rejection_counts:
    top_blocker = max(rejection_counts.items(), key=lambda x: x[1])
    print(f"🎯 Main blocker: {top_blocker[0]} ({top_blocker[1]}/{len(test_candles[-50:])} candles)")
    print(f"\nFIX: Lower the threshold or disable the '{top_blocker[0]}' filter")

print(f"\n{'='*100}")







