#!/usr/bin/env python3
"""
Validate Main 3 Strategies - 48 Hour Lookback
Priority testing: Trump DNA, 75% WR Champion, Momentum Multi-Pair
Check weekly cycle phase alignment
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator
import pytz

print("🎯 MAIN STRATEGIES VALIDATION - 48 HOUR LOOKBACK")
print("=" * 80)
print()

# Check weekly cycle phase
london_tz = pytz.timezone('Europe/London')
now = datetime.now(london_tz)
day_of_week = now.strftime("%A")
week_phase = ""

if day_of_week in ['Monday', 'Tuesday']:
    week_phase = "EARLY WEEK (Trends building)"
elif day_of_week in ['Wednesday', 'Thursday']:
    week_phase = "MID WEEK (Peak volatility/opportunities)"
elif day_of_week == 'Friday':
    week_phase = "LATE WEEK (Profit taking, ranges)"

print(f"📅 Current: {now.strftime('%A, %B %d, %Y @ %I:%M%p %Z')}")
print(f"🔄 Weekly Phase: {week_phase}")
print(f"📊 Lookback: Last 48 hours (captures 2 days of cycle)")
print()

# Define the 3 MAIN strategies to focus on
MAIN_STRATEGIES = [
    {
        'priority': 1,
        'name': 'gold_trump_week',
        'display': '🏅 Trump DNA Gold',
        'module': 'src.strategies.gold_trump_week_strategy',
        'function': 'get_gold_trump_week_strategy',
        'instruments': ['XAU_USD'],
        'target_trades_day': 5,
        'description': 'Trump DNA - Weekly cycle trader'
    },
    {
        'priority': 2,
        'name': 'champion_75wr',
        'display': '🏆 75% WR Champion',
        'module': 'src.strategies.champion_75wr',
        'function': 'get_champion_75wr_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'target_trades_day': 5,
        'description': '75% win rate ultra-selective'
    },
    {
        'priority': 3,
        'name': 'momentum_trading',
        'display': '📈 Momentum Multi-Pair',
        'module': 'src.strategies.momentum_trading',
        'function': 'get_momentum_trading_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
        'target_trades_day': 5,
        'description': 'Adaptive momentum with regime detection'
    }
]

# Also test these but lower priority
OTHER_STRATEGIES = [
    {'name': 'gold_scalping', 'display': '🥇 Gold Scalping', 'module': 'src.strategies.gold_scalping', 'function': 'get_gold_scalping_strategy', 'instruments': ['XAU_USD']},
    {'name': 'ultra_strict_forex', 'display': '💱 Ultra Strict Fx', 'module': 'src.strategies.ultra_strict_forex', 'function': 'get_ultra_strict_forex_strategy', 'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY']},
    {'name': 'range_trading', 'display': '↔️ Range Trading', 'module': 'src.strategies.range_trading', 'function': 'get_range_trading_strategy', 'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']},
]

print("=" * 80)
print("PRIORITY 1: MAIN STRATEGIES (DETAILED ANALYSIS)")
print("=" * 80)
print()

main_results = []

for strat_config in MAIN_STRATEGIES:
    print(f"\n{'='*80}")
    print(f"🎯 PRIORITY {strat_config['priority']}: {strat_config['display']}")
    print(f"{'='*80}")
    print(f"Description: {strat_config['description']}")
    print(f"Target: {strat_config['target_trades_day']} trades/day")
    print()
    
    try:
        # Import strategy
        module = __import__(strat_config['module'], fromlist=[strat_config['function']])
        get_strategy = getattr(module, strat_config['function'])
        strategy = get_strategy()
        
        print(f"✅ Strategy loaded: {strategy.name}")
        
        # Show current parameters
        if hasattr(strategy, 'min_adx'):
            print(f"📊 Current Parameters:")
            print(f"   Min ADX: {strategy.min_adx}")
            print(f"   Min Momentum: {getattr(strategy, 'min_momentum', 'N/A')}")
            print(f"   Min Volume: {getattr(strategy, 'min_volume', 'N/A')}")
            print(f"   Quality Threshold: {getattr(strategy, 'min_quality_score', getattr(strategy, 'min_signal_strength', 'N/A'))}")
        print()
        
        # Get 48 hours of historical data
        print(f"📥 Fetching 48-hour history for {len(strat_config['instruments'])} instruments...")
        
        fetcher = get_historical_fetcher()
        
        # Get M15 candles for 48 hours (192 candles)
        historical_data = {}
        for instrument in strat_config['instruments']:
            candles = fetcher.fetch_candles(instrument, count=192, granularity='M15')
            if candles:
                historical_data[instrument] = []
                for candle in candles:
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
        validator = StrategyValidator(strat_config['name'], lookback_hours=48)
        results = validator.run_strategy_backtest(strategy, historical_data)
        
        # Analyze by day
        trades_48h = results['signals_generated']
        trades_per_day = trades_48h / 2  # 48 hours = 2 days
        avg_quality = results['avg_quality']
        
        # Check weekly cycle distribution
        trades_per_hour = results['trades_per_hour']
        
        print(f"📊 48-HOUR RESULTS:")
        print(f"-" * 80)
        print(f"Total Signals (48h): {trades_48h}")
        print(f"Trades Per Day: {trades_per_day:.1f}")
        print(f"Target: {strat_config['target_trades_day']}")
        print(f"Average Quality: {avg_quality:.1f}" if avg_quality > 0 else "Average Quality: N/A")
        print()
        
        # Validation
        if strat_config['target_trades_day'] * 0.6 <= trades_per_day <= strat_config['target_trades_day'] * 2.0:
            status = "✅ PASS"
            passed = True
        elif trades_per_day == 0:
            status = "❌ CRITICAL FAIL (ZERO trades)"
            passed = False
        elif trades_per_day < strat_config['target_trades_day'] * 0.5:
            status = "⚠️ TOO FEW (thresholds too strict)"
            passed = False
        else:
            status = "⚠️ TOO MANY (may overtrade)"
            passed = False
        
        print(f"Status: {status}")
        print()
        
        main_results.append({
            'priority': strat_config['priority'],
            'display': strat_config['display'],
            'name': strat_config['name'],
            'trades_48h': trades_48h,
            'trades_per_day': trades_per_day,
            'target': strat_config['target_trades_day'],
            'avg_quality': avg_quality,
            'status': status,
            'passed': passed
        })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:200]}")
        main_results.append({
            'priority': strat_config['priority'],
            'display': strat_config['display'],
            'name': strat_config['name'],
            'trades_48h': 0,
            'trades_per_day': 0,
            'target': strat_config['target_trades_day'],
            'avg_quality': 0,
            'status': f"❌ ERROR",
            'passed': False
        })

# Test other strategies quickly
print("\n" + "="*80)
print("PRIORITY 2: OTHER STRATEGIES (QUICK CHECK)")
print("="*80)
print()

other_results = []

for strat_config in OTHER_STRATEGIES:
    print(f"Testing {strat_config['display']}...", end=" ")
    
    try:
        module = __import__(strat_config['module'], fromlist=[strat_config['function']])
        get_strategy = getattr(module, strat_config['function'])
        strategy = get_strategy()
        
        # Quick 48h test
        fetcher = get_historical_fetcher()
        historical_data = {}
        for instrument in strat_config['instruments']:
            candles = fetcher.fetch_candles(instrument, count=192, granularity='M15')
            if candles:
                historical_data[instrument] = []
                for candle in candles:
                    mid_data = candle.get('mid', {})
                    historical_data[instrument].append({
                        'time': candle.get('time'),
                        'close': float(mid_data.get('c', 0)),
                        'bid': float(candle.get('bid', {}).get('c', mid_data.get('c', 0))),
                        'ask': float(candle.get('ask', {}).get('c', mid_data.get('c', 0))),
                        'volume': int(candle.get('volume', 1000))
                    })
        
        validator = StrategyValidator(strat_config['name'], lookback_hours=48)
        results = validator.run_strategy_backtest(strategy, historical_data)
        
        trades_48h = results['signals_generated']
        trades_day = trades_48h / 2
        
        status = "✅" if trades_day >= 3 else ("⚠️" if trades_day > 0 else "❌")
        
        print(f"{status} {trades_48h} signals (48h), ~{trades_day:.1f}/day")
        
        other_results.append({
            'display': strat_config['display'],
            'trades_48h': trades_48h,
            'trades_per_day': trades_day
        })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:50]}")
        other_results.append({
            'display': strat_config['display'],
            'trades_48h': 0,
            'trades_per_day': 0
        })

# Final Report
print()
print("=" * 100)
print("FINAL VALIDATION REPORT - 48 HOUR LOOKBACK")
print("=" * 100)
print()

print("🎯 MAIN STRATEGIES (PRIORITY):")
print("-" * 100)
print(f"{'Priority':<10} {'Strategy':<30} {'Trades (48h)':<15} {'Per Day':<12} {'Target':<10} {'Status'}")
print("-" * 100)

for r in sorted(main_results, key=lambda x: x['priority']):
    print(f"{r['priority']:<10} {r['display']:<30} {r['trades_48h']:<15} {r['trades_per_day']:<12.1f} {r['target']:<10} {r['status']}")

print()
print("📊 OTHER STRATEGIES (TESTED):")
print("-" * 100)

for r in other_results:
    status_icon = "✅" if r['trades_per_day'] >= 3 else ("⚠️" if r['trades_per_day'] > 0 else "❌")
    print(f"{status_icon}  {r['display']:<30} {r['trades_48h']:<15} {r['trades_per_day']:<12.1f}")

print()
print("=" * 100)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 100)
print()

# Calculate totals
total_main = sum(r['trades_48h'] for r in main_results)
total_other = sum(r['trades_48h'] for r in other_results)
total_all = total_main + total_other

main_per_day = total_main / 2
other_per_day = total_other / 2
total_per_day = total_all / 2

print(f"Main Strategies (48h): {total_main} signals, {main_per_day:.1f}/day")
print(f"Other Strategies (48h): {total_other} signals, {other_per_day:.1f}/day")
print(f"ALL Strategies (48h): {total_all} signals, {total_per_day:.1f}/day")
print()

# Weekly cycle analysis
print(f"🔄 WEEKLY CYCLE ANALYSIS:")
print(f"-" * 100)
print(f"Current Phase: {week_phase}")
print(f"Testing Period: Last 48 hours = {day_of_week} + previous day")
print()

if total_all == 0:
    print("❌ ZERO SIGNALS IN 48 HOURS - CRITICAL ISSUE!")
    print()
    print("This means:")
    print("  • Parameters are TOO STRICT for real market conditions")
    print("  • OR market has been unusually flat for 2 days")
    print("  • Need MUCH more relaxed parameters")
    print()
    print("💡 IMMEDIATE ACTION:")
    print("  1. Lower ALL thresholds by 50%")
    print("  2. Test with ultra-relaxed parameters")
    print("  3. Consider this might be wrong phase of weekly cycle")
    print("  4. Test against last week's Wednesday/Thursday (peak cycle)")
elif total_per_day < 15:
    print("⚠️ LOW SIGNAL COUNT - Strategies too conservative")
    print()
    print(f"Expected: 30-50 trades/day across all strategies")
    print(f"Actual: {total_per_day:.0f} trades/day")
    print()
    print("Recommendations:")
    print("  • Lower thresholds by 25-30%")
    print("  • Enable more aggressive entry criteria")
    print("  • Consider weekly cycle (might be in slow phase)")
else:
    print("✅ HEALTHY SIGNAL GENERATION")
    print()
    print(f"Total: {total_per_day:.0f} trades/day is good")
    print("Ready to deploy!")

print()
print("=" * 100)
print()

# Check if main strategies passed
main_passed = sum(1 for r in main_results if r['passed'])

if main_passed == 3:
    print("✅ ALL 3 MAIN STRATEGIES VALIDATED - Ready to deploy!")
elif main_passed >= 2:
    print(f"⚠️ {main_passed}/3 main strategies validated - Acceptable")
else:
    print(f"❌ Only {main_passed}/3 main strategies working - Need tuning")

print()






















