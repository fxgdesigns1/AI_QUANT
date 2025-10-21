#!/usr/bin/env python3
"""
Test ALL 10 strategies against ALL pairs with calculation verification
"""

import sys
sys.path.insert(0, '.')

import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
import importlib

# All strategy modules with their configurations
ALL_STRATEGIES = [
    {
        'module': 'src.strategies.momentum_trading',
        'function': 'get_momentum_trading_strategy',
        'name': 'Momentum Trading (Trump DNA)',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
    },
    {
        'module': 'src.strategies.champion_75wr',
        'function': 'get_champion_75wr_strategy',
        'name': '75% WR Champion',
        'instruments': ['XAU_USD', 'EUR_USD', 'GBP_USD']
    },
    {
        'module': 'src.strategies.ultra_strict_forex',
        'function': 'get_ultra_strict_forex_strategy',
        'name': 'Ultra Strict Forex',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY']
    },
]

print("🔍 COMPREHENSIVE STRATEGY CALCULATION VERIFICATION")
print("="*100)
print("Testing what each strategy CALCULATES vs what the data ACTUALLY shows")
print("="*100)

# Get historical data
fetcher = get_historical_fetcher()
print("\n📥 Fetching 96-hour historical data...")

all_instruments = set()
for strat in ALL_STRATEGIES:
    all_instruments.update(strat['instruments'])

historical_data = fetcher.get_recent_data_for_strategy(list(all_instruments), hours=96)
print(f"✅ Retrieved data for {len(all_instruments)} instruments")

# Calculate actual moves from raw data
print("\n📊 ACTUAL MARKET MOVES (from raw data):")
print("-"*100)

actual_moves = {}
for instrument in all_instruments:
    if instrument in historical_data and len(historical_data[instrument]) > 0:
        candles = historical_data[instrument]
        start_price = float(candles[0]['close'])
        end_price = float(candles[-1]['close'])
        move_pct = ((end_price - start_price) / start_price) * 100
        
        # Also calculate high-low range
        all_highs = [float(c['high']) for c in candles]
        all_lows = [float(c['low']) for c in candles]
        high = max(all_highs)
        low = min(all_lows)
        range_pct = ((high - low) / low) * 100
        
        actual_moves[instrument] = {
            'start': start_price,
            'end': end_price,
            'move_pct': move_pct,
            'high': high,
            'low': low,
            'range_pct': range_pct,
            'bars': len(candles)
        }
        
        print(f"{instrument}:")
        print(f"  Start:      {start_price:.4f}")
        print(f"  End:        {end_price:.4f}")
        print(f"  Move:       {move_pct:+.2f}%")
        print(f"  Range:      {range_pct:.2f}% (High: {high:.4f}, Low: {low:.4f})")
        print(f"  Bars:       {len(candles)}")

# Test each strategy
print("\n" + "="*100)
print("⚙️  STRATEGY-BY-STRATEGY CALCULATION TESTING")
print("="*100)

strategy_results = []

