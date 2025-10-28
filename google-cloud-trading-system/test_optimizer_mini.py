#!/usr/bin/env python3
"""
MINIMAL TEST - Just 2 parameter combinations for Gold
Verify the entire optimizer pipeline works before running big optimization
"""

import sys
sys.path.insert(0, '.')

from universal_optimizer import UniversalOptimizer
from src.strategies.gold_scalping import GoldScalpingStrategy

print("\n" + "="*70)
print("MINIMAL OPTIMIZER TEST - 2 Combinations Only")
print("="*70 + "\n")

optimizer = UniversalOptimizer(
    strategy_class=GoldScalpingStrategy,
    strategy_name='Gold Scalping Mini Test',
    instruments=['XAU_USD']
)

# TINY parameter ranges - just 2 combinations total
param_ranges = {
    'stop_loss_atr': [2.0],  # 1 value
    'take_profit_atr': [5.0, 10.0],  # 2 values
}

print("Parameter combinations: 1 × 2 = 2 total")
print("This should take ~10-20 seconds max\n")

results = optimizer.optimize(param_ranges, days=2, top_n=2)

print("\n" + "="*70)
if results:
    print("✅ OPTIMIZER WORKS!")
    print(f"Got {len(results)} results")
    for i, r in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  Params: {r['params']}")
        print(f"  Trades: {r['total_trades']}")
        print(f"  Win Rate: {r['win_rate']:.1f}%")
        print(f"  P&L: {r['total_pnl']:.5f}")
else:
    print("❌ OPTIMIZER FAILED - NO RESULTS")
print("="*70)




