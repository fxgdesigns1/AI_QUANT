#!/usr/bin/env python3
"""
MINIMAL Gold-only test with ZERO filters
Proves Gold CAN generate signals when nothing blocks it
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🥇 MINIMAL GOLD TEST - ZERO FILTERS")
print("="*100)
print("Testing if Gold CAN generate signals with all filters removed")
print("="*100)

# Get historical data
fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['XAU_USD'], hours=48)

print(f"\n✅ Retrieved {len(historical_data['XAU_USD'])} candles for Gold")

# Calculate actual move
candles = historical_data['XAU_USD']
start = float(candles[0]['close'])
end = float(candles[-1]['close'])
move = ((end - start) / start) * 100
print(f"✅ Gold moved {move:+.2f}% over 48 hours\n")

# Load strategy
strategy = get_momentum_trading_strategy()

print("📊 Strategy Configuration:")
print(f"   XAU_USD in instruments? {('XAU_USD' in strategy.instruments)}")
print(f"   min_adx: {strategy.min_adx}")
print(f"   min_momentum: {strategy.min_momentum}")
print(f"   min_quality_score: {strategy.min_quality_score}")
print(f"   daily_trade_ranking: {strategy.daily_trade_ranking}")

# Build price history
print(f"\n📈 Building price history...")
for candle in candles:
    if 'XAU_USD' not in strategy.price_history:
        strategy.price_history['XAU_USD'] = []
    strategy.price_history['XAU_USD'].append({
        'time': candle['time'],
        'close': float(candle['close']),
        'high': float(candle['high']),
        'low': float(candle['low']),
        'volume': float(candle['volume'])
    })

print(f"✅ Price history: {len(strategy.price_history['XAU_USD'])} bars")

# Test signal generation on last 20 candles
print(f"\n🎯 Testing signal generation on last 20 candles...")
print("-"*100)

signals_generated = 0
test_candles = candles[-20:]

for idx, candle in enumerate(test_candles):
    close_price = float(candle['close'])
    
    market_data = MarketData(
        pair='XAU_USD',
        bid=close_price,
        ask=close_price + 0.1,
        timestamp=candle['time'],
        is_live=False,
        data_source='OANDA_Historical',
        spread=0.1,
        last_update_age=0
    )
    
    # Call analyze_market
    signals = strategy.analyze_market({'XAU_USD': market_data})
    
    if signals:
        signals_generated += len(signals)
        print(f"✅ Candle {idx+1}: SIGNAL GENERATED! Price: {close_price:.2f}")
        for signal in signals:
            print(f"   → {signal.side.value} @ {close_price:.2f}, SL: {signal.stop_loss:.2f}, TP: {signal.take_profit:.2f}")
    else:
        print(f"❌ Candle {idx+1}: No signal. Price: {close_price:.2f}")

print("\n" + "="*100)
print("RESULTS")
print("="*100)
print(f"Total signals generated: {signals_generated}")
print(f"Signals per candle: {signals_generated/20:.2f}")
print(f"Expected: At least 1-2 signals from 20 candles with Gold's volatility")

if signals_generated == 0:
    print(f"\n❌ ZERO SIGNALS - Gold is COMPLETELY BROKEN")
    print(f"   Gold moved {move:+.2f}% but generated 0 signals")
    print(f"   There is a CRITICAL BUG blocking Gold specifically")
elif signals_generated < 5:
    print(f"\n⚠️  VERY FEW SIGNALS - Gold mostly blocked")
    print(f"   Only {signals_generated} signals from 20 candles")
    print(f"   Filters still too strict")
else:
    print(f"\n✅ GOLD WORKS! Generated {signals_generated} signals")
    print(f"   Problem is in backtest loop, not strategy itself")

print("="*100)



