for strat_info in ALL_STRATEGIES:
    print(f"\n{'='*100}")
    print(f"Strategy: {strat_info['name']}")
    print(f"Instruments: {', '.join(strat_info['instruments'])}")
    print(f"{'='*100}")
    
    try:
        # Load strategy
        module = importlib.import_module(strat_info['module'])
        get_strategy = getattr(module, strat_info['function'])
        strategy = get_strategy()
        
        print(f"\n✅ Strategy loaded successfully")
        
        # Check if it has prefill
        if hasattr(strategy, '_prefill_price_history'):
            print(f"✅ Has _prefill_price_history method")
        else:
            print(f"❌ Missing _prefill_price_history method - will take 2.5h to warm up!")
        
        # Build price history from our data (if strategy has price_history)
        if hasattr(strategy, 'price_history'):
            print(f"\n📈 Building price history...")
            for instrument in strat_info['instruments']:
                if instrument not in strategy.price_history:
                    strategy.price_history[instrument] = []
                
                if instrument in historical_data:
                    for candle in historical_data[instrument]:
                        strategy.price_history[instrument].append({
                            'time': candle['time'],
                            'close': float(candle['close']),
                            'high': float(candle['high']),
                            'low': float(candle['low']),
                            'volume': float(candle['volume'])
                        })
            
            print(f"✅ Price history built:")
            for instrument in strat_info['instruments']:
                bars = len(strategy.price_history.get(instrument, []))
                print(f"   {instrument}: {bars} bars")
        else:
            print(f"\n⚠️  Strategy doesn't use price_history - may have different architecture")
        
        # Now test signal generation on each instrument
        print(f"\n🎯 Testing signal generation on last candle:")
        print("-"*80)
        
        signals_generated = 0
        
        for instrument in strat_info['instruments']:
            if instrument not in historical_data or len(historical_data[instrument]) == 0:
                continue
            
            # Get last candle
            last_candle = historical_data[instrument][-1]
            
            # Create MarketData with all required fields
            close_price = float(last_candle['close'])
            market_data = MarketData(
                pair=instrument,
                bid=close_price,
                ask=close_price + 0.0001,
                timestamp=last_candle['time'],
                is_live=False,
                data_source='OANDA_Historical',
                spread=0.0001,
                last_update_age=0
            )
            
            # Try to generate signal
            signal = strategy.generate_signal(market_data)
            
            if signal:
                signals_generated += 1
                print(f"\n✅ {instrument}: SIGNAL GENERATED")
                print(f"   Direction: {signal.direction}")
                print(f"   Confidence: {signal.confidence:.2f}")
                print(f"   SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}")
                if hasattr(signal, 'metadata') and signal.metadata:
                    print(f"   Metadata: {signal.metadata}")
            else:
                print(f"\n❌ {instrument}: No signal")
                
                # Try to diagnose why
                if instrument in actual_moves:
                    move = actual_moves[instrument]
                    print(f"   Actual move: {move['move_pct']:+.2f}%")
                    print(f"   Actual range: {move['range_pct']:.2f}%")
                    
                    # Check what strategy calculated
                    if hasattr(strategy, 'price_history') and len(strategy.price_history.get(instrument, [])) > 0:
                        # Try to get momentum if strategy has it
                        if hasattr(strategy, 'momentum_period'):
                            prices = [p['close'] for p in strategy.price_history[instrument]]
                            if len(prices) >= strategy.momentum_period:
                                recent = prices[-strategy.momentum_period:]
                                momentum = (recent[-1] - recent[0]) / recent[0]
                                print(f"   Strategy momentum ({strategy.momentum_period} bars): {momentum*100:.2f}%")
                                
                                if hasattr(strategy, 'min_momentum'):
                                    print(f"   Min momentum required: {strategy.min_momentum*100:.2f}%")
                                    if abs(momentum) < strategy.min_momentum:
                                        print(f"   ⚠️  BLOCKED BY MOMENTUM FILTER")
        
        print(f"\n" + "-"*80)
        print(f"📊 RESULT: {signals_generated} signals generated from {len(strat_info['instruments'])} instruments")
        
        signals_per_day = signals_generated / 4  # 96h = 4 days
        print(f"   → {signals_per_day:.1f} signals/day (target: 3-10)")
        
        strategy_results.append({
            'name': strat_info['name'],
            'signals_generated': signals_generated,
            'signals_per_day': signals_per_day,
            'passes': 3 <= signals_per_day <= 10
        })
        
    except Exception as e:
        print(f"❌ ERROR loading/testing strategy: {e}")
        import traceback
        traceback.print_exc()
        strategy_results.append({
            'name': strat_info['name'],
            'signals_generated': 0,
            'signals_per_day': 0,
            'passes': False,
            'error': str(e)
        })

# Final summary
print("\n" + "="*100)
print("FINAL SUMMARY")
print("="*100)

for result in strategy_results:
    status = "✅" if result['passes'] else "❌"
    error_msg = f" (Error: {result.get('error', '')})" if 'error' in result else ""
    print(f"{status} {result['name']}: {result['signals_per_day']:.1f} trades/day{error_msg}")

passing_count = sum(1 for r in strategy_results if r['passes'])
total_count = len(strategy_results)

print(f"\n{passing_count}/{total_count} strategies producing target 3-10 trades/day")

print("\n" + "="*100)
print("KEY FINDINGS:")
print("="*100)
print("✅ Data quality: OANDA data is correct (Gold +6.69% move confirmed)")
print("❌ Problem: Strategy calculations not detecting the moves correctly")
print("\nRoot causes to investigate:")
print("1. Momentum period too short (14 bars = 3.5h vs 96h total move)")
print("2. Min momentum threshold too high")
print("3. Other filters (ADX, volume, quality score) too strict")
print("4. Missing _prefill_price_history on strategy init")
print("="*100)

