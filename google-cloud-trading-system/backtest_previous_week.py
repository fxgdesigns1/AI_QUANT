#!/usr/bin/env python3
"""
Backtest ALL fixed strategies against the previous week's data
"""

import sys
sys.path.insert(0, '.')

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData

print("📊 PREVIOUS WEEK BACKTEST RESULTS")
print("="*100)
print("Testing optimized strategies against last 7 days of market data")
print("="*100)

# Get 7 days of historical data
fetcher = get_historical_fetcher()

print("\n📥 Fetching 7-day (168 hour) historical data...")

instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD', 'XAU_USD']
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=168)

print(f"✅ Retrieved data for {len(instruments)} instruments\n")

# Calculate actual market moves
print("📈 ACTUAL MARKET MOVES (7 Days):")
print("-"*100)

market_summary = {}
for instrument in sorted(instruments):
    if instrument in historical_data and len(historical_data[instrument]) > 0:
        candles = historical_data[instrument]
        start_price = float(candles[0]['close'])
        end_price = float(candles[-1]['close'])
        move_pct = ((end_price - start_price) / start_price) * 100
        
        # Calculate high-low range
        all_highs = [float(c['high']) for c in candles]
        all_lows = [float(c['low']) for c in candles]
        high = max(all_highs)
        low = min(all_lows)
        range_pct = ((high - low) / low) * 100
        
        market_summary[instrument] = {
            'start': start_price,
            'end': end_price,
            'move_pct': move_pct,
            'range_pct': range_pct,
            'bars': len(candles)
        }
        
        print(f"{instrument}:")
        print(f"  Start:  {start_price:.4f}")
        print(f"  End:    {end_price:.4f}")
        print(f"  Move:   {move_pct:+.2f}%")
        print(f"  Range:  {range_pct:.2f}% (High: {high:.4f}, Low: {low:.4f})")
        print(f"  Bars:   {len(candles)}")
        print()

# Test each strategy
print("="*100)
print("⚙️  STRATEGY BACKTEST RESULTS")
print("="*100)

strategies_to_test = [
    {
        'name': 'Trump DNA (Momentum Trading)',
        'module': 'src.strategies.momentum_trading',
        'function': 'get_momentum_trading_strategy',
        'instruments': ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
    },
    {
        'name': 'Ultra Strict Forex',
        'module': 'src.strategies.ultra_strict_forex',
        'function': 'get_ultra_strict_forex_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
    },
]

all_results = []

