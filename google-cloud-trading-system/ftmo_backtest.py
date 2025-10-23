#!/usr/bin/env python3
"""
FTMO Backtest Script
Simulates trading with strict FTMO challenge rules
Tests strategies to ensure they can pass FTMO Phase 1 & 2
"""

import os
import sys
import yaml
import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any
import pandas as pd
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

# Import required modules
from src.core.oanda_client import OandaClient
from src.core.data_feed import MarketData
from src.core.ftmo_risk_manager import FTMORiskManager
from src.strategies.momentum_trading import MomentumTradingStrategy

def get_historical_data_ftmo(client, instrument, days=30, granularity='M5'):
    """Get historical data for FTMO backtest"""
    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=days)
    
    try:
        logger.info(f"  Fetching {instrument} ({granularity}) data for {days} days...")
        
        # OANDA max count is 5000 candles
        # For >17 days with M5 (288 candles/day), use H1 instead
        if days > 17 and granularity == 'M5':
            granularity = 'H1'
            logger.info(f"    Using H1 granularity for {days} days (avoids OANDA limit)")
        
        # Calculate count needed
        candles_per_day = 288 if granularity == 'M5' else 24 if granularity == 'H1' else 1
        count = min(5000, days * candles_per_day)
        
        response = client.get_candles(
            instrument=instrument,
            granularity=granularity,
            count=count
        )
        
        if not response or 'candles' not in response:
            logger.error(f"    ❌ No data returned for {instrument}")
            return None
        
        candles = response['candles']
        logger.info(f"    ✅ {len(candles)} candles retrieved")
        
        # Process candles
        processed_candles = []
        for candle in candles:
            try:
                time_str = candle.get('time', None)
                if not time_str:
                    continue
                
                timestamp = datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                timestamp = pytz.UTC.localize(timestamp)
                
                # Extract bid/ask prices
                if 'bid' in candle and isinstance(candle['bid'], dict):
                    bid_close = float(candle['bid'].get('c', 0))
                else:
                    continue
                    
                if 'ask' in candle and isinstance(candle['ask'], dict):
                    ask_close = float(candle['ask'].get('c', 0))
                else:
                    continue
                
                mid_close = (bid_close + ask_close) / 2
                
                processed_candles.append({
                    'timestamp': timestamp,
                    'bid_close': bid_close,
                    'ask_close': ask_close,
                    'mid_close': mid_close,
                    'volume': candle.get('volume', 0),
                    'complete': candle.get('complete', False)
                })
            except Exception as e:
                continue
        
        filtered_candles = [
            c for c in processed_candles 
            if start_date <= c['timestamp'] <= end_date
        ]
        
        logger.info(f"    ✅ {len(filtered_candles)} candles in date range")
        return filtered_candles
        
    except Exception as e:
        logger.error(f"    ❌ Error fetching {instrument}: {e}")
        return None

def create_market_data_ftmo(candle, instrument):
    """Create MarketData object from processed candle"""
    try:
        return MarketData(
            pair=instrument,
            bid=candle['bid_close'],
            ask=candle['ask_close'],
            timestamp=candle['timestamp'].isoformat(),
            spread=candle['ask_close'] - candle['bid_close'],
            is_live=False,
            data_source='backtest',
            last_update_age=0,
            volatility_score=0.0,
            regime='unknown',
            correlation_risk=0.0,
            confidence=1.0,
            validation_status='valid'
        )
    except Exception as e:
        logger.error(f"Error creating MarketData: {e}")
        return None

