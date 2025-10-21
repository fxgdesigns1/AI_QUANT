#!/usr/bin/env python3
"""
Test all pairs together like the real system does
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🔍 TEST ALL PAIRS TOGETHER")
print("="*100)

# Get data
fetcher = get_historical_fetcher()
instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=48)

print(f"✅ Retrieved data for {len(instruments)} instruments")

# Load strategy
strategy = get_momentum_trading_strategy()

# Clear prefill
for inst in instruments:
    if inst in strategy.price_history:
        strategy.price_history[inst] = []

# Disable time gap
strategy.min_time_between_trades_minutes = 0

print(f"\n🎯 Processing ALL pairs together (like live system):")
print("="*100)

# Find the length of shortest history
min_length = min(len(historical_data[inst]) for inst in instruments)
print(f"\nProcessing {min_length} candles for each instrument")

signals_by_instrument = {inst: 0 for inst in instruments}

# Process timestamp by timestamp
for candle_idx in range(min_length):
    # Build market_data dict with ALL instruments at this timestamp
    market_data_dict = {}
    
    for instrument in instruments:
        candle = historical_data[instrument][candle_idx]
        close_price = float(candle['close'])
        
        market_data_dict[instrument] = MarketData(
            pair=instrument,
            bid=close_price,
            ask=close_price + 0.0001,
            timestamp=candle['time'],
            is_live=False,
            data_source='OANDA_Historical',
            spread=0.0001,
            last_update_age=0
        )
    
    # Call analyze_market with ALL instruments (like live trading)
    signals = strategy.analyze_market(market_data_dict)
    
    if signals:
        for signal in signals:
            signals_by_instrument[signal.instrument] += 1
            if candle_idx % 100 == 0 or signals_by_instrument[signal.instrument] <= 3:
                print(f"✅ Candle {candle_idx}: {signal.instrument} {signal.side.value} signal")

print(f"\n{'='*100}")
print("RESULTS:")
print(f"{'='*100}\n")

total_signals = 0
for inst in instruments:
    count = signals_by_instrument[inst]
    total_signals += count
    status = "✅" if count > 0 else "❌"
    signals_per_day = count / 2  # 48 hours = 2 days
    print(f"{status} {inst}: {count} signals ({signals_per_day:.1f}/day)")

print(f"\nTotal: {total_signals} signals ({total_signals/2:.1f}/day)")
print(f"Target: 6-20 signals over 2 days (3-10/day)")

if total_signals >= 6:
    print(f"\n✅ EXCELLENT - System working!")
elif total_signals >= 3:
    print(f"\n⚠️  BELOW TARGET - Needs more tuning")
else:
    print(f"\n❌ BROKEN - Major issues remain")

print(f"\n{'='*100}")







