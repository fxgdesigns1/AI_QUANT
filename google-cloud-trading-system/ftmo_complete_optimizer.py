#!/usr/bin/env python3
"""
FTMO Complete Optimizer
Comprehensive optimization system for achieving 65%+ win rate
Includes data fetching, backtesting, and parameter optimization
"""

import os
import sys
import yaml
import logging
import json
import itertools
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple
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

from src.core.oanda_client import OandaClient
from src.core.data_feed import MarketData
from src.core.ftmo_risk_manager import FTMORiskManager
from src.strategies.momentum_trading import MomentumTradingStrategy

def fetch_oanda_data(client, instrument, days=14):
    """Fetch historical data from OANDA with proper format handling"""
    logger.info(f"📥 Fetching {instrument} data for {days} days...")
    
    # Use H1 for longer periods to avoid count limit
    granularity = 'H1' if days > 17 else 'M5'
    candles_per_day = 24 if granularity == 'H1' else 288
    count = min(5000, days * candles_per_day)
    
    try:
        response = client.get_candles(
            instrument=instrument,
            granularity=granularity,
            count=count
        )
        
        if not response or 'candles' not in response:
            logger.error(f"  ❌ No data returned")
            return None
        
        candles = response['candles']
        logger.info(f"  ✅ {len(candles)} {granularity} candles retrieved")
        
        # Process candles
        processed_data = []
        for candle in candles:
            try:
                time_str = candle.get('time')
                if not time_str:
                    continue
                
                timestamp = datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                timestamp = pytz.UTC.localize(timestamp)
                
                # Extract bid/ask
                if 'bid' in candle and isinstance(candle['bid'], dict):
                    bid_c = float(candle['bid'].get('c', 0))
                    bid_h = float(candle['bid'].get('h', 0))
                    bid_l = float(candle['bid'].get('l', 0))
                else:
                    continue
                    
                if 'ask' in candle and isinstance(candle['ask'], dict):
                    ask_c = float(candle['ask'].get('c', 0))
                    ask_h = float(candle['ask'].get('h', 0))
                    ask_l = float(candle['ask'].get('l', 0))
                else:
                    continue
                
                # Calculate mid prices
                mid_c = (bid_c + ask_c) / 2
                mid_h = (bid_h + ask_h) / 2
                mid_l = (bid_l + ask_l) / 2
                
                processed_data.append({
                    'timestamp': timestamp,
                    'close': mid_c,
                    'high': mid_h,
                    'low': mid_l,
                    'bid': bid_c,
                    'ask': ask_c,
                    'volume': candle.get('volume', 0)
                })
            except Exception as e:
                continue
        
        if not processed_data:
            logger.error(f"  ❌ No valid candles processed")
            return None
        
        logger.info(f"  ✅ {len(processed_data)} candles processed")
        return processed_data
        
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return None

def calculate_indicators(prices):
    """Calculate technical indicators from price data"""
    if len(prices) < 50:
        return None
    
    df = pd.DataFrame(prices)
    
    # Calculate momentum
    df['momentum_5'] = df['close'].pct_change(5)
    df['momentum_10'] = df['close'].pct_change(10)
    df['momentum_20'] = df['close'].pct_change(20)
    df['momentum_40'] = df['close'].pct_change(40)
    
    # Calculate EMAs
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # Calculate ATR (simplified)
    df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
    df['atr'] = df['tr'].rolling(14).mean()
    
    # Calculate ADX (simplified)
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = df['tr']
    plus_di = 100 * (plus_dm.rolling(14).mean() / tr.rolling(14).mean())
    minus_di = 100 * (minus_dm.rolling(14).mean() / tr.rolling(14).mean())
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(14).mean()
    
    return df

