#!/usr/bin/env python3
"""
Tune Momentum Strategy NOW - Find Working Parameters
Tests progressively looser settings until we find what produces ~5 trades/day
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator

print("🔧 TUNING MOMENTUM STRATEGY - FIND WORKING PARAMETERS")
print("=" * 80)
print()

# Test configurations from strict to very relaxed
test_configs = [
    {
        'name': 'ULTRA STRICT (Current-ish)',
        'min_adx': 25,
        'min_momentum': 0.008,
        'min_volume': 0.35,
        'min_quality_score': 70
    },
    {
        'name': 'STRICT',
        'min_adx': 22,
        'min_momentum': 0.006,
        'min_volume': 0.30,
        'min_quality_score': 60
    },
    {
        'name': 'MODERATE',
        'min_adx': 20,
        'min_momentum': 0.004,
        'min_volume': 0.25,
        'min_quality_score': 50
    },
    {
        'name': 'RELAXED',
        'min_adx': 18,
        'min_momentum': 0.003,
        'min_volume': 0.20,
        'min_quality_score': 40
    },
    {
        'name': 'VERY RELAXED',
        'min_adx': 15,
        'min_momentum': 0.002,
        'min_volume': 0.15,
        'min_quality_score': 30
    },
    {
        'name': 'ULTRA RELAXED',
        'min_adx': 12,
        'min_momentum': 0.001,
        'min_volume': 0.10,
        'min_quality_score': 20
    }
]

# Get historical data
fetcher = get_historical_fetcher()
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']

print("📥 Fetching last 4 hours of market data...")
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=4)
print(f"✅ Got data for {len(historical_data)} instruments")
print()

print("🔄 Testing different parameter configurations...")
print()

results = []
validator = StrategyValidator('momentum_trading', lookback_hours=4)

for config in test_configs:
    print(f"Testing: {config['name']:<20}", end=" ")
    
    # Load fresh strategy
    strategy = get_momentum_trading_strategy()
    
    # Apply test configuration
    strategy.min_adx = config['min_adx']
    strategy.min_momentum = config['min_momentum']
    strategy.min_volume = config['min_volume']
    strategy.min_quality_score = config['min_quality_score']
    
    # Reset strategy state
    strategy.price_history = {inst: [] for inst in instruments}
    strategy.daily_trade_count = 0
    strategy.daily_signals = []
    
    # Run through historical data
    backtest_results = validator.run_strategy_backtest(strategy, historical_data)
    
    trades_4h = backtest_results['signals_generated']
    trades_day_est = trades_4h * 6
    avg_quality = backtest_results['avg_quality']
    
    results.append({
        'config': config,
        'trades_4h': trades_4h,
        'trades_day_est': trades_day_est,
        'avg_quality': avg_quality
    })
    
    print(f"→ {trades_4h} signals, ~{trades_day_est:.0f}/day, quality {avg_quality:.1f}")

print()
print("=" * 80)
print("TUNING RESULTS")
print("=" * 80)
print()

# Find configs that produce signals
working_configs = [r for r in results if r['trades_day_est'] > 0]

if not working_configs:
    print("❌ NO CONFIGURATION PRODUCED SIGNALS!")
    print()
    print("This means:")
    print("  • Market was COMPLETELY FLAT in last 4 hours")
    print("  • Even ultra-relaxed parameters (ADX 12, momentum 0.1%) didn't trigger")
    print("  • ALL pairs had zero momentum")
    print()
    print("💡 RECOMMENDATION:")
    print("  1. Accept that some hours/days have NO tradeable setups")
    print("  2. Use ULTRA RELAXED parameters for normal days")
    print("  3. Add range-trading strategy for flat markets")
    print("  4. Test against yesterday's data (more active)")
    print()
    print("Suggested parameters for next active market:")
    print(f"  min_adx: {test_configs[-1]['min_adx']}")
    print(f"  min_momentum: {test_configs[-1]['min_momentum']}")
    print(f"  min_volume: {test_configs[-1]['min_volume']}")
    print(f"  min_quality_score: {test_configs[-1]['min_quality_score']}")
else:
    # Show working configurations
    print(f"{'Config':<20} {'Trades (4h)':<15} {'Est/Day':<12} {'Quality':<10} {'Fit'}")
    print("-" * 80)
    
    for r in results:
        trades_day = r['trades_day_est']
        distance_from_5 = abs(trades_day - 5)
        
        if 3 <= trades_day <= 10:
            fit = "✅ GOOD"
        elif trades_day > 10:
            fit = "⚠️ TOO MANY"
        elif trades_day > 0:
            fit = "⚠️ TOO FEW"
        else:
            fit = "❌ NONE"
        
        marker = '🎯' if trades_day > 0 and distance_from_5 == min(abs(x['trades_day_est'] - 5) for x in working_configs) else '  '
        
        print(f"{marker} {r['config']['name']:<18} {r['trades_4h']:<15} {trades_day:<12.1f} {r['avg_quality']:<10.1f} {fit}")
    
    print("=" * 80)
    print()
    
    # Find best (closest to 5 trades/day)
    best = min(working_configs, key=lambda x: abs(x['trades_day_est'] - 5))
    
    print("🏆 RECOMMENDED CONFIGURATION:")
    print("-" * 80)
    print(f"Config: {best['config']['name']}")
    print(f"Expected: {best['trades_day_est']:.1f} trades/day")
    print(f"Quality: {best['avg_quality']:.1f} average")
    print()
    print("Parameters:")
    for param, value in best['config'].items():
        if param != 'name':
            print(f"  {param}: {value}")
    print()
    
    print("🔧 TO APPLY THESE SETTINGS:")
    print("-" * 80)
    print()
    print("Edit: google-cloud-trading-system/src/strategies/momentum_trading.py")
    print()
    print("Change lines ~62-64 to:")
    print(f"  self.min_adx = {best['config']['min_adx']}")
    print(f"  self.min_momentum = {best['config']['min_momentum']}")
    print(f"  self.min_volume = {best['config']['min_volume']}")
    print()
    print("Change line ~145 to:")
    print(f"  self.min_quality_score = {best['config']['min_quality_score']}")
    print()

print("=" * 80)


















