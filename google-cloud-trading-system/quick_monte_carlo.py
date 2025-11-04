#!/usr/bin/env python3
"""
Quick Monte Carlo - 100 iterations for faster results
"""

import sys
sys.path.insert(0, '.')

from monte_carlo_optimizer import monte_carlo_parameter_search
from src.core.historical_fetcher import get_historical_fetcher

print("🎲 QUICK MONTE CARLO (100 iterations)")
print("="*80)

# Get past week data
fetcher = get_historical_fetcher()
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']

print("📥 Fetching past 96 hours...")
historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=96)

# Run Monte Carlo (100 iterations = ~2 minutes)
top_configs = monte_carlo_parameter_search(
    strategy_name='momentum_trading',
    strategy_module='src.strategies.momentum_trading',
    strategy_function='get_momentum_trading_strategy',
    instruments=instruments,
    historical_data=historical_data,
    iterations=100  # Fast test
)

print("\n" + "="*80)
print("🎯 BEST CONFIGURATION FOUND:")
print("="*80)
best = top_configs[0]
print(f"\nExpected Performance: {best['signals_per_day']:.1f} trades/day")
print(f"Quality Score: {best['avg_quality']:.1f}")
print(f"\nOptimal Parameters:")
print(f"  ADX Threshold: {best['config']['min_adx']:.1f}")
print(f"  Momentum: {best['config']['min_momentum']*100:.3f}%")
print(f"  Volume: {best['config']['min_volume']:.2f}")
print(f"  Quality: {best['config']['quality_threshold']:.1f}")
print("\n" + "="*80)




















