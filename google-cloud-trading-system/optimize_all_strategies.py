#!/usr/bin/env python3
"""
Master script to optimize ALL 10 strategies individually
Runs each optimization sequentially and generates comprehensive report
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
from src.strategies.ultra_strict_forex import UltraStrictForexStrategy
from src.strategies.ultra_strict_v2 import UltraStrictV2RegimeAware
from src.strategies.momentum_v2 import MomentumV2Improved
from src.strategies.all_weather_70wr import AllWeatherAdaptive70WR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


STRATEGY_CONFIGS = [
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
    },
    {
        'name': 'Ultra Strict Forex',
        'class': UltraStrictForexStrategy,
        'instruments': ['GBP_USD', 'EUR_USD', 'AUD_USD', 'NZD_USD', 'USD_JPY'],
        'param_ranges': {
            'stop_loss_atr': [2.0, 3.5],
            'take_profit_atr': [5.0, 15.0],
            'min_adx': [10.0, 25.0],
            'min_momentum': [0.0003, 0.001],
            'momentum_period': [30, 50],
            'trend_period': [80, 120],
            'min_quality_score': [15, 25]
        }
    },
    {
        'name': 'Ultra Strict V2',
        'class': UltraStrictV2RegimeAware,
        'instruments': ['EUR_USD', 'USD_JPY', 'AUD_USD'],
        'param_ranges': {
            'stop_loss_atr': [2.0, 3.5],
            'take_profit_atr': [5.0, 15.0],
            'min_adx': [10.0, 25.0],
            'min_momentum': [0.0003, 0.001],
            'momentum_period': [30, 50],
            'trend_period': [80, 120],
            'min_quality_score': [15, 25]
        }
    },
    {
        'name': 'Momentum V2',
        'class': MomentumV2Improved,
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'param_ranges': {
            'stop_loss_atr': [1.5, 3.0],
            'take_profit_atr': [5.0, 20.0],
            'min_adx': [5.0, 15.0],
            'min_momentum': [0.0001, 0.001],
            'momentum_period': [30, 50],
            'trend_period': [60, 100],
            'min_quality_score': [10, 20]
        }
    },
    {
        'name': 'All-Weather 70% WR',
        'class': AllWeatherAdaptive70WR,
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'param_ranges': {
            'stop_loss_atr': [2.0, 3.0],
            'take_profit_atr': [5.0, 15.0],
            'min_adx': [10.0, 20.0],
            'min_momentum': [0.0003, 0.001],
            'momentum_period': [30, 50],
            'trend_period': [80, 120],
            'min_quality_score': [15, 25]
        }
    }
]


def optimize_all_strategies():
    """Optimize all strategies individually"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 COMPREHENSIVE STRATEGY OPTIMIZATION")
    logger.info("="*70)
    logger.info(f"Total Strategies: {len(STRATEGY_CONFIGS)}")
    logger.info(f"Lookback Period: 7 days")
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")
    
    all_results = {}
    start_time = time.time()
    
    for i, config in enumerate(STRATEGY_CONFIGS, 1):
        strategy_start = time.time()
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"# STRATEGY {i}/{len(STRATEGY_CONFIGS)}: {config['name']}")
        logger.info(f"{'#'*70}\n")
        
        try:
            optimizer = UniversalOptimizer(
                strategy_class=config['class'],
                strategy_name=config['name'],
                instruments=config['instruments']
            )
            
            top_results = optimizer.optimize(
                param_ranges=config['param_ranges'],
                days=7,
                top_n=5
            )
            
            all_results[config['name']] = {
                'instruments': config['instruments'],
                'top_results': top_results,
                'optimization_time': time.time() - strategy_start
            }
            
            logger.info(f"\n✅ {config['name']} optimization complete!")
            logger.info(f"   Time taken: {time.time() - strategy_start:.1f} seconds")
            
        except Exception as e:
            logger.error(f"\n❌ {config['name']} optimization failed: {str(e)}")
            all_results[config['name']] = {'error': str(e)}
    
    total_time = time.time() - start_time
    
    # Save comprehensive results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ALL_STRATEGIES_OPTIMIZATION_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ ALL OPTIMIZATIONS COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Total Time: {total_time/60:.1f} minutes")
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"{'='*70}\n")
    
    # Generate summary report
    generate_summary_report(all_results, output_file)
    
    return all_results


def generate_summary_report(all_results, json_file):
    """Generate human-readable summary report"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"OPTIMIZATION_SUMMARY_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write("# COMPREHENSIVE STRATEGY OPTIMIZATION REPORT\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Lookback Period:** 7 days (Oct 10-17, 2025)\n")
        f.write(f"**Full Data:** {json_file}\n\n")
        f.write("="*70 + "\n\n")
        
        for strategy_name, result in all_results.items():
            f.write(f"## {strategy_name}\n\n")
            
            if 'error' in result:
                f.write(f"❌ **Optimization Failed:** {result['error']}\n\n")
                continue
            
            f.write(f"**Instruments:** {', '.join(result['instruments'])}\n")
            f.write(f"**Optimization Time:** {result['optimization_time']:.1f} seconds\n\n")
            
            if result['top_results']:
                best = result['top_results'][0]
                
                f.write("### 🏆 Best Configuration\n\n")
                f.write("**Parameters:**\n")
                for param, value in best['params'].items():
                    f.write(f"- `{param}`: {value}\n")
                
                f.write(f"\n**Performance:**\n")
                f.write(f"- Total Trades: {best['total_trades']}\n")
                f.write(f"- Win Rate: {best['win_rate']:.1f}%\n")
                f.write(f"- Wins: {best['win_count']} | Losses: {best['loss_count']}\n")
                f.write(f"- Total P&L: {best['total_pnl']:.5f}\n")
                f.write(f"- Avg Win: {best['avg_win']:.5f}\n")
                f.write(f"- Avg Loss: {best['avg_loss']:.5f}\n")
                f.write(f"- Score: {best['score']:.2f}\n\n")
                
                # Trade breakdown by pair
                if 'trades' in best:
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
                    
                    f.write("**Breakdown by Pair:**\n\n")
                    for pair, stats in sorted(pair_stats.items()):
                        total = stats['wins'] + stats['losses']
                        wr = (stats['wins'] / total * 100) if total > 0 else 0
                        f.write(f"- **{pair}**: {total} trades, {wr:.1f}% WR, P&L: {stats['total_pnl']:.5f}\n")
                
                f.write("\n")
            else:
                f.write("⚠️ No valid results found\n\n")
            
            f.write("-"*70 + "\n\n")
    
    logger.info(f"📄 Summary report saved to: {report_file}")


if __name__ == '__main__':
    optimize_all_strategies()