def run_ftmo_backtest(strategy, instruments, phase=1, days=30):
    """Run FTMO-compliant backtest"""
    client = OandaClient()
    
    # Initialize FTMO risk manager
    ftmo_rm = FTMORiskManager(initial_balance=100000, phase=phase)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 FTMO PHASE {phase} BACKTEST: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Period: {days} days")
    logger.info(f"Instruments: {', '.join(instruments)}")
    logger.info(f"Target: {ftmo_rm.profit_target*100}% (${ftmo_rm.account.initial_balance * ftmo_rm.profit_target:,.2f})")
    
    # Download historical data
    historical_data = {}
    for instrument in instruments:
        data = get_historical_data_ftmo(client, instrument, days)
        if data:
            historical_data[instrument] = data
    
    if not historical_data:
        logger.error("❌ No historical data available!")
        return None
    
    # Clear and prefill price history
    if hasattr(strategy, 'price_history'):
        if isinstance(strategy.price_history, dict):
            for instrument in instruments:
                strategy.price_history[instrument] = []
                # Prefill first 100 candles
                if instrument in historical_data and len(historical_data[instrument]) >= 100:
                    for candle in historical_data[instrument][:100]:
                        strategy.price_history[instrument].append(candle['mid_close'])
                    logger.info(f"  ✅ Prefilled {len(strategy.price_history[instrument])} bars for {instrument}")
    
    # Track trades
    trades = []
    open_trades = {}
    
    # Create unified timeline
    all_timestamps = set()
    for instrument, candles in historical_data.items():
        for candle in candles:
            all_timestamps.add(candle['timestamp'])
    
    sorted_timestamps = sorted(all_timestamps)
    
    # Skip first 100 timestamps for indicator calculation
    start_idx = 100
    if len(sorted_timestamps) <= start_idx:
        logger.error("❌ Insufficient data for backtest")
        return None
    
    logger.info(f"🔄 Running FTMO backtest ({len(sorted_timestamps)} timestamps)...")
    
    # Process each timestamp
    for i, timestamp in enumerate(sorted_timestamps[start_idx:], start=start_idx):
        if i % 500 == 0:
            report = ftmo_rm.get_status_report()
            logger.info(f"  Progress: {i}/{len(sorted_timestamps)} ({i*100//len(sorted_timestamps)}%) - Balance: ${report['balance']:,.2f}, Profit: {report['profit_pct']:+.2f}%")
        
        # Build market data
        market_data_dict = {}
        for instrument, candles in historical_data.items():
            matching_candles = [c for c in candles if c['timestamp'] == timestamp]
            if matching_candles:
                candle = matching_candles[0]
                market_data = create_market_data_ftmo(candle, instrument)
                if market_data:
                    market_data_dict[instrument] = market_data
        
        # Generate signals
        try:
            signals = strategy.analyze_market(market_data_dict)
            
            # Process new signals
            if signals:
                for signal in signals:
                    if signal and hasattr(signal, 'instrument'):
                        instrument = getattr(signal, 'instrument', None)
                        side = getattr(signal, 'side', None)
                        if hasattr(side, 'value'):
                            side = side.value
                        entry_price = getattr(signal, 'entry_price', None)
                        stop_loss = getattr(signal, 'stop_loss', None)
                        take_profit = getattr(signal, 'take_profit', None)
                        
                        if instrument and side and entry_price and stop_loss and take_profit:
                            # Validate with FTMO risk manager
                            is_valid, reason, position_size = ftmo_rm.validate_trade(
                                entry_price, stop_loss, take_profit, instrument, len(open_trades)
                            )
                            
                            if is_valid:
                                trade_id = f"{instrument}_{timestamp}"
                                open_trades[trade_id] = {
                                    'instrument': instrument,
                                    'side': side,
                                    'entry_price': entry_price,
                                    'stop_loss': stop_loss,
                                    'take_profit': take_profit,
                                    'entry_time': timestamp,
                                    'units': position_size
                                }
                                
                                # Record entry with FTMO manager
                                ftmo_rm.record_trade_entry(
                                    instrument, side, entry_price, stop_loss, take_profit, position_size
                                )
        except Exception as e:
            pass
        
        # Check open trades for exits
        to_close = []
        for trade_id, trade in open_trades.items():
            instrument = trade['instrument']
            if instrument in market_data_dict:
                current_price = market_data_dict[instrument].bid if trade['side'] == 'SELL' else market_data_dict[instrument].ask
                
                # Check stop loss and take profit
                hit_sl = False
                hit_tp = False
                
                if trade['side'] in ['BUY', 'LONG']:
                    if current_price <= trade['stop_loss']:
                        hit_sl = True
                        exit_price = trade['stop_loss']
                    elif current_price >= trade['take_profit']:
                        hit_tp = True
                        exit_price = trade['take_profit']
                else:  # SELL/SHORT
                    if current_price >= trade['stop_loss']:
                        hit_sl = True
                        exit_price = trade['stop_loss']
                    elif current_price <= trade['take_profit']:
                        hit_tp = True
                        exit_price = trade['take_profit']
                
                if hit_sl or hit_tp:
                    # Calculate P&L
                    if trade['side'] in ['BUY', 'LONG']:
                        profit_loss = (exit_price - trade['entry_price']) * trade['units']
                    else:
                        profit_loss = (trade['entry_price'] - exit_price) * trade['units']
                    
                    # Record exit
                    trade['exit_price'] = exit_price
                    trade['exit_time'] = timestamp
                    trade['profit_loss'] = profit_loss
                    trade['status'] = 'win' if hit_tp else 'loss'
                    trades.append(trade)
                    to_close.append(trade_id)
                    
                    # Update FTMO account
                    ftmo_rm.record_trade_exit(profit_loss, hit_tp)
                    
                    # Check if FTMO limits breached
                    can_continue, _ = ftmo_rm.can_trade()
                    if not can_continue:
                        logger.warning("⚠️ FTMO limit breached, stopping backtest")
                        break
        
        # Remove closed trades
        for trade_id in to_close:
            del open_trades[trade_id]
        
        # Check if FTMO target reached
        report = ftmo_rm.get_status_report()
        if report['status'] == 'PASSED':
            logger.info("🎉 FTMO target reached!")
            break
        elif report['status'] == 'FAILED':
            logger.warning("❌ FTMO challenge failed!")
            break
    
    # Close remaining open trades
    for trade_id, trade in open_trades.items():
        instrument = trade['instrument']
        if instrument in historical_data and historical_data[instrument]:
            last_candle = historical_data[instrument][-1]
            last_price = last_candle['mid_close']
            
            if trade['side'] in ['BUY', 'LONG']:
                profit_loss = (last_price - trade['entry_price']) * trade['units']
            else:
                profit_loss = (trade['entry_price'] - last_price) * trade['units']
            
            trade['exit_price'] = last_price
            trade['exit_time'] = sorted_timestamps[-1]
            trade['profit_loss'] = profit_loss
            trade['status'] = 'win' if profit_loss > 0 else 'loss'
            trades.append(trade)
            
            ftmo_rm.record_trade_exit(profit_loss, profit_loss > 0)
    
    # Generate final report
    final_report = ftmo_rm.get_status_report()
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📈 FTMO PHASE {phase} RESULTS: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Final Balance: ${final_report['balance']:,.2f}")
    logger.info(f"Profit: ${final_report['profit']:+,.2f} ({final_report['profit_pct']:+.2f}%)")
    logger.info(f"Target: ${final_report['target_profit']:,.2f} ({final_report['progress_to_target']:.1f}% complete)")
    logger.info(f"Trading Days: {final_report['trading_days']}")
    logger.info(f"Total Trades: {final_report['total_trades']}")
    logger.info(f"Win Rate: {final_report['wins']}/{final_report['total_trades']} ({final_report['win_rate']:.1f}%)")
    logger.info(f"Max Consecutive Losses: {final_report['max_consecutive_losses']}")
    logger.info(f"Max Total Drawdown: {final_report['total_drawdown_pct']:.2f}%")
    logger.info(f"Status: {final_report['status']}")
    logger.info(f"{'='*70}\n")
    
    # Calculate additional metrics
    if trades:
        win_trades = [t for t in trades if t['status'] == 'win']
        loss_trades = [t for t in trades if t['status'] == 'loss']
        
        avg_win = sum(t['profit_loss'] for t in win_trades) / len(win_trades) if win_trades else 0
        avg_loss = sum(t['profit_loss'] for t in loss_trades) / len(loss_trades) if loss_trades else 0
        
        profit_factor = abs(sum(t['profit_loss'] for t in win_trades) / sum(t['profit_loss'] for t in loss_trades)) if loss_trades and sum(t['profit_loss'] for t in loss_trades) != 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        daily_returns = []
        current_day_pnl = 0
        last_date = None
        
        for trade in sorted(trades, key=lambda x: x['exit_time']):
            trade_date = trade['exit_time'].date()
            if last_date and trade_date != last_date:
                daily_returns.append(current_day_pnl)
                current_day_pnl = 0
            current_day_pnl += trade['profit_loss']
            last_date = trade_date
        
        if current_day_pnl != 0:
            daily_returns.append(current_day_pnl)
        
        if daily_returns:
            sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        logger.info(f"Additional Metrics:")
        logger.info(f"  Average Win: ${avg_win:+,.2f}")
        logger.info(f"  Average Loss: ${avg_loss:+,.2f}")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    
    return {
        'strategy': strategy.name,
        'phase': phase,
        'ftmo_report': final_report,
        'trades': trades,
        'total_trades': len(trades),
        'win_rate': final_report['win_rate'],
        'profit_factor': profit_factor if trades else 0,
        'sharpe_ratio': sharpe_ratio if trades else 0
    }