for strat_info in strategies_to_test:
    print(f"\n{'='*100}")
    print(f"Strategy: {strat_info['name']}")
    print(f"Instruments: {', '.join(strat_info['instruments'])}")
    print(f"{'='*100}\n")
    
    try:
        import importlib
        module = importlib.import_module(strat_info['module'])
        get_strategy = getattr(module, strat_info['function'])
        strategy = get_strategy()
        
        print(f"✅ Strategy loaded")
        
        # CRITICAL FIX: Clear prefill before backtest!
        # Prefill contains RECENT data, backtest feeds OLD data
        # Mixing them creates wrong chronological order
        for instrument in strat_info['instruments']:
            if instrument in strategy.price_history:
                strategy.price_history[instrument] = []
        
        print(f"✅ Cleared prefill - will build naturally from historical candles")
        
        # Let the strategy build it naturally from _update_price_history as we feed candles
        # This maintains correct chronological order
        
        # Disable time gap for backtest
        original_gap = None
        if hasattr(strategy, 'min_time_between_trades_minutes'):
            original_gap = strategy.min_time_between_trades_minutes
            strategy.min_time_between_trades_minutes = 0
        
        # Test signal generation - CRITICAL FIX: Process ALL instruments together!
        signals_generated = 0
        signals_by_instrument = {inst: 0 for inst in strat_info['instruments'] if inst in historical_data}
        
        # Find shortest history length
        min_length = min(len(historical_data[inst]) for inst in strat_info['instruments'] if inst in historical_data)
        
        print(f"✅ Processing {min_length} candles for each instrument together")
        
        # Process timestamp by timestamp (like live trading)
        for candle_idx in range(min_length):
            # Build market_data dict with ALL instruments at this timestamp
            market_data_dict = {}
            
            for instrument in strat_info['instruments']:
                if instrument not in historical_data:
                    continue
                
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
            if hasattr(strategy, 'analyze_market'):
                signals = strategy.analyze_market(market_data_dict)
                if signals:
                    for signal in signals:
                        signals_generated += 1
                        signals_by_instrument[signal.instrument] += 1
        
        # Restore time gap
        if original_gap is not None:
            strategy.min_time_between_trades_minutes = original_gap
        
        # Calculate metrics
        signals_per_day = signals_generated / 7
        
        print(f"\n📊 RESULTS:")
        print(f"   Total signals: {signals_generated}")
        print(f"   Signals/day: {signals_per_day:.1f}")
        print(f"   Target: 3-10 signals/day")
        
        print(f"\n   Breakdown by pair:")
        for inst, count in signals_by_instrument.items():
            if count > 0:
                print(f"     {inst}: {count} signals ({count/7:.1f}/day)")
        
        # Status
        if 3 <= signals_per_day <= 10:
            status = "✅ EXCELLENT"
        elif 1 <= signals_per_day < 3:
            status = "⚠️  BELOW TARGET"
        else:
            status = "❌ NEEDS TUNING"
        
        print(f"\n   Status: {status}")
        
        all_results.append({
            'name': strat_info['name'],
            'signals': signals_generated,
            'signals_per_day': signals_per_day,
            'status': status
        })
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        all_results.append({
            'name': strat_info['name'],
            'signals': 0,
            'signals_per_day': 0,
            'status': '❌ ERROR',
            'error': str(e)
        })

# Final summary
print("\n" + "="*100)
print("SUMMARY - PREVIOUS WEEK BACKTEST")
print("="*100)

print("\n📈 Market Activity (7 days):")
for instrument, data in market_summary.items():
    print(f"   {instrument}: {data['move_pct']:+.2f}% move, {data['range_pct']:.2f}% range")

print("\n⚙️  Strategy Performance:")
for result in all_results:
    print(f"   {result['status']} {result['name']}: {result['signals_per_day']:.1f} signals/day")

total_signals = sum(r['signals'] for r in all_results)
avg_signals_per_day = total_signals / 7

print(f"\n📊 Overall System:")
print(f"   Total signals (7 days): {total_signals}")
print(f"   Average signals/day: {avg_signals_per_day:.1f}")
print(f"   Target: 40-80 signals/day across all strategies")

if avg_signals_per_day >= 40:
    print(f"\n   ✅ EXCELLENT - System producing target signal volume")
elif avg_signals_per_day >= 20:
    print(f"\n   ⚠️  GOOD - Above minimum but below target")
else:
    print(f"\n   ❌ NEEDS MORE TUNING - Below target volume")

print("\n" + "="*100)
print("KEY INSIGHTS:")
print("="*100)

# Compare to market volatility
gold_move = market_summary.get('XAU_USD', {}).get('move_pct', 0)
forex_avg = sum(market_summary.get(p, {}).get('range_pct', 0) for p in ['EUR_USD', 'GBP_USD', 'USD_JPY']) / 3

print(f"""
Market Conditions:
- Gold moved {gold_move:+.2f}% (significant opportunity)
- Forex average range: {forex_avg:.2f}% (moderate volatility)

Strategy Performance:
- Trump DNA: {all_results[0]['signals_per_day']:.1f} signals/day
- Target was 3-10 signals/day per strategy
- With fixes applied, capturing more opportunities

Next Steps:
1. If below 3 signals/day: Lower thresholds further
2. If above 10 signals/day: Raise quality filters slightly
3. Monitor live performance for 24h before further tuning
""")

print("="*100)

