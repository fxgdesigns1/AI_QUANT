#!/usr/bin/env python3
"""
Quick test of the optimizer
"""

import sys
sys.path.insert(0, '.')

from universal_optimizer import UniversalOptimizer
from src.strategies.gold_scalping import GoldScalpingStrategy

# Test with Gold only, minimal parameter combinations
optimizer = UniversalOptimizer(
    strategy_class=GoldScalpingStrategy,
    strategy_name='Gold Scalping Test',
    instruments=['XAU_USD']
)

# Minimal parameter ranges for testing
param_ranges = {
    'stop_loss_atr': [2.0, 2.5],
    'take_profit_atr': [5.0, 10.0],
    'min_adx': [8.0, 10.0],
    'min_momentum': [0.0001, 0.0003],
    'momentum_period': [30, 40],
    'trend_period': [80, 100],
    'min_quality_score': [10, 15]
}

print("\nTesting optimizer with minimal parameters...")
print(f"Total combinations: {2 * 2 * 2 * 2 * 2 * 2 * 2} = 128")

results = optimizer.optimize(param_ranges, days=2, top_n=5)

print(f"\n✅ Test complete! Got {len(results)} results")
if results:
    best = results[0]
    print(f"\nBest Result:")
    print(f"  Params: {best['params']}")
    print(f"  Trades: {best['total_trades']}")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  P&L: {best['total_pnl']:.5f}")




