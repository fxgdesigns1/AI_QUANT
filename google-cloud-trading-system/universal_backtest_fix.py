#!/usr/bin/env python3
"""
Universal Backtest Fix

This script provides a universal fix for the backtest system to properly handle OANDA data format.
It can be applied to any backtest script in the system.

Key fixes:
1. Properly handles bid/ask data format from OANDA API
2. Correctly creates MarketData objects with the right field names
3. Properly pre-fills price history with float values
4. Handles timezone-aware datetime comparisons
5. Ensures proper error handling and logging
"""

import os
import sys
import yaml
import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any, Optional

sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import required modules
from src.core.oanda_client import OandaClient
from src.core.data_feed import MarketData

def load_credentials():
    """Load OANDA credentials from config files"""
    try:
        with open('app.yaml') as f:
            config = yaml.safe_load(f)
            os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
        with open('accounts.yaml') as f:
            accounts = yaml.safe_load(f)
            os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
        logger.info("✅ Credentials loaded")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load credentials: {e}")
        return False

def get_historical_data(client, instrument, days=14, granularity='M5'):
    """Get historical data from OANDA with proper error handling for the actual data format"""
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
        
        # Use the correct method name
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
        
        # Process candles into a list of dictionaries with standardized format
        processed_candles = []
        for candle in candles:
            try:
                # Extract time
                time_str = candle.get('time', None)
                if not time_str:
                    continue
                
                # Convert time string to datetime with UTC timezone
                timestamp = datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                timestamp = pytz.UTC.localize(timestamp)
                
                # Extract bid/ask prices
                if 'bid' in candle and isinstance(candle['bid'], dict):
                    bid_open = float(candle['bid'].get('o', 0))
                    bid_high = float(candle['bid'].get('h', 0))
                    bid_low = float(candle['bid'].get('l', 0))
                    bid_close = float(candle['bid'].get('c', 0))
                else:
                    continue
                    
                if 'ask' in candle and isinstance(candle['ask'], dict):
                    ask_open = float(candle['ask'].get('o', 0))
                    ask_high = float(candle['ask'].get('h', 0))
                    ask_low = float(candle['ask'].get('l', 0))
                    ask_close = float(candle['ask'].get('c', 0))
                else:
                    continue
                
                # Calculate mid prices
                mid_open = (bid_open + ask_open) / 2
                mid_high = (bid_high + ask_high) / 2
                mid_low = (bid_low + ask_low) / 2
                mid_close = (bid_close + ask_close) / 2
                
                # Create standardized candle dictionary
                processed_candle = {
                    'timestamp': timestamp,
                    'bid_open': bid_open,
                    'bid_high': bid_high,
                    'bid_low': bid_low,
                    'bid_close': bid_close,
                    'ask_open': ask_open,
                    'ask_high': ask_high,
                    'ask_low': ask_low,
                    'ask_close': ask_close,
                    'mid_open': mid_open,
                    'mid_high': mid_high,
                    'mid_low': mid_low,
                    'mid_close': mid_close,
                    'volume': candle.get('volume', 0),
                    'complete': candle.get('complete', False)
                }
                
                processed_candles.append(processed_candle)
            except Exception as e:
                logger.warning(f"    ⚠️ Error processing candle: {e}")
                continue
        
        if not processed_candles:
            logger.error(f"    ❌ No valid candles processed for {instrument}")
            return None
            
        # Filter by date range
        filtered_candles = [
            c for c in processed_candles 
            if start_date <= c['timestamp'] <= end_date
        ]
        
        logger.info(f"    ✅ {len(filtered_candles)} candles in date range")
        return filtered_candles
        
    except Exception as e:
        logger.error(f"    ❌ Error fetching {instrument}: {e}")
        return None

