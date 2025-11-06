#!/usr/bin/env python3
"""
Check if prices are in correct chronological order
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🔍 PRICE ORDER VERIFICATION")
print("="*100)

# Get Gold data
fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['XAU_USD'], hours=48)
candles = historical_data['XAU_USD']

print(f"\n📊 OANDA API Data (First 10 candles):")
print("-"*100)
for i, candle in enumerate(candles[:10]):
    print(f"Candle {i+1}: {candle['time']} - Close: ${float(candle['close']):.2f}")

print(f"\n📊 OANDA API Data (Last 10 candles):")
print("-"*100)
for i, candle in enumerate(candles[-10:]):
    print(f"Candle {i+1}: {candle['time']} - Close: ${float(candle['close']):.2f}")

# Check if chronological
print(f"\n🔍 CHRONOLOGICAL ORDER CHECK:")
print("-"*100)
times = [candle['time'] for candle in candles]
is_chronological = all(times[i] <= times[i+1] for i in range(len(times)-1))
print(f"   Chronological: {'✅ YES' if is_chronological else '❌ NO - REVERSED!'}")

# Check overall move
start = float(candles[0]['close'])
end = float(candles[-1]['close'])
move = ((end - start) / start) * 100
print(f"\n   Start (oldest): ${start:.2f}")
print(f"   End (newest):   ${end:.2f}")
print(f"   Move: {move:+.2f}%")

# Now check how strategy builds it
print(f"\n📊 STRATEGY PRICE HISTORY:")
print("-"*100)

strategy = get_momentum_trading_strategy()

print(f"Strategy prefill loaded {len(strategy.price_history.get('XAU_USD', []))} bars")
print(f"First 5 prices: {strategy.price_history.get('XAU_USD', [])[:5]}")
print(f"Last 5 prices: {strategy.price_history.get('XAU_USD', [])[-5:]}")

# Manually build like backtest does
manual_history = []
for candle in candles:
    mid_price = float(candle['close'])
    manual_history.append(mid_price)

print(f"\n📊 MANUAL BUILD (like backtest):")
print("-"*100)
print(f"First 5: {manual_history[:5]}")
print(f"Last 5: {manual_history[-5:]}")

# Calculate momentum both ways
if len(manual_history) >= 50:
    recent_50 = manual_history[-50:]
    momentum_50 = (recent_50[-1] - recent_50[0]) / recent_50[0]
    print(f"\n📊 50-BAR MOMENTUM (manual):")
    print(f"   Start: ${recent_50[0]:.2f}")
    print(f"   End:   ${recent_50[-1]:.2f}")
    print(f"   Momentum: {momentum_50*100:.4f}%")
    
    if momentum_50 > 0:
        print(f"   ✅ BULLISH (positive momentum)")
    else:
        print(f"   ❌ BEARISH (negative momentum)")
        print(f"   ⚠️  THIS IS WRONG IF GOLD WENT UP!")

print("\n" + "="*100)
print("DIAGNOSIS:")
print("="*100)

if move > 5 and momentum_50 < 0:
    print("""
❌ CRITICAL ERROR FOUND:
   - Overall move: +8% (UP)
   - 50-bar momentum: NEGATIVE (DOWN)
   
This is IMPOSSIBLE unless:
1. Prices are in WRONG ORDER (reversed)
2. Price calculation is INVERTED
3. We're looking at wrong instrument data

ACTION: Check price order in strategy.price_history
    """)
elif move > 5 and momentum_50 > 0:
    print("""
✅ MOMENTUM CORRECT:
   - Overall move: +8% (UP)
   - 50-bar momentum: POSITIVE (UP)
   
Strategy should generate BULLISH signals now!
    """)

print("="*100)





















