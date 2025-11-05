#!/usr/bin/env python3
"""
Alternative 14-Day Backtest for All Strategies
Uses the actual OANDA data format (bid/ask instead of mid)
Tests each strategy against the past 14 days of market data
Win rate < 50% = FAILURE
"""

import os
import sys
import yaml
import logging
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
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
from src.core.data_feed import MarketData

def get_historical_data(client, instrument, days=14, granularity='M5'):
    """Get historical data from OANDA with proper error handling for the actual data format"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    try:
        logger.info(f"  Fetching {instrument} ({granularity}) data for {days} days...")
        
        # Use the correct method name
        response = client.get_candles(
            instrument=instrument,
            granularity=granularity,
            count=5000  # Maximum allowed, will be trimmed to actual date range later
        )
        
        if not response or 'candles' not in response:
            logger.error(f"    ❌ No data returned for {instrument}")
            return None
        
        candles = response['candles']
        logger.info(f"    ✅ {len(candles)} candles retrieved")
        
        # Convert to pandas DataFrame for easier manipulation
        data = []
        for candle in candles:
            if 'time' not in candle:
                continue
                
            try:
                timestamp = candle['time']
                
                # Check for bid/ask fields
                if 'bid' in candle and isinstance(candle['bid'], dict):
                    bid_open = float(candle['bid'].get('o', 0))
                    bid_high = float(candle['bid'].get('h', 0))
                    bid_low = float(candle['bid'].get('l', 0))
                    bid_close = float(candle['bid'].get('c', 0))
                else:
                    # Skip if no bid data
                    continue
                    
                if 'ask' in candle and isinstance(candle['ask'], dict):
                    ask_open = float(candle['ask'].get('o', 0))
                    ask_high = float(candle['ask'].get('h', 0))
                    ask_low = float(candle['ask'].get('l', 0))
                    ask_close = float(candle['ask'].get('c', 0))
                else:
                    # Skip if no ask data
                    continue
                
                # Calculate mid prices
                mid_open = (bid_open + ask_open) / 2
                mid_high = (bid_high + ask_high) / 2
                mid_low = (bid_low + ask_low) / 2
                mid_close = (bid_close + ask_close) / 2
                
                data.append({
                    'time': timestamp,
                    'open': mid_open,
                    'high': mid_high,
                    'low': mid_low,
                    'close': mid_close,
                    'bid_close': bid_close,
                    'ask_close': ask_close,
                    'volume': candle.get('volume', 0)
                })
            except (KeyError, ValueError) as e:
                logger.warning(f"    ⚠️ Error parsing candle: {e}")
                continue
        
        if not data:
            logger.error(f"    ❌ No valid candles for {instrument}")
            return None
            
        df = pd.DataFrame(data)
        
        # Convert timestamp to datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Filter by date range
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
        
        logger.info(f"    ✅ {len(df)} candles in date range")
        return df
        
    except Exception as e:
        logger.error(f"    ❌ Error fetching {instrument}: {e}")
        return None

def prepare_market_data(df_row, instrument):
    """Convert DataFrame row to MarketData object"""
    timestamp = df_row['time']
    bid_price = df_row['bid_close']
    ask_price = df_row['ask_close']
    
    # Create MarketData with appropriate fields
    return MarketData(
        instrument=instrument,
        timestamp=timestamp,
        bid=bid_price,
        ask=ask_price,
        spread=ask_price - bid_price,
        is_live=False,
        data_source='backtest',
        last_update_age=0
    )

def calculate_technical_indicators(df):
    """Calculate technical indicators needed for strategy evaluation"""
    # Calculate ADX (Average Directional Index)
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # True Range
    tr1 = np.abs(high[1:] - low[1:])
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)
    
    # Directional Movement
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]
    
    plus_dm = np.zeros_like(up_move)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    
    minus_dm = np.zeros_like(down_move)
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]
    
    # Smoothed TR, +DM, -DM (14-period)
    period = 14
    smoothed_tr = np.zeros_like(tr)
    smoothed_plus_dm = np.zeros_like(plus_dm)
    smoothed_minus_dm = np.zeros_like(minus_dm)
    
    # Initial values
    smoothed_tr[0] = np.sum(tr[:min(period, len(tr))])
    smoothed_plus_dm[0] = np.sum(plus_dm[:min(period, len(plus_dm))])
    smoothed_minus_dm[0] = np.sum(minus_dm[:min(period, len(minus_dm))])
    
    # Calculate smoothed values
    for i in range(1, len(tr)):
        smoothed_tr[i] = smoothed_tr[i-1] - (smoothed_tr[i-1]/period) + tr[i]
        smoothed_plus_dm[i] = smoothed_plus_dm[i-1] - (smoothed_plus_dm[i-1]/period) + plus_dm[i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i-1] - (smoothed_minus_dm[i-1]/period) + minus_dm[i]
    
    # Calculate +DI and -DI
    plus_di = 100 * smoothed_plus_dm / smoothed_tr
    minus_di = 100 * smoothed_minus_dm / smoothed_tr
    
    # Calculate DX and ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX (14-period smoothed DX)
    adx = np.zeros_like(dx)
    adx[:period-1] = np.nan  # First period-1 values are NaN
    
    # Initial ADX value
    adx[period-1] = np.mean(dx[:period])
    
    # Calculate smoothed ADX
    for i in range(period, len(dx)):
        adx[i] = (adx[i-1] * (period-1) + dx[i]) / period
    
    # Add ADX to DataFrame
    adx_series = np.concatenate([np.array([np.nan]), adx])  # Add NaN at beginning to align with original df
    df['adx'] = adx_series
    
    # Calculate Momentum (percent change over period)
    df['momentum_5'] = df['close'].pct_change(5) * 100  # 5-period momentum
    df['momentum_14'] = df['close'].pct_change(14) * 100  # 14-period momentum
    df['momentum_20'] = df['close'].pct_change(20) * 100  # 20-period momentum
    
    # Calculate Moving Averages
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Calculate ATR (Average True Range)
    atr = np.zeros_like(close)
    atr[0] = tr[0] if len(tr) > 0 else 0  # Initial ATR is the first TR
    
    # Calculate smoothed ATR
    for i in range(1, len(tr)):
        atr[i] = (atr[i-1] * 13 + tr[i]) / 14  # 14-period smoothed ATR
    
    # Add ATR to DataFrame
    atr_series = np.concatenate([np.array([np.nan]), atr])  # Add NaN at beginning to align with original df
    df['atr'] = atr_series
    
    return df

def configure_strategy_parameters(strategy, strategy_type):
    """Configure strategy with appropriate fundamental parameters"""
    if strategy_type == "momentum":
        # Set proper momentum strategy parameters
        strategy.min_adx = 25.0  # Strong trend required
        strategy.min_momentum = 0.005  # Significant momentum required
        strategy.min_quality_score = 70  # Only high-quality setups
        strategy.momentum_period = 20  # Longer period for trend confirmation
        strategy.trend_period = 50  # Long-term trend confirmation
        strategy.stop_loss_atr = 3.0  # Wider stop to avoid premature exits
        strategy.take_profit_atr = 6.0  # Reasonable profit target
        strategy.max_trades_per_day = 5  # Limit number of trades
        strategy.min_time_between_trades_minutes = 120  # Avoid overtrading
        strategy.require_trend_continuation = True  # Ensure trend alignment
        
        logger.info(f"✅ Configured momentum strategy with fundamental parameters:")
        logger.info(f"   - min_adx: {strategy.min_adx}")
        logger.info(f"   - min_momentum: {strategy.min_momentum}")
        logger.info(f"   - min_quality_score: {strategy.min_quality_score}")
        logger.info(f"   - momentum_period: {strategy.momentum_period}")
        logger.info(f"   - trend_period: {strategy.trend_period}")
        logger.info(f"   - R:R ratio: 1:{strategy.take_profit_atr/strategy.stop_loss_atr:.1f}")
    
    elif strategy_type == "scalping":
        # Set proper scalping strategy parameters
        strategy.min_spread = 0.0005  # Maximum acceptable spread
        strategy.min_volatility = 0.0015  # Minimum volatility required
        strategy.max_volatility = 0.0050  # Maximum volatility allowed
        strategy.stop_loss_pips = 15  # Tight stop loss
        strategy.take_profit_pips = 30  # Reasonable profit target
        strategy.max_trades_per_day = 10  # Allow more trades for scalping
        strategy.min_time_between_trades_minutes = 30  # Allow more frequent trades
        
        logger.info(f"✅ Configured scalping strategy with fundamental parameters:")
        logger.info(f"   - min_spread: {strategy.min_spread}")
        logger.info(f"   - volatility range: {strategy.min_volatility}-{strategy.max_volatility}")
        logger.info(f"   - stop_loss_pips: {strategy.stop_loss_pips}")
        logger.info(f"   - take_profit_pips: {strategy.take_profit_pips}")
        logger.info(f"   - R:R ratio: 1:{strategy.take_profit_pips/strategy.stop_loss_pips:.1f}")

def prefill_strategy_price_history(strategy, historical_data, instrument, bars=100):
    """Prefill strategy price history with historical data"""
    if not historical_data or instrument not in historical_data:
        return
        
    df = historical_data[instrument]
    if len(df) < bars:
        bars = len(df)
        
    # Get the first 'bars' rows for prefilling
    prefill_data = df.head(bars)
    
    # Add to strategy price history
    if hasattr(strategy, 'price_history'):
        if isinstance(strategy.price_history, dict):
            strategy.price_history[instrument] = prefill_data['close'].tolist()
        else:
            strategy.price_history = prefill_data['close'].tolist()
            
    logger.info(f"  ✅ Prefilled {bars} bars of price history for {instrument}")

def run_strategy_backtest(strategy, instruments, strategy_type, days=14):
    """Run backtest for a single strategy with proper fundamental characteristics"""
    client = OandaClient()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 BACKTESTING: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Instruments: {', '.join(instruments)}")
    
    # Configure strategy with proper parameters
    configure_strategy_parameters(strategy, strategy_type)
    
    # Download and process historical data
    historical_data = {}
    for instrument in instruments:
        df = get_historical_data(client, instrument, days)
        if df is not None and not df.empty:
            # Calculate technical indicators
            df = calculate_technical_indicators(df)
            historical_data[instrument] = df
    
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
        if isinstance(strategy.price_history, dict):
            for instrument in instruments:
                strategy.price_history[instrument] = []
        else:
            strategy.price_history = []
            
    # Prefill price history for each instrument
    for instrument in instruments:
        if instrument in historical_data:
            prefill_strategy_price_history(strategy, historical_data, instrument)
    
    # Track trades
    trades = []
    open_trades = {}
    
    # Process each instrument's data chronologically
    logger.info(f"\n🔄 Running backtest...")
    
    # Create a unified timeline from all instruments
    all_timestamps = set()
    for instrument, df in historical_data.items():
        all_timestamps.update(df['time'].tolist())
    
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
        for instrument, df in historical_data.items():
            # Find row for this timestamp
            df_at_time = df[df['time'] == timestamp]
            if not df_at_time.empty:
                # Create market data
                market_data_dict[instrument] = prepare_market_data(df_at_time.iloc[0], instrument)
        
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
        if instrument in historical_data:
            last_price = historical_data[instrument]['close'].iloc[-1]
            
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

def main():
    """Run backtest for all strategies with proper fundamental characteristics"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 14-DAY BACKTEST - ALL STRATEGIES (ALTERNATIVE)")
    logger.info("="*70)
    logger.info("Win Rate Threshold: 50%")
    logger.info("Below 50% = FAILURE ❌")
    logger.info("="*70 + "\n")
    
    # Define strategies to test with their fundamental characteristics
    strategies = [
        {
            'name': 'Trump DNA (Momentum Trading)',
            'strategy': MomentumTradingStrategy(),
            'instruments': ['XAU_USD'],  # Focus on Gold for faster testing
            'type': 'momentum'
        },
        {
            'name': 'Gold Scalping',
            'strategy': GoldScalpingStrategy(),
            'instruments': ['XAU_USD'],
            'type': 'scalping'
        }
    ]
    
    # Run backtests
    results = []
    for strategy_config in strategies:
        try:
            result = run_strategy_backtest(
                strategy_config['strategy'],
                strategy_config['instruments'],
                strategy_config['type']
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
    logger.info("📊 FINAL SUMMARY - 14 DAY BACKTEST (ALTERNATIVE)")
    logger.info("="*70)
    logger.info(f"{'Strategy':<40} {'Trades':<10} {'Win Rate':<15} {'Profit Factor':<15} {'Status':<15}")
    logger.info("-"*70)
    
    for result in results:
        profit_factor = f"{result.get('profit_factor', 0):.2f}"
        logger.info(f"{result['strategy']:<40} {result['trades']:<10} {result['win_rate']:.2f}%{'':<10} {profit_factor:<15} {result['status']:<15}")
    
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
    output_file = 'alternative_backtest_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\n💾 Detailed results saved to {output_file}")

if __name__ == "__main__":
    main()



