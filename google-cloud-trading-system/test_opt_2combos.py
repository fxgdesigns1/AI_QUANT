#!/usr/bin/env python3
"""
VERIFY: 2-combination optimizer test with Momentum Trading
"""

import sys
sys.path.insert(0, '.')

from universal_optimizer import UniversalOptimizer
from src.strategies.momentum_trading import MomentumTradingStrategy

print("\n" + "="*70)
print("2-COMBINATION OPTIMIZER TEST")
print("="*70 + "\n")

optimizer = UniversalOptimizer(
    strategy_class=MomentumTradingStrategy,
    strategy_name='Momentum Test',
    instruments=['XAU_USD']
)

# Just 2 combinations
param_ranges = {
    'stop_loss_atr': [2.0, 2.5],  # 2 values = 2 combinations
}

print("Running 2 combinations on 2 days of data...")
print("Should take ~30-60 seconds\n")

results = optimizer.optimize(param_ranges, days=2, top_n=2)

print("\n" + "="*70)
if results and len(results) > 0:
    print("✅ OPTIMIZER WORKS!")
    print(f"\nGot {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"\n  #{i}: stop_loss_atr={r['params']['stop_loss_atr']}")
        print(f"      Trades: {r['total_trades']}, WR: {r['win_rate']:.1f}%, P&L: {r['total_pnl']:.5f}")
else:
    print("❌ NO RESULTS - Something wrong")
print("="*70)




