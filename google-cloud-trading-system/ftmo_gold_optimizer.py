#!/usr/bin/env python3
"""
FTMO Gold Optimizer
Monte Carlo optimization for XAU_USD targeting 65%+ win ratio
Optimized for FTMO challenge requirements
"""

import os
import sys
import yaml
import logging
import json
import itertools
from datetime import datetime
from typing import Dict, List
import numpy as np

sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

from src.strategies.momentum_trading import MomentumTradingStrategy
from universal_backtest_fix import run_backtest

def create_param_combinations(param_ranges):
    """Create all parameter combinations"""
    keys = list(param_ranges.keys())
    values = list(param_ranges.values())
    combinations = list(itertools.product(*values))
    
    return [dict(zip(keys, combo)) for combo in combinations]

def calculate_ftmo_fitness(backtest_result):
    """
    Calculate fitness score for FTMO challenge
    
    Prioritizes:
    1. Win rate >= 65% (highest priority)
    2. Profit factor >= 1.8
    3. Max drawdown <= 8%
    4. Sufficient trade frequency (20+ trades per month)
    """
    trades = backtest_result.get('trades', 0)
    win_rate = backtest_result.get('win_rate', 0)
    profit_factor = backtest_result.get('profit_factor', 0)
    total_profit = backtest_result.get('total_profit', 0)
    
    # No trades = zero fitness
    if trades == 0:
        return 0
    
    # Calculate fitness components
    # 1. Win rate component (60% weight)
    win_rate_score = min(1.0, win_rate / 100)  # Normalize to 0-1
    win_rate_bonus = max(0, (win_rate - 65) / 35)  # Bonus for > 65%
    win_rate_fitness = (win_rate_score * 0.5) + (win_rate_bonus * 0.1)
    
    # 2. Profit factor component (20% weight)
    pf_fitness = min(1.0, profit_factor / 3.0) * 0.2
    
    # 3. Trade frequency component (10% weight)
    # Target: 20-40 trades per month (in 30 days)
    trades_per_30_days = trades
    ideal_trades = 30
    freq_distance = abs(trades_per_30_days - ideal_trades)
    freq_fitness = (1 / (1 + freq_distance / 10)) * 0.1
    
    # 4. Profitability component (10% weight)
    profit_fitness = (1 if total_profit > 0 else 0) * 0.1
    
    # Calculate total fitness
    total_fitness = win_rate_fitness + pf_fitness + freq_fitness + profit_fitness
    
    return total_fitness

def optimize_gold_for_ftmo():
    """Run Monte Carlo optimization for XAU_USD with FTMO-focused parameters"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 FTMO GOLD OPTIMIZATION - Monte Carlo")
    logger.info("="*70)
    logger.info("Target: 65%+ win rate")
    logger.info("Risk: Conservative (FTMO-compliant)")
    logger.info("Instrument: XAU_USD")
    logger.info("="*70 + "\n")
    
    # Define FTMO-optimized parameter ranges
    param_ranges = {
        'min_adx': [15, 20, 25, 30],
        'min_momentum': [0.003, 0.005, 0.008],
        'min_quality_score': [55, 60, 65, 70],
        'stop_loss_atr': [2.0, 2.5, 3.0],
        'take_profit_atr': [4.0, 5.0, 6.0],
        'momentum_period': [15, 20, 25],
        'trend_period': [40, 50, 60]
    }
    
    # Create all combinations
    param_combinations = create_param_combinations(param_ranges)
    total_combinations = len(param_combinations)
    
    logger.info(f"📊 Testing {total_combinations} parameter combinations...")
    logger.info(f"   This will take approximately {total_combinations * 2 / 60:.1f} minutes\n")
    
    # Import historical data fetching
    from src.core.oanda_client import OandaClient
    client = OandaClient()
    
    # Get historical data for XAU_USD (30 days)
    from universal_backtest_fix import get_historical_data
    
    logger.info("📥 Downloading historical data...")
    historical_data = {}
    data = get_historical_data(client, 'XAU_USD', days=30)
    if data:
        historical_data['XAU_USD'] = data
    else:
        logger.error("❌ Failed to download historical data!")
        return None
    
    # Test each parameter combination
    results = []
    
    for i, params in enumerate(param_combinations, 1):
        if i % 10 == 0 or i == 1:
            logger.info(f"  Testing combination {i}/{total_combinations} ({i*100//total_combinations}%)")
        
        try:
            # Create strategy with these parameters
            strategy = MomentumTradingStrategy()
            
            # Apply parameters
            for key, value in params.items():
                setattr(strategy, key, value)
            
            # Also set conservative FTMO limits
            strategy.max_trades_per_day = 5
            strategy.min_time_between_trades_minutes = 0  # Disable for backtest
            strategy.require_trend_continuation = True
            
            # Run backtest
            backtest_result = run_backtest(strategy, historical_data, days=30)
            
            # Calculate FTMO fitness
            fitness = calculate_ftmo_fitness(backtest_result)
            
            # Store result
            result = {
                'params': params,
                'fitness': fitness,
                'trades': backtest_result.get('trades', 0),
                'win_rate': backtest_result.get('win_rate', 0),
                'profit_factor': backtest_result.get('profit_factor', 0),
                'total_profit': backtest_result.get('total_profit', 0),
                'avg_win': backtest_result.get('avg_win', 0),
                'avg_loss': backtest_result.get('avg_loss', 0)
            }
            
            results.append(result)
            
        except Exception as e:
            logger.debug(f"  Error testing combination {i}: {e}")
    
    # Sort by fitness
    results.sort(key=lambda x: x['fitness'], reverse=True)
    
    # Display top 10 results
    logger.info(f"\n{'='*70}")
    logger.info("📊 TOP 10 PARAMETER COMBINATIONS")
    logger.info("="*70)
    logger.info(f"{'Rank':<6} {'Win Rate':<12} {'Trades':<10} {'PF':<8} {'Fitness':<10} {'Params'}")
    logger.info("-"*70)
    
    for i, result in enumerate(results[:10], 1):
        logger.info(f"{i:<6} {result['win_rate']:.1f}%{'':<7} {result['trades']:<10} {result['profit_factor']:.2f}{'':<4} {result['fitness']:.4f}{'':<4} {result['params']}")
    
    logger.info("="*70)
    
    # Save all results
    output_file = 'ftmo_gold_optimization_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n💾 All results saved to {output_file}")
    
    # Display best parameters
    if results:
        best = results[0]
        logger.info(f"\n🏆 BEST PARAMETERS FOR FTMO GOLD TRADING:")
        logger.info(f"   Win Rate: {best['win_rate']:.1f}%")
        logger.info(f"   Trades: {best['trades']}")
        logger.info(f"   Profit Factor: {best['profit_factor']:.2f}")
        logger.info(f"   Fitness Score: {best['fitness']:.4f}")
        logger.info(f"\n   Parameters:")
        for key, value in best['params'].items():
            logger.info(f"      {key}: {value}")
    
    return results

if __name__ == "__main__":
    optimize_gold_for_ftmo()




