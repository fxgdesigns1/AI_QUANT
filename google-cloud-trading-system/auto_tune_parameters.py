#!/usr/bin/env python3
"""
Auto-Tune Parameters - Find Optimal Settings for ~5 Trades/Day Target
Tests multiple configurations against last 4 hours to find best fit
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from typing import Dict, List
import copy

from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def auto_tune_momentum_parameters():
    """
    Automatically find optimal parameters for ~5 trades/day target
    """
    print("🔧 AUTO-TUNING MOMENTUM PARAMETERS")
    print("=" * 80)
    print()
    
    # Load current strategy to get base config
    from src.strategies.momentum_trading import get_momentum_trading_strategy
    base_strategy = get_momentum_trading_strategy()
    
    instruments = base_strategy.instruments
    
    print(f"🎯 Target: ~5 trades per day")
    print(f"📊 Testing against last 4 hours of real market data")
    print(f"🔍 Instruments: {len(instruments)} pairs")
    print()
    
    # Get historical data once
    fetcher = get_historical_fetcher()
    historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=4)
    
    # Test different parameter combinations
    test_configs = [
        {
            'name': 'Very Strict',
            'min_adx': 30,
            'min_momentum': 0.010,
            'min_volume': 0.40,
            'min_quality_score': 80
        },
        {
            'name': 'Strict',
            'min_adx': 25,
            'min_momentum': 0.008,
            'min_volume': 0.35,
            'min_quality_score': 70
        },
        {
            'name': 'Moderate',
            'min_adx': 22,
            'min_momentum': 0.006,
            'min_volume': 0.30,
            'min_quality_score': 60
        },
        {
            'name': 'Relaxed',
            'min_adx': 20,
            'min_momentum': 0.005,
            'min_volume': 0.25,
            'min_quality_score': 50
        },
        {
            'name': 'Very Relaxed',
            'min_adx': 18,
            'min_momentum': 0.004,
            'min_volume': 0.20,
            'min_quality_score': 40
        }
    ]
    
    results = []
    validator = StrategyValidator('momentum_trading', lookback_hours=4)
    
    print("Testing configurations...")
    print()
    
    for config in test_configs:
        print(f"Testing: {config['name']}...")
        
        # Create strategy with this config
        strategy = get_momentum_trading_strategy()
        
        # Apply test config
        strategy.min_adx = config['min_adx']
        strategy.min_momentum = config['min_momentum']
        strategy.min_volume = config['min_volume']
        strategy.min_quality_score = config['min_quality_score']
        
        # Reset strategy state
        strategy.price_history = {inst: [] for inst in instruments}
        strategy.daily_trade_count = 0
        strategy.daily_signals = []
        
        # Run backtest
        backtest_results = validator.run_strategy_backtest(strategy, historical_data)
        
        trades_4h = backtest_results['signals_generated']
        trades_per_day_est = trades_4h * 6
        avg_quality = backtest_results['avg_quality']
        
        # Calculate distance from target (5 trades/day)
        distance_from_target = abs(trades_per_day_est - 5)
        
        results.append({
            'config': config,
            'signals_4h': trades_4h,
            'signals_per_day_est': trades_per_day_est,
            'avg_quality': avg_quality,
            'distance_from_target': distance_from_target
        })
        
        print(f"  → {trades_4h} signals (4h), ~{trades_per_day_est:.1f}/day, quality {avg_quality:.1f}")
    
    print()
    print("=" * 80)
    print("AUTO-TUNING RESULTS")
    print("=" * 80)
    print()
    
    # Sort by distance from target (closest to 5 trades/day wins)
    results.sort(key=lambda x: x['distance_from_target'])
    
    # Print comparison table
    print(f"{'Config':<15} {'Trades (4h)':<15} {'Est/Day':<12} {'Quality':<10} {'Distance from Target'}")
    print("-" * 80)
    
    for r in results:
        config_name = r['config']['name']
        signals_4h = r['signals_4h']
        signals_day = r['signals_per_day_est']
        quality = r['avg_quality']
        distance = r['distance_from_target']
        
        marker = '🎯' if distance == results[0]['distance_from_target'] else '  '
        
        print(f"{marker} {config_name:<13} {signals_4h:<15} {signals_day:<12.1f} {quality:<10.1f} {distance:.1f}")
    
    print("=" * 80)
    print()
    
    # Get best config
    best = results[0]
    
    print("🏆 RECOMMENDED CONFIGURATION:")
    print("-" * 80)
    print(f"Config: {best['config']['name']}")
    print(f"Expected: {best['signals_per_day_est']:.1f} trades/day")
    print(f"Quality: {best['avg_quality']:.1f} average")
    print()
    print("Parameters:")
    for param, value in best['config'].items():
        if param != 'name':
            print(f"  {param}: {value}")
    print()
    
    # Show comparison to current
    print("CURRENT vs RECOMMENDED:")
    print("-" * 80)
    
    from src.strategies.momentum_trading import get_momentum_trading_strategy
    current = get_momentum_trading_strategy()
    
    params_to_compare = [
        ('min_adx', current.min_adx, best['config']['min_adx']),
        ('min_momentum', current.min_momentum, best['config']['min_momentum']),
        ('min_volume', current.min_volume, best['config']['min_volume']),
        ('min_quality_score', current.min_quality_score, best['config']['min_quality_score'])
    ]
    
    print(f"{'Parameter':<20} {'Current':<15} {'Recommended':<15} {'Change'}")
    print("-" * 80)
    
    for param_name, current_val, recommended_val in params_to_compare:
        change_pct = ((recommended_val - current_val) / current_val * 100) if current_val else 0
        change_str = f"{change_pct:+.0f}%"
        
        print(f"{param_name:<20} {current_val:<15.4f} {recommended_val:<15.4f} {change_str}")
    
    print()
    print("=" * 80)
    
    return best


if __name__ == "__main__":
    best_config = auto_tune_momentum_parameters()
    
    print()
    print("💡 To apply these changes:")
    print("   1. Update momentum_trading.py with recommended values")
    print("   2. Run validate_strategy.py to confirm")
    print("   3. Deploy to cloud")
    print()






















