#!/usr/bin/env python3
"""
Optimize 75% Win Rate Champion Strategy
"""

import os
import sys
import logging
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_optimizer import UniversalOptimizer
from src.strategies.champion_75wr import UltraSelective75WRChampion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_champion_75wr():
    """Optimize 75% WR Champion strategy"""
    
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
    
    optimizer = UniversalOptimizer(
        strategy_class=UltraSelective75WRChampion,
        strategy_name="75% WR Champion",
        instruments=instruments
    )
    
    # Parameter ranges for ultra-selective strategy
    param_ranges = {
        'stop_loss_atr': [2.0, 2.5, 3.0, 3.5],
        'take_profit_atr': [5.0, 7.5, 10.0, 15.0],
        'min_adx': [15.0, 20.0, 25.0, 30.0],
        'min_momentum': [0.0005, 0.001, 0.0015, 0.002],
        'momentum_period': [30, 40, 50],
        'trend_period': [80, 100, 120],
        'min_quality_score': [20, 25, 30, 35]
    }
    
    logger.info("\n" + "="*70)
    logger.info("75% WR CHAMPION OPTIMIZATION")
    logger.info("="*70)
    logger.info(f"Instruments: {', '.join(instruments)}")
    logger.info(f"Strategy Focus: Ultra-selective, high win rate")
    logger.info("="*70 + "\n")
    
    # Run optimization
    top_results = optimizer.optimize(param_ranges, days=7, top_n=10)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"CHAMPION_75WR_OPTIMIZATION_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(top_results, f, indent=2, default=str)
    
    logger.info(f"\n✅ Results saved to {output_file}")
    
    # Print best configuration
    if top_results:
        best = top_results[0]
        logger.info("\n" + "="*70)
        logger.info("🏆 BEST CONFIGURATION FOR 75% WR CHAMPION")
        logger.info("="*70)
        logger.info(f"\nParameters to implement:")
        for param, value in best['params'].items():
            logger.info(f"  self.{param} = {value}")
        logger.info(f"\nExpected Performance:")
        logger.info(f"  Total Trades: {best['total_trades']}")
        logger.info(f"  Win Rate: {best['win_rate']:.1f}%")
        logger.info(f"  Total P&L: {best['total_pnl']:.5f}")
        logger.info(f"  Wins: {best['win_count']} | Losses: {best['loss_count']}")
        logger.info("="*70 + "\n")
    
    return top_results


if __name__ == '__main__':
    optimize_champion_75wr()