def main():
    """Run FTMO backtest for all strategies"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 FTMO CHALLENGE BACKTEST")
    logger.info("="*70)
    logger.info("Phase 1 Target: 10% profit")
    logger.info("Max Daily Loss: 5%")
    logger.info("Max Total Loss: 10%")
    logger.info("="*70 + "\n")
    
    # Test Momentum Strategy on Gold first
    momentum_strategy = MomentumTradingStrategy()
    
    # Configure for conservative FTMO trading
    momentum_strategy.min_adx = 20.0
    momentum_strategy.min_momentum = 0.005
    momentum_strategy.min_quality_score = 65
    momentum_strategy.momentum_period = 20
    momentum_strategy.trend_period = 50
    momentum_strategy.stop_loss_atr = 2.5
    momentum_strategy.take_profit_atr = 5.0
    momentum_strategy.max_trades_per_day = 5
    momentum_strategy.min_time_between_trades_minutes = 60
    momentum_strategy.require_trend_continuation = True
    
    logger.info("📊 Strategy Configuration:")
    logger.info(f"  min_adx: {momentum_strategy.min_adx}")
    logger.info(f"  min_momentum: {momentum_strategy.min_momentum}")
    logger.info(f"  min_quality_score: {momentum_strategy.min_quality_score}")
    logger.info(f"  R:R ratio: 1:{momentum_strategy.take_profit_atr/momentum_strategy.stop_loss_atr:.1f}")
    
    # Run backtest
    result = run_ftmo_backtest(momentum_strategy, ['XAU_USD'], phase=1, days=30)
    
    if result:
        # Save results
        output_file = 'ftmo_backtest_results.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\n💾 Results saved to {output_file}")
        
        # Send summary to Telegram
        try:
            from src.core.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            
            message = f"""<b>FTMO Phase {result['phase']} Backtest Complete</b>

<b>Strategy:</b> {result['strategy']}
<b>Result:</b> {result['ftmo_report']['status']}

<b>Performance:</b>
Balance: ${result['ftmo_report']['balance']:,.2f}
Profit: ${result['ftmo_report']['profit']:+,.2f} ({result['ftmo_report']['profit_pct']:+.2f}%)
Target Progress: {result['ftmo_report']['progress_to_target']:.1f}%

<b>Stats:</b>
Trades: {result['total_trades']}
Win Rate: {result['win_rate']:.1f}%
Profit Factor: {result.get('profit_factor', 0):.2f}
Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}
Trading Days: {result['ftmo_report']['trading_days']}

<b>Drawdown:</b>
Max Total DD: {result['ftmo_report']['total_drawdown_pct']:.2f}%
Max Consecutive Losses: {result['ftmo_report']['max_consecutive_losses']}
"""
            
            notifier.send_system_status(message)
            logger.info("✅ Summary sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send Telegram update: {e}")

if __name__ == "__main__":
    main()

