#!/usr/bin/env python3
"""
14-Day Backtest for All Strategies
Tests each strategy against the past 14 days of market data
Win rate < 50% = FAILURE
"""

import os
import sys
import yaml
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict

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

# Import required modules
from src.core.oanda_client import OandaClient
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy
from src.strategies.ict_ote_strategy import ICTOTEStrategy
from src.core.data_feed import MarketData

def run_strategy_backtest(strategy, instruments, days=14):
    """Run backtest for a single strategy"""
    client = OandaClient()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 BACKTESTING: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Instruments: {', '.join(instruments)}")
    
    # Download historical data
    historical_data = {}
    for instrument in instruments:
        try:
            logger.info(f"  Fetching {instrument}...")
            candles = client.get_candles(
                instrument=instrument,
                granularity='M5',
                count=5000  # ~17 days at M5
            )
            
            if candles:
                historical_data[instrument] = candles
                logger.info(f"    ✅ {len(candles)} candles retrieved")
            else:
                logger.warning(f"    ⚠️ No data for {instrument}")
        except Exception as e:
            logger.error(f"    ❌ Error fetching {instrument}: {e}")
    
    if not historical_data:
        logger.error("❌ No historical data available!")
        return {
            'strategy': strategy.name,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'status': 'FAILURE - No Data'
        }
    
    # Clear price history for backtest
    if hasattr(strategy, 'price_history'):
        strategy.price_history = []
    
    # Track trades
    trades = []
    open_trades = {}
    
    # Create a unified timeline from all instruments
    all_timestamps = set()
    for instrument, candles in historical_data.items():
        for candle in candles:
            all_timestamps.add(candle['time'])
    
    sorted_timestamps = sorted(all_timestamps)
    
    logger.info(f"\n🔄 Processing {len(sorted_timestamps)} timestamps...")
    
    # Process each timestamp
    for i, timestamp in enumerate(sorted_timestamps):
        if i % 500 == 0:
            logger.info(f"  Progress: {i}/{len(sorted_timestamps)} timestamps ({i*100//len(sorted_timestamps)}%)")
        
        # Build market data for all instruments at this timestamp
        market_data_dict = {}
        for instrument, candles in historical_data.items():
            # Find candle for this timestamp
            candle = None
            for c in candles:
                if c['time'] == timestamp:
                    candle = c
                    break
            
            if candle:
                # Update price history
                if hasattr(strategy, 'price_history'):
                    if isinstance(strategy.price_history, dict):
                        if instrument not in strategy.price_history:
                            strategy.price_history[instrument] = []
                        strategy.price_history[instrument].append(float(candle['close']))
                    else:
                        strategy.price_history.append(float(candle['close']))
                
                # Create market data
                price = float(candle['close'])
                market_data_dict[instrument] = MarketData(
                    instrument=instrument,
                    timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                    bid=price - 0.0001,
                    ask=price + 0.0001,
                    spread=0.0002,
                    is_live=False,
                    data_source='backtest',
                    last_update_age=0
                )
        
        # Generate signals
        try:
            signals = strategy.analyze_market(market_data_dict)
            
            # Process new signals
            if signals:
                for signal in signals:
                    if signal and hasattr(signal, 'instrument'):
                        trade_id = f"{signal.instrument}_{timestamp}"
                        if trade_id not in open_trades:
                            open_trades[trade_id] = {
                                'instrument': signal.instrument,
                                'side': signal.side.value if hasattr(signal.side, 'value') else signal.side,
                                'entry_price': signal.entry_price,
                                'stop_loss': signal.stop_loss,
                                'take_profit': signal.take_profit,
                                'entry_time': timestamp,
                                'quality_score': getattr(signal, 'strength', 0)
                            }
        except Exception as e:
            logger.debug(f"Error generating signals at {timestamp}: {e}")
        
        # Check open trades for exits
        to_close = []
        for trade_id, trade in open_trades.items():
            instrument = trade['instrument']
            if instrument in market_data_dict:
                current_price = market_data_dict[instrument].bid
                
                # Check stop loss
                if trade['side'] == 'BUY' or trade['side'] == 'LONG':
                    if current_price <= trade['stop_loss']:
                        trade['exit_price'] = trade['stop_loss']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['stop_loss'] - trade['entry_price']) * 10000
                        trade['status'] = 'loss'
                        trades.append(trade)
                        to_close.append(trade_id)
                    elif current_price >= trade['take_profit']:
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['take_profit'] - trade['entry_price']) * 10000
                        trade['status'] = 'win'
                        trades.append(trade)
                        to_close.append(trade_id)
                else:  # SELL/SHORT
                    if current_price >= trade['stop_loss']:
                        trade['exit_price'] = trade['stop_loss']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['entry_price'] - trade['stop_loss']) * 10000
                        trade['status'] = 'loss'
                        trades.append(trade)
                        to_close.append(trade_id)
                    elif current_price <= trade['take_profit']:
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['entry_price'] - trade['take_profit']) * 10000
                        trade['status'] = 'win'
                        trades.append(trade)
                        to_close.append(trade_id)
        
        # Remove closed trades
        for trade_id in to_close:
            del open_trades[trade_id]
    
    # Calculate results
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['status'] == 'win')
    losses = sum(1 for t in trades if t['status'] == 'loss')
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    # Determine status
    if total_trades == 0:
        status = "FAILURE - No Trades"
    elif win_rate < 50:
        status = "❌ FAILURE"
    else:
        status = "✅ PASS"
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📈 RESULTS: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Wins: {wins}")
    logger.info(f"Losses: {losses}")
    logger.info(f"Win Rate: {win_rate:.2f}%")
    logger.info(f"Status: {status}")
    logger.info(f"{'='*70}\n")
    
    return {
        'strategy': strategy.name,
        'trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'status': status,
        'trade_details': trades
    }