def simple_backtest(data, params):
    """Simple backtest with given parameters"""
    df = calculate_indicators(data)
    
    if df is None or len(df) < 100:
        return {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'profit_pips': 0,
            'max_dd': 0
        }
    
    trades = []
    open_trade = None
    balance = 100000
    peak_balance = 100000
    max_dd = 0
    
    # Extract parameters
    min_adx = params.get('min_adx', 20)
    min_momentum = params.get('min_momentum', 0.005)
    min_quality = params.get('min_quality_score', 60)
    sl_atr = params.get('stop_loss_atr', 2.5)
    tp_atr = params.get('take_profit_atr', 5.0)
    momentum_period = params.get('momentum_period', 20)
    
    # Process each row
    for i in range(100, len(df)):
        row = df.iloc[i]
        
        # Skip if indicators are NaN
        if pd.isna(row['adx']) or pd.isna(row['atr']):
            continue
        
        # Check open trade
        if open_trade:
            current_price = row['close']
            
            # Check SL/TP
            if open_trade['side'] == 'BUY':
                if current_price <= open_trade['sl']:
                    # Stop loss hit
                    pnl = (open_trade['sl'] - open_trade['entry']) * open_trade['units']
                    open_trade['exit'] = open_trade['sl']
                    open_trade['pnl'] = pnl
                    open_trade['result'] = 'loss'
                    trades.append(open_trade)
                    balance += pnl
                    open_trade = None
                elif current_price >= open_trade['tp']:
                    # Take profit hit
                    pnl = (open_trade['tp'] - open_trade['entry']) * open_trade['units']
                    open_trade['exit'] = open_trade['tp']
                    open_trade['pnl'] = pnl
                    open_trade['result'] = 'win'
                    trades.append(open_trade)
                    balance += pnl
                    if balance > peak_balance:
                        peak_balance = balance
                    open_trade = None
            else:  # SELL
                if current_price >= open_trade['sl']:
                    # Stop loss hit
                    pnl = (open_trade['entry'] - open_trade['sl']) * open_trade['units']
                    open_trade['exit'] = open_trade['sl']
                    open_trade['pnl'] = pnl
                    open_trade['result'] = 'loss'
                    trades.append(open_trade)
                    balance += pnl
                    open_trade = None
                elif current_price <= open_trade['tp']:
                    # Take profit hit
                    pnl = (open_trade['entry'] - open_trade['tp']) * open_trade['units']
                    open_trade['exit'] = open_trade['tp']
                    open_trade['pnl'] = pnl
                    open_trade['result'] = 'win'
                    trades.append(open_trade)
                    balance += pnl
                    if balance > peak_balance:
                        peak_balance = balance
                    open_trade = None
            
            # Update max drawdown
            dd = (peak_balance - balance) / peak_balance
            if dd > max_dd:
                max_dd = dd
            
            continue
        
        # Generate new signal
        momentum_col = f'momentum_{momentum_period}' if f'momentum_{momentum_period}' in df.columns else 'momentum_20'
        momentum = row.get(momentum_col, 0)
        adx = row['adx']
        atr = row['atr']
        
        # Check if conditions met
        if adx < min_adx or abs(momentum) < min_momentum or pd.isna(atr) or atr == 0:
            continue
        
        # Simple quality score
        quality = 0
        quality += min(40, (adx / 50) * 40)  # ADX contribution
        quality += min(30, (abs(momentum) / 0.01) * 30)  # Momentum contribution
        quality += 30  # Base score
        
        if quality < min_quality:
            continue
        
        # Determine direction
        if momentum > 0 and row['close'] > row['ema_21']:
            side = 'BUY'
            entry = row['close']
            sl = entry - (sl_atr * atr)
            tp = entry + (tp_atr * atr)
            
            open_trade = {
                'side': side,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'units': 10,  # Simple position size
                'entry_time': row['timestamp'] if 'timestamp' in row else i
            }
        elif momentum < 0 and row['close'] < row['ema_21']:
            side = 'SELL'
            entry = row['close']
            sl = entry + (sl_atr * atr)
            tp = entry - (tp_atr * atr)
            
            open_trade = {
                'side': side,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'units': 10,  # Simple position size
                'entry_time': row['timestamp'] if 'timestamp' in row else i
            }
    
    # Calculate results
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['result'] == 'win')
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    profit_pips = sum(t['pnl'] for t in trades)
    
    return {
        'trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_pips': profit_pips,
        'max_dd': max_dd * 100,
        'final_balance': balance
    }

