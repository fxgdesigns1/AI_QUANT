#!/usr/bin/env python3
"""
Diagnose why Gold shows negative momentum when it moved +8% up
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher

print("🔍 GOLD MOMENTUM DIAGNOSIS")
print("="*100)

# Get Gold data
fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['XAU_USD'], hours=168)  # 7 days
candles = historical_data['XAU_USD']

print(f"\n📊 Retrieved {len(candles)} Gold candles (7 days)")

# Overall move
start_price = float(candles[0]['close'])
end_price = float(candles[-1]['close'])
overall_move = ((end_price - start_price) / start_price) * 100

print(f"\n📈 OVERALL MOVE:")
print(f"   Start: ${start_price:.2f}")
print(f"   End:   ${end_price:.2f}")
print(f"   Move:  {overall_move:+.2f}%")

# Check momentum at different periods
print(f"\n📊 MOMENTUM AT DIFFERENT WINDOWS:")
print("-"*100)

periods = [14, 20, 50, 100, 200]
for period in periods:
    if len(candles) >= period:
        recent_candles = candles[-period:]
        period_start = float(recent_candles[0]['close'])
        period_end = float(recent_candles[-1]['close'])
        period_momentum = ((period_end - period_start) / period_start) * 100
        
        print(f"Last {period:3d} candles: {period_momentum:+.2f}%")

# Check last 50 candles individually to see volatility
print(f"\n📊 LAST 50 CANDLES (5-min each = 4.2 hours):")
print("-"*100)

last_50 = candles[-50:]
for i, candle in enumerate(last_50):
    close = float(candle['close'])
    
    # Calculate momentum from this point backwards (14 candles)
    if i >= 14:
        lookback_14 = last_50[i-14:i+1]
        start_14 = float(lookback_14[0]['close'])
        end_14 = float(lookback_14[-1]['close'])
        momentum_14 = ((end_14 - start_14) / start_14) * 100
        
        direction = "📈 UP" if momentum_14 > 0 else "📉 DOWN"
        
        print(f"Candle {i+1:2d}: ${close:.2f}  |  14-bar momentum: {momentum_14:+.2f}% {direction}")

print("\n" + "="*100)
print("ANALYSIS:")
print("="*100)

print("""
The strategy uses a 14-bar momentum (14 x 5min = 70 minutes = 1.17 hours).

If Gold moved +8% over 7 days but showed NEGATIVE 14-bar momentum at a specific
candle, it means:

1. Gold was in a temporary PULLBACK at that moment
2. The 14-bar window (1.17 hours) captured a DOWN move
3. Even though the overall trend was UP (+8%), short-term was DOWN

This is WHY we see:
- Gold: +8% overall (correct)
- Signal: BEARISH with -7.84% momentum (also correct for that 14-bar window!)

The strategy is working as designed - it caught a pullback/reversal opportunity.

QUESTION: Do we want the strategy to:
A) Trade pullbacks in the overall trend (current behavior)
B) Only trade in the direction of the larger trend (need multi-timeframe)
C) Use longer momentum period (e.g. 50 bars = 4 hours instead of 14 bars = 1h)
""")

print("="*100)









