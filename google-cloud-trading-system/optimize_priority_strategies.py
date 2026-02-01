#!/usr/bin/env python3
"""
Optimize TOP PRIORITY strategies first
Trump DNA, 75% WR Champion, Gold Scalping
"""

import os
import sys
import logging
from datetime import datetime
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_optimizer import UniversalOptimizer
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.champion_75wr import UltraSelective75WRChampion
from src.strategies.gold_scalping import GoldScalpingStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


PRIORITY_CONFIGS = [
    {
        'name': 'Trump DNA (Momentum Trading)',
        'class': MomentumTradingStrategy,
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'XAU_USD'],
        'param_ranges': {
            'stop_loss_atr': [2.0, 2.5, 3.0],
            'take_profit_atr': [10.0, 15.0, 20.0],
            'min_adx': [5.0, 8.0, 10.0],
            'min_momentum': [0.0001, 0.0003, 0.0005],
            'momentum_period': [30, 40, 50],
            'trend_period': [80, 100, 120],
            'min_quality_score': [5, 10, 15]
        }
    },
    {
        'name': '75% WR Champion',
        'class': UltraSelective75WRChampion,
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'param_ranges': {
            'stop_loss_atr': [2.0, 3.0],
            'take_profit_atr': [5.0, 15.0],
            'min_adx': [15.0, 25.0],
            'min_momentum': [0.0005, 0.0015],
            'momentum_period': [30, 50],
            'trend_period': [80, 120],
            'min_quality_score': [20, 30]
        }
    },
    {
        'name': 'Gold Scalping',
        'class': GoldScalpingStrategy,
        'instruments': ['XAU_USD'],
        'param_ranges': {
            'stop_loss_atr': [1.5, 3.0],
            'take_profit_atr': [3.0, 10.0],
            'min_adx': [5.0, 15.0],
            'min_momentum': [0.0001, 0.0005],
            'momentum_period': [20, 40],
            'trend_period': [60, 100],
            'min_quality_score': [5, 15]
        }
    }
]


def optimize_priority_strategies():
    """Optimize priority strategies"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 PRIORITY STRATEGY OPTIMIZATION")
    logger.info("="*70)
    logger.info(f"Total Strategies: {len(PRIORITY_CONFIGS)}")
    logger.info(f"Lookback Period: 5 days")
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")
    
    all_results = {}
    start_time = time.time()
    
    for i, config in enumerate(PRIORITY_CONFIGS, 1):
        strategy_start = time.time()
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"# STRATEGY {i}/{len(PRIORITY_CONFIGS)}: {config['name']}")
        logger.info(f"{'#'*70}\n")
        
        try:
            optimizer = UniversalOptimizer(
                strategy_class=config['class'],
                strategy_name=config['name'],
                instruments=config['instruments']
            )
            
            top_results = optimizer.optimize(
                param_ranges=config['param_ranges'],
                days=5,  # 5 days for faster optimization
                top_n=3
            )
            
            all_results[config['name']] = {
                'instruments': config['instruments'],
                'top_results': top_results,
                'optimization_time': time.time() - strategy_start
            }
            
            logger.info(f"\n✅ {config['name']} optimization complete!")
            logger.info(f"   Time taken: {(time.time() - strategy_start)/60:.1f} minutes")
            
        except Exception as e:
            logger.error(f"\n❌ {config['name']} optimization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            all_results[config['name']] = {'error': str(e)}
    
    total_time = time.time() - start_time
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"PRIORITY_STRATEGIES_OPTIMIZATION_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary
    summary_file = f"PRIORITY_OPTIMIZATION_SUMMARY_{timestamp}.md"
    with open(summary_file, 'w') as f:
        f.write(f"# PRIORITY STRATEGIES OPTIMIZATION\n\n")
        f.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Time:** {total_time/60:.1f} minutes\n")
        f.write(f"**Lookback:** 5 days\n\n")
        
        for name, result in all_results.items():
            f.write(f"## {name}\n\n")
            if 'error' in result:
                f.write(f"❌ Error: {result['error']}\n\n")
            elif result.get('top_results'):
                best = result['top_results'][0]
                f.write(f"**Best Parameters:**\n")
                for k, v in best['params'].items():
                    f.write(f"- `{k}` = {v}\n")
                f.write(f"\n**Performance:**\n")
                f.write(f"- Trades: {best['total_trades']}\n")
                f.write(f"- Win Rate: {best['win_rate']:.1f}%\n")
                f.write(f"- P&L: {best['total_pnl']:.5f}\n\n")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ PRIORITY OPTIMIZATIONS COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Total Time: {total_time/60:.1f} minutes")
    logger.info(f"Results: {output_file}")
    logger.info(f"Summary: {summary_file}")
    logger.info(f"{'='*70}\n")


if __name__ == '__main__':
    optimize_priority_strategies()




