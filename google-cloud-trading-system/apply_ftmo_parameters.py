#!/usr/bin/env python3
"""
Apply FTMO-Optimized Parameters
Applies the best parameters from optimization to the strategy files
"""

import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_optimization_results():
    """Load optimization results"""
    results_file = 'ftmo_optimization_results.json'
    
    if not os.path.exists(results_file):
        logger.error(f"❌ Results file not found: {results_file}")
        return None
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    logger.info(f"✅ Loaded {len(results)} optimization results")
    return results

def apply_parameters_to_strategy(params, strategy_file, instrument='XAU_USD'):
    """Apply parameters to strategy file"""
    logger.info(f"\n📝 Applying parameters to {strategy_file}...")
    logger.info(f"   Instrument: {instrument}")
    logger.info(f"   Parameters:")
    for key, value in params.items():
        logger.info(f"      {key} = {value}")
    
    # Read strategy file
    with open(strategy_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = f"{strategy_file}.ftmo_backup"
    with open(backup_file, 'w') as f:
        f.write(content)
    logger.info(f"   ✅ Backup created: {backup_file}")
    
    # Update parameters in __init__ method
    # This is a simplified version - would need more sophisticated parsing for production
    replacements = {
        'min_adx': f'self.min_adx = {params.get("min_adx", 20.0)}',
        'min_momentum': f'self.min_momentum = {params.get("min_momentum", 0.005)}',
        'min_quality_score': f'self.min_quality_score = {params.get("min_quality_score", 65)}',
        'stop_loss_atr': f'self.stop_loss_atr = {params.get("stop_loss_atr", 2.5)}',
        'take_profit_atr': f'self.take_profit_atr = {params.get("take_profit_atr", 5.0)}',
        'momentum_period': f'self.momentum_period = {params.get("momentum_period", 20)}',
        'trend_period': f'self.trend_period = {params.get("trend_period", 50)}'
    }
    
    logger.info(f"   ✅ Parameters prepared for application")
    logger.info(f"   ⚠️  Manual verification recommended before deployment")
    
    return replacements

def main():
    """Apply FTMO-optimized parameters"""
    logger.info("\n" + "="*70)
    logger.info("🎯 APPLYING FTMO-OPTIMIZED PARAMETERS")
    logger.info("="*70 + "\n")
    
    # Load results
    results = load_optimization_results()
    
    if not results:
        logger.error("❌ No optimization results available")
        return
    
    # Get best result
    best = results[0]
    
    logger.info(f"🏆 BEST CONFIGURATION:")
    logger.info(f"   Win Rate: {best['win_rate']:.1f}%")
    logger.info(f"   Total Trades: {best['trades']}")
    logger.info(f"   Profit: {best['profit_pips']:+.0f} pips")
    logger.info(f"   Fitness: {best['fitness']:.4f}")
    
    # Check if it meets 65% threshold
    if best['win_rate'] < 65:
        logger.warning(f"\n⚠️  WARNING: Best win rate ({best['win_rate']:.1f}%) is below 65% target")
        logger.warning(f"   Consider:")
        logger.warning(f"   - Testing on different time period")
        logger.warning(f"   - Adjusting parameter ranges")
        logger.warning(f"   - Using hybrid manual/auto approach")
        
        # Find best >= 60%
        good_results = [r for r in results if r['win_rate'] >= 60]
        if good_results:
            logger.info(f"\n   Found {len(good_results)} configurations with 60%+ win rate")
            logger.info(f"   Using best available: {good_results[0]['win_rate']:.1f}%")
            best = good_results[0]
    
    # Apply to momentum trading strategy
    strategy_file = 'src/strategies/momentum_trading.py'
    replacements = apply_parameters_to_strategy(
        best['params'],
        strategy_file,
        'XAU_USD'
    )
    
    # Create configuration file
    config_file = 'FTMO_OPTIMIZED_PARAMETERS.json'
    config = {
        'instrument': 'XAU_USD',
        'optimization_date': datetime.now().isoformat(),
        'parameters': best['params'],
        'expected_performance': {
            'win_rate': best['win_rate'],
            'trades_per_14_days': best['trades'],
            'profit_pips': best['profit_pips'],
            'fitness_score': best['fitness']
        },
        'ftmo_compliance': {
            'max_risk_per_trade': 0.005,
            'max_daily_trades': 5,
            'max_concurrent_positions': 2,
            'min_risk_reward': 2.0
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"\n✅ Configuration saved to {config_file}")
    logger.info(f"\n📋 NEXT STEPS:")
    logger.info(f"   1. Review {config_file}")
    logger.info(f"   2. Manually update {strategy_file} with parameters")
    logger.info(f"   3. Run validation backtest")
    logger.info(f"   4. Deploy to Google Cloud")
    logger.info(f"\n" + "="*70)

if __name__ == "__main__":
    main()

