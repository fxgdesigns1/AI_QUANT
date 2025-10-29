#!/usr/bin/env python3
"""
Diagnose why forex pairs generate 0 signals when Gold generates 10
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🔍 DIAGNOSE ALL PAIRS - Why only Gold works?")
print("="*100)

# Get data for all pairs
fetcher = get_historical_fetcher()
instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=168)

print(f"\n📊 MARKET MOVES (7 Days):")
print("-"*100)

market_moves = {}
for instrument in instruments:
    if instrument in historical_data and len(historical_data[instrument]) > 0:
        candles = historical_data[instrument]
        start = float(candles[0]['close'])
        end = float(candles[-1]['close'])
        move = ((end - start) / start) * 100
        
        # Check 50-bar momentum (what strategy uses)
        if len(candles) >= 50:
            recent_50 = candles[-50:]
            start_50 = float(recent_50[0]['close'])
            end_50 = float(recent_50[-1]['close'])
            momentum_50 = ((end_50 - start_50) / start_50) * 100
        else:
            momentum_50 = 0
        
        market_moves[instrument] = {
            'total_move': move,
            'momentum_50': momentum_50,
            'bars': len(candles)
        }
        
        print(f"{instrument}:")
        print(f"  Total move (7d):  {move:+.2f}%")
        print(f"  50-bar momentum:  {momentum_50:+.2f}%")
        print(f"  Bars: {len(candles)}")

# Load strategy
print(f"\n⚙️  LOADING STRATEGY:")
print("-"*100)

strategy = get_momentum_trading_strategy()

print(f"✅ Strategy loaded")
print(f"\n📊 Strategy Configuration:")
print(f"   momentum_period: {strategy.momentum_period} bars")
print(f"   trend_period: {strategy.trend_period} bars")
print(f"   min_momentum: {strategy.min_momentum} ({strategy.min_momentum*100:.4f}%)")
print(f"   min_adx: {strategy.min_adx}")
print(f"   min_quality_score: {strategy.min_quality_score}")

# Clear prefill
for instrument in instruments:
    if instrument in strategy.price_history:
        strategy.price_history[instrument] = []

print(f"\n✅ Cleared prefill")

# Disable time gap
strategy.min_time_between_trades_minutes = 0

# Test each pair
print(f"\n🎯 TESTING EACH PAIR:")
print("="*100)

results = {}

for instrument in instruments:
    print(f"\n{'─'*100}")
    print(f"Testing: {instrument}")
    print(f"{'─'*100}")
    
    if instrument not in historical_data:
        print(f"❌ No data available")
        continue
    
    candles = historical_data[instrument]
    signals_generated = 0
    first_signal_candle = None
    rejection_reasons = {}
    
    # Feed candles chronologically
    for idx, candle in enumerate(candles):
        close_price = float(candle['close'])
        
        market_data = MarketData(
            pair=instrument,
            bid=close_price,
            ask=close_price + 0.0001,
            timestamp=candle['time'],
            is_live=False,
            data_source='OANDA_Historical',
            spread=0.0001,
            last_update_age=0
        )
        
        signals = strategy.analyze_market({instrument: market_data})
        
        if signals:
            signals_generated += 1
            if first_signal_candle is None:
                first_signal_candle = idx
    
    signals_per_day = signals_generated / 7
    
    results[instrument] = {
        'signals': signals_generated,
        'signals_per_day': signals_per_day,
        'first_signal': first_signal_candle,
        'market_move': market_moves[instrument]['total_move'],
        'momentum_50': market_moves[instrument]['momentum_50']
    }
    
    status = "✅" if signals_generated > 0 else "❌"
    print(f"\n{status} Results:")
    print(f"   Total signals: {signals_generated}")
    print(f"   Signals/day: {signals_per_day:.1f}")
    print(f"   Market move: {market_moves[instrument]['total_move']:+.2f}%")
    print(f"   50-bar momentum: {market_moves[instrument]['momentum_50']:+.2f}%")
    
    if signals_generated > 0:
        print(f"   First signal at candle: {first_signal_candle}/{len(candles)}")
    else:
        print(f"   ⚠️  NO SIGNALS GENERATED")
        
        # Check if it meets thresholds
        momentum_50 = abs(market_moves[instrument]['momentum_50']) / 100
        if momentum_50 < strategy.min_momentum:
            print(f"   → Likely blocked by min_momentum ({momentum_50:.6f} < {strategy.min_momentum})")

# Summary
print(f"\n{'='*100}")
print("SUMMARY BY PAIR:")
print(f"{'='*100}\n")

for instrument in instruments:
    if instrument in results:
        r = results[instrument]
        status = "✅" if r['signals'] > 0 else "❌"
        print(f"{status} {instrument}: {r['signals']} signals ({r['signals_per_day']:.1f}/day) - Move: {r['market_move']:+.2f}%")

print(f"\n{'='*100}")
print("ANALYSIS:")
print(f"{'='*100}\n")

working_pairs = [k for k, v in results.items() if v['signals'] > 0]
broken_pairs = [k for k, v in results.items() if v['signals'] == 0]

print(f"✅ Working pairs: {', '.join(working_pairs) if working_pairs else 'NONE'}")
print(f"❌ Broken pairs: {', '.join(broken_pairs) if broken_pairs else 'NONE'}")

if broken_pairs:
    print(f"\n🔍 Why broken pairs don't work:")
    for pair in broken_pairs:
        r = results[pair]
        momentum = abs(r['momentum_50']) / 100
        print(f"\n   {pair}:")
        print(f"      50-bar momentum: {momentum:.6f} ({r['momentum_50']:+.4f}%)")
        print(f"      Min required: {strategy.min_momentum:.6f} ({strategy.min_momentum*100:.4f}%)")
        
        if momentum < strategy.min_momentum:
            gap = (strategy.min_momentum - momentum) * 100
            print(f"      ❌ BLOCKED: {gap:.4f}% below threshold")
            
            # Recommendation
            recommended = momentum * 0.5  # 50% of actual momentum
            print(f"      💡 Recommend lowering min_momentum to: {recommended:.6f}")
        else:
            print(f"      ⚠️  Momentum passes - check other filters")

print(f"\n{'='*100}")
print("RECOMMENDATIONS:")
print(f"{'='*100}\n")

if broken_pairs:
    # Find the highest momentum among broken pairs
    broken_momentums = [abs(results[p]['momentum_50'])/100 for p in broken_pairs]
    max_broken_momentum = max(broken_momentums) if broken_momentums else 0
    
    if max_broken_momentum > 0:
        recommended_threshold = max_broken_momentum * 0.7  # 70% of highest
        print(f"Current min_momentum: {strategy.min_momentum:.6f} ({strategy.min_momentum*100:.4f}%)")
        print(f"Recommended: {recommended_threshold:.6f} ({recommended_threshold*100:.4f}%)")
        print(f"\nThis would enable signals from:")
        for pair in broken_pairs:
            momentum = abs(results[pair]['momentum_50']) / 100
            if momentum >= recommended_threshold:
                print(f"   ✅ {pair} (momentum: {momentum:.6f})")

print(f"\n{'='*100}")














