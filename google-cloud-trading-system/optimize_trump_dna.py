#!/usr/bin/env python3
"""
Optimize Trump DNA (Momentum Trading) Strategy for ALL pairs
"""

import os
import sys
import logging
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_optimizer import UniversalOptimizer
from src.strategies.momentum_trading import MomentumTradingStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_trump_dna():
    """Optimize Trump DNA strategy for all major pairs + Gold"""
    
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'XAU_USD']
    
    optimizer = UniversalOptimizer(
        strategy_class=MomentumTradingStrategy,
        strategy_name="Trump DNA (Momentum Trading)",
        instruments=instruments
    )
    
    # Parameter ranges to test
    param_ranges = {
        'stop_loss_atr': [1.5, 2.0, 2.5, 3.0, 3.5],
        'take_profit_atr': [5.0, 10.0, 15.0, 20.0, 25.0],
        'min_adx': [5.0, 8.0, 10.0, 15.0, 20.0],
        'min_momentum': [0.0001, 0.0003, 0.0005, 0.001, 0.002],
        'momentum_period': [20, 30, 40, 50, 60],
        'trend_period': [60, 80, 100, 120],
        'min_quality_score': [5, 10, 15, 20, 25]
    }
    
    logger.info("\n" + "="*70)
    logger.info("TRUMP DNA OPTIMIZATION - ALL PAIRS")
    logger.info("="*70)
    logger.info(f"Instruments: {', '.join(instruments)}")
    logger.info(f"Lookback: 7 days (168 hours)")
    logger.info("="*70 + "\n")
    
    # Run optimization
    top_results = optimizer.optimize(param_ranges, days=7, top_n=10)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"TRUMP_DNA_OPTIMIZATION_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(top_results, f, indent=2, default=str)
    
    logger.info(f"\n✅ Results saved to {output_file}")
    
    # Print best configuration
    if top_results:
        best = top_results[0]
        logger.info("\n" + "="*70)
        logger.info("🏆 BEST CONFIGURATION FOR TRUMP DNA")
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
        
        # Show trade breakdown by pair
        if 'trades' in best:
            logger.info("\n" + "="*70)
            logger.info("TRADE BREAKDOWN BY PAIR")
            logger.info("="*70)
            
            pair_stats = {}
            for trade in best['trades']:
                pair = trade['pair']
                if pair not in pair_stats:
                    pair_stats[pair] = {'wins': 0, 'losses': 0, 'total_pnl': 0}
                
                if trade['result'] == 'win':
                    pair_stats[pair]['wins'] += 1
                else:
                    pair_stats[pair]['losses'] += 1
                pair_stats[pair]['total_pnl'] += trade['pnl']
            
            for pair, stats in sorted(pair_stats.items()):
                total = stats['wins'] + stats['losses']
                wr = (stats['wins'] / total * 100) if total > 0 else 0
                logger.info(f"\n{pair}:")
                logger.info(f"  Trades: {total} | Wins: {stats['wins']} | Losses: {stats['losses']}")
                logger.info(f"  Win Rate: {wr:.1f}%")
                logger.info(f"  P&L: {stats['total_pnl']:.5f}")
    
    return top_results


if __name__ == '__main__':
    optimize_trump_dna()