def main():
    """Run backtest for all strategies"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 14-DAY BACKTEST - ALL STRATEGIES")
    logger.info("="*70)
    logger.info("Win Rate Threshold: 50%")
    logger.info("Below 50% = FAILURE ❌")
    logger.info("="*70 + "\n")
    
    # Define strategies to test
    strategies = [
        {
            'name': 'Trump DNA (Momentum Trading)',
            'strategy': MomentumTradingStrategy(),
            'instruments': ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
        },
        {
            'name': 'Gold Scalping',
            'strategy': GoldScalpingStrategy(),
            'instruments': ['XAU_USD']
        },
        {
            'name': 'ICT OTE Strategy',
            'strategy': ICTOTEStrategy(),
            'instruments': ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        }
    ]
    
    # Run backtests
    results = []
    for strategy_config in strategies:
        try:
            result = run_strategy_backtest(
                strategy_config['strategy'],
                strategy_config['instruments']
            )
            results.append(result)
        except Exception as e:
            logger.error(f"❌ Error testing {strategy_config['name']}: {e}")
            results.append({
                'strategy': strategy_config['name'],
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'status': f'FAILURE - Error: {str(e)}'
            })
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("📊 FINAL SUMMARY - 14 DAY BACKTEST")
    logger.info("="*70)
    logger.info(f"{'Strategy':<40} {'Trades':<10} {'Win Rate':<15} {'Status':<15}")
    logger.info("-"*70)
    
    for result in results:
        logger.info(f"{result['strategy']:<40} {result['trades']:<10} {result['win_rate']:.2f}%{'':<10} {result['status']:<15}")
    
    logger.info("="*70)
    
    # Count failures
    failures = [r for r in results if 'FAILURE' in r['status'] or r['win_rate'] < 50]
    passes = [r for r in results if 'FAILURE' not in r['status'] and r['win_rate'] >= 50]
    
    logger.info(f"\n✅ PASSED: {len(passes)}")
    logger.info(f"❌ FAILED: {len(failures)}")
    
    if failures:
        logger.info("\n⚠️ FAILED STRATEGIES:")
        for failure in failures:
            logger.info(f"  - {failure['strategy']}: {failure['win_rate']:.2f}% win rate")
    
    # Save detailed results
    output_file = 'backtest_results_all_strategies.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\n💾 Detailed results saved to {output_file}")

if __name__ == "__main__":
    main()