def create_market_data(candle, instrument):
    """Create MarketData object from a processed candle dictionary"""
    try:
        # Create MarketData object with the correct field names
        market_data = MarketData(
            pair=instrument,  # Use 'pair' instead of 'instrument'
            bid=candle['bid_close'],
            ask=candle['ask_close'],
            timestamp=candle['timestamp'].isoformat(),  # Convert to ISO format string
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
        
        return market_data
    except Exception as e:
        logger.error(f"Error creating MarketData: {e}")
        return None

def prefill_strategy_price_history(strategy, historical_data, instrument, bars=100):
    """Prefill strategy price history with historical data"""
    if not historical_data or not historical_data[instrument]:
        return
        
    candles = historical_data[instrument]
    if len(candles) < bars:
        bars = len(candles)
        
    # Get the first 'bars' candles for prefilling
    prefill_data = candles[:bars]
    
    # Add to strategy price history
    if hasattr(strategy, 'price_history'):
        if isinstance(strategy.price_history, dict):
            strategy.price_history[instrument] = []
            for candle in prefill_data:
                # Use mid_close for price history
                strategy.price_history[instrument].append(candle['mid_close'])
            logger.info(f"  ✅ Prefilled {len(strategy.price_history[instrument])} bars of price history for {instrument}")
        else:
            strategy.price_history = []
            for candle in prefill_data:
                # Use mid_close for price history
                strategy.price_history.append(candle['mid_close'])
            logger.info(f"  ✅ Prefilled {len(strategy.price_history)} bars of price history")

def run_backtest(strategy, historical_data, days=14):
    """Run a backtest using the fixed data format"""
    # Calculate date range
    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 BACKTESTING: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Instruments: {', '.join(historical_data.keys())}")
    
    # Clear price history for backtest
    if hasattr(strategy, 'price_history'):
        if isinstance(strategy.price_history, dict):
            for instrument in historical_data.keys():
                strategy.price_history[instrument] = []
        else:
            strategy.price_history = []
            
    # Prefill price history for each instrument
    for instrument in historical_data.keys():
        prefill_strategy_price_history(strategy, historical_data, instrument)
    
    # Track trades
    trades = []
    open_trades = {}
    
    # Create a unified timeline from all instruments
    all_timestamps = set()
    for instrument, candles in historical_data.items():
        for candle in candles:
            all_timestamps.add(candle['timestamp'])
    
    sorted_timestamps = sorted(all_timestamps)
    total_timestamps = len(sorted_timestamps)
    
    # Skip the first 100 timestamps to allow for indicator calculation
    start_idx = 100
    if total_timestamps <= start_idx:
        logger.error(f"❌ Not enough data points for backtest (need > {start_idx})")
        return {
            'strategy': strategy.name,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'status': 'FAILURE - Insufficient Data'
        }
        
    logger.info(f"  Starting backtest at timestamp {start_idx}/{total_timestamps}")
    
    # Process each timestamp
    for i, timestamp in enumerate(sorted_timestamps[start_idx:], start=start_idx):
        if i % 1000 == 0 or i == start_idx:
            logger.info(f"  Progress: {i}/{total_timestamps} timestamps ({i*100//total_timestamps}%)")
        
        # Build market data for all instruments at this timestamp
        market_data_dict = {}
        for instrument, candles in historical_data.items():
            # Find candle for this timestamp
            matching_candles = [c for c in candles if c['timestamp'] == timestamp]
            if matching_candles:
                candle = matching_candles[0]
                # Create market data
                market_data = create_market_data(candle, instrument)
                if market_data:
                    market_data_dict[instrument] = market_data
        
        # Generate signals
        try:
            signals = strategy.analyze_market(market_data_dict)
            
            # Process new signals
            if signals:
                for signal in signals:
                    if signal and hasattr(signal, 'instrument'):
                        trade_id = f"{signal.instrument}_{timestamp}"
                        if trade_id not in open_trades:
                            # Extract signal attributes safely
                            instrument = getattr(signal, 'instrument', None)
                            side = getattr(signal, 'side', None)
                            if hasattr(side, 'value'):
                                side = side.value
                            entry_price = getattr(signal, 'entry_price', None)
                            stop_loss = getattr(signal, 'stop_loss', None)
                            take_profit = getattr(signal, 'take_profit', None)
                            strength = getattr(signal, 'strength', 0)
                            
                            # Only add valid trades
                            if instrument and side and entry_price and stop_loss and take_profit:
                                open_trades[trade_id] = {
                                    'instrument': instrument,
                                    'side': side,
                                    'entry_price': entry_price,
                                    'stop_loss': stop_loss,
                                    'take_profit': take_profit,
                                    'entry_time': timestamp,
                                    'quality_score': strength
                                }
                                logger.info(f"  ✅ New {side} signal for {instrument} at {entry_price}")
        except Exception as e:
            logger.debug(f"Error generating signals at {timestamp}: {e}")
        
        # Check open trades for exits
        to_close = []
        for trade_id, trade in open_trades.items():
            instrument = trade['instrument']
            if instrument in market_data_dict:
                current_price = market_data_dict[instrument].bid if trade['side'] == 'SELL' else market_data_dict[instrument].ask
                
                # Check stop loss
                if trade['side'] == 'BUY' or trade['side'] == 'LONG':
                    if current_price <= trade['stop_loss']:
                        trade['exit_price'] = trade['stop_loss']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['stop_loss'] - trade['entry_price']) * 10000
                        trade['status'] = 'loss'
                        trades.append(trade)
                        to_close.append(trade_id)
                        logger.info(f"  ❌ Stop loss hit for {instrument} {trade['side']} at {trade['stop_loss']}")
                    elif current_price >= trade['take_profit']:
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['take_profit'] - trade['entry_price']) * 10000
                        trade['status'] = 'win'
                        trades.append(trade)
                        to_close.append(trade_id)
                        logger.info(f"  ✅ Take profit hit for {instrument} {trade['side']} at {trade['take_profit']}")
                else:  # SELL/SHORT
                    if current_price >= trade['stop_loss']:
                        trade['exit_price'] = trade['stop_loss']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['entry_price'] - trade['stop_loss']) * 10000
                        trade['status'] = 'loss'
                        trades.append(trade)
                        to_close.append(trade_id)
                        logger.info(f"  ❌ Stop loss hit for {instrument} {trade['side']} at {trade['stop_loss']}")
                    elif current_price <= trade['take_profit']:
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_time'] = timestamp
                        trade['profit_pips'] = (trade['entry_price'] - trade['take_profit']) * 10000
                        trade['status'] = 'win'
                        trades.append(trade)
                        to_close.append(trade_id)
                        logger.info(f"  ✅ Take profit hit for {instrument} {trade['side']} at {trade['take_profit']}")
        
        # Remove closed trades
        for trade_id in to_close:
            del open_trades[trade_id]
    
    # Close any remaining open trades at the end of the backtest
    for trade_id, trade in open_trades.items():
        instrument = trade['instrument']
        if instrument in historical_data and historical_data[instrument]:
            last_candle = historical_data[instrument][-1]
            last_price = last_candle['mid_close']
            
            if trade['side'] == 'BUY' or trade['side'] == 'LONG':
                profit_pips = (last_price - trade['entry_price']) * 10000
                status = 'win' if profit_pips > 0 else 'loss'
            else:  # SELL/SHORT
                profit_pips = (trade['entry_price'] - last_price) * 10000
                status = 'win' if profit_pips > 0 else 'loss'
            
            trade['exit_price'] = last_price
            trade['exit_time'] = sorted_timestamps[-1]
            trade['profit_pips'] = profit_pips
            trade['status'] = status
            trades.append(trade)
            logger.info(f"  ⚠️ Closing open {trade['side']} trade for {instrument} at {last_price} ({status})")
    
    # Calculate results
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['status'] == 'win')
    losses = sum(1 for t in trades if t['status'] == 'loss')
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    # Calculate additional metrics
    if total_trades > 0:
        win_amounts = [t['profit_pips'] for t in trades if t['status'] == 'win']
        loss_amounts = [t['profit_pips'] for t in trades if t['status'] == 'loss']
        
        avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
        total_profit = sum(t['profit_pips'] for t in trades)
        profit_factor = abs(sum(win_amounts) / sum(loss_amounts)) if sum(loss_amounts) != 0 else float('inf')
    else:
        avg_win = 0
        avg_loss = 0
        total_profit = 0
        profit_factor = 0
    
    # Determine status
    if total_trades == 0:
        status = "FAILURE - No Trades"
    elif win_rate < 50:
        status = "❌ FAILURE - Win Rate < 50%"
    else:
        status = "✅ PASS - Win Rate >= 50%"
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📈 RESULTS: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Wins: {wins}")
    logger.info(f"Losses: {losses}")
    logger.info(f"Win Rate: {win_rate:.2f}%")
    logger.info(f"Average Win: {avg_win:.2f} pips")
    logger.info(f"Average Loss: {avg_loss:.2f} pips")
    logger.info(f"Profit Factor: {profit_factor:.2f}")
    logger.info(f"Total Profit: {total_profit:.2f} pips")
    logger.info(f"Status: {status}")
    logger.info(f"{'='*70}\n")
    
    return {
        'strategy': strategy.name,
        'trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'total_profit': total_profit,
        'status': status,
        'trade_details': trades
    }