def optimize_for_ftmo():
    """Run comprehensive optimization for FTMO challenge"""
    
    logger.info("\n" + "="*70)
    logger.info("🎯 FTMO GOLD OPTIMIZER - Monte Carlo Simulation")
    logger.info("="*70)
    logger.info("Target: 65%+ Win Rate")
    logger.info("Instrument: XAU_USD")
    logger.info("Period: 14 days")
    logger.info("="*70 + "\n")
    
    # Fetch data
    client = OandaClient()
    data = fetch_oanda_data(client, 'XAU_USD', days=14)
    
    if not data:
        logger.error("❌ Failed to fetch data")
        return None
    
    # Define parameter ranges for FTMO optimization
    param_ranges = {
        'min_adx': [10, 15, 20, 25, 30],
        'min_momentum': [0.002, 0.003, 0.005, 0.008],
        'min_quality_score': [50, 55, 60, 65, 70],
        'stop_loss_atr': [2.0, 2.5, 3.0, 3.5],
        'take_profit_atr': [4.0, 5.0, 6.0, 8.0],
        'momentum_period': [15, 20, 25, 30]
    }
    
    # Generate all combinations
    keys = list(param_ranges.keys())
    values = list(param_ranges.values())
    combinations = list(itertools.product(*values))
    param_combos = [dict(zip(keys, combo)) for combo in combinations]
    
    total_combos = len(param_combos)
    logger.info(f"📊 Testing {total_combos} parameter combinations...")
    logger.info(f"   Estimated time: {total_combos * 0.5 / 60:.1f} minutes\n")
    
    # Test each combination
    results = []
    
    for i, params in enumerate(param_combos, 1):
        if i % 100 == 0 or i == 1:
            logger.info(f"  Progress: {i}/{total_combos} ({i*100//total_combos}%)")
        
        try:
            result = simple_backtest(data, params)
            
            # Calculate FTMO fitness
            fitness = 0
            
            # Win rate component (60% weight)
            if result['win_rate'] >= 65:
                fitness += 0.6 * (result['win_rate'] / 100)
            else:
                fitness += 0.3 * (result['win_rate'] / 100)  # Penalty for < 65%
            
            # Trade frequency (20% weight) - target 20-40 trades
            trade_score = 1 - abs(result['trades'] - 30) / 50
            fitness += 0.2 * max(0, trade_score)
            
            # Profitability (10% weight)
            if result['profit_pips'] > 0:
                fitness += 0.1
            
            # Max drawdown (10% weight) - lower is better
            dd_score = 1 - (result['max_dd'] / 10)  # Normalize to 10% max
            fitness += 0.1 * max(0, dd_score)
            
            results.append({
                'params': params,
                'fitness': fitness,
                **result
            })
            
        except Exception as e:
            logger.debug(f"  Error testing combo {i}: {e}")
    
    # Sort by fitness
    results.sort(key=lambda x: x['fitness'], reverse=True)
    
    # Display top 10
    logger.info(f"\n{'='*70}")
    logger.info("🏆 TOP 10 PARAMETER COMBINATIONS FOR FTMO")
    logger.info("="*70)
    logger.info(f"{'Rank':<6} {'WR%':<8} {'Trades':<10} {'Profit':<12} {'MaxDD%':<10} {'Fitness':<10}")
    logger.info("-"*70)
    
    for i, r in enumerate(results[:10], 1):
        logger.info(f"{i:<6} {r['win_rate']:.1f}{'':<3} {r['trades']:<10} {r['profit_pips']:+.0f}{'':<7} {r['max_dd']:.2f}{'':<5} {r['fitness']:.4f}")
    
    logger.info("="*70)
    
    # Display best parameters in detail
    if results:
        best = results[0]
        logger.info(f"\n🎯 OPTIMAL PARAMETERS FOR 65%+ WIN RATE:")
        logger.info(f"   Win Rate: {best['win_rate']:.1f}%")
        logger.info(f"   Total Trades: {best['trades']}")
        logger.info(f"   Wins: {best['wins']} | Losses: {best['losses']}")
        logger.info(f"   Profit: {best['profit_pips']:+.2f} pips")
        logger.info(f"   Max Drawdown: {best['max_dd']:.2f}%")
        logger.info(f"   Fitness Score: {best['fitness']:.4f}")
        logger.info(f"\n   Parameters:")
        for key, value in best['params'].items():
            logger.info(f"      {key}: {value}")
        
        # Filter results with 65%+ win rate
        high_wr_results = [r for r in results if r['win_rate'] >= 65]
        
        if high_wr_results:
            logger.info(f"\n✅ Found {len(high_wr_results)} combinations with 65%+ win rate!")
            logger.info(f"\n🏆 TOP 5 HIGH WIN RATE COMBINATIONS:")
            for i, r in enumerate(high_wr_results[:5], 1):
                logger.info(f"\n   #{i}: Win Rate: {r['win_rate']:.1f}% | Trades: {r['trades']} | Profit: {r['profit_pips']:+.0f} pips")
                for key, value in r['params'].items():
                    logger.info(f"        {key}: {value}")
        else:
            logger.warning(f"\n⚠️ No combinations achieved 65%+ win rate")
            logger.warning(f"   Best win rate: {results[0]['win_rate']:.1f}%")
            logger.warning(f"   Consider:")
            logger.warning(f"   - Lowering quality threshold")
            logger.warning(f"   - Adjusting momentum thresholds")
            logger.warning(f"   - Testing on different time periods")
    
    # Save results
    output_file = 'ftmo_optimization_results.json'
    with open(output_file, 'w') as f:
        json.dump(results[:50], f, indent=2, default=str)  # Save top 50
    logger.info(f"\n💾 Top 50 results saved to {output_file}")
    
    return results

if __name__ == "__main__":
    optimize_for_ftmo()