def run_backtest_for_strategies(strategies, days=14):
    """Run backtest for multiple strategies"""
    # Load credentials
    if not load_credentials():
        return []
    
    # Initialize OANDA client
    client = OandaClient()
    
    # Download historical data for all instruments
    all_instruments = set()
    for strategy_config in strategies:
        all_instruments.update(strategy_config['instruments'])
    
    historical_data = {}
    for instrument in all_instruments:
        data = get_historical_data(client, instrument, days)
        if data:
            historical_data[instrument] = data
    
    # Run backtests
    results = []
    for strategy_config in strategies:
        try:
            # Filter historical data for this strategy
            strategy_data = {
                instrument: historical_data[instrument]
                for instrument in strategy_config['instruments']
                if instrument in historical_data
            }
            
            if not strategy_data:
                logger.error(f"❌ No historical data available for {strategy_config['name']}")
                results.append({
                    'strategy': strategy_config['name'],
                    'status': 'FAILURE - No Data',
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0
                })
                continue
            
            # Run backtest
            result = run_backtest(strategy_config['strategy'], strategy_data, days)
            results.append(result)
        except Exception as e:
            logger.error(f"❌ Error testing {strategy_config['name']}: {e}")
            results.append({
                'strategy': strategy_config['name'],
                'status': f'FAILURE - Error: {str(e)}',
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0
            })
    
    return results

# Example usage
if __name__ == "__main__":
    logger.info("This is a library module. Import and use in your backtest scripts.")
    logger.info("Example usage:")
    logger.info("from universal_backtest_fix import run_backtest_for_strategies")
    logger.info("results = run_backtest_for_strategies(strategies, days=14)")
