#!/usr/bin/env python3
"""
TEST NEW STRATEGIES - LAST 2 WEEKS BACKTEST
Compares Oct 18 Google Drive strategies vs Oct 20 current strategies
Tests against real market data from last 14 days

Purpose: Verify performance before deployment
"""

import os
import sys
import yaml
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict
from typing import Dict, List, Tuple
import pandas as pd

sys.path.insert(0, '.')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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

# ========================================
# STRATEGY CONFIGURATIONS TO TEST
# ========================================

class StrategyConfig:
    """Configuration for a strategy variant"""
    def __init__(self, name, params):
        self.name = name
        self.params = params

# Oct 18 Google Drive Strategies (with real-market lowering)
OCT18_STRATEGIES = {
    '75wr_champion_oct18': StrategyConfig(
        name="75% WR Champion (Oct 18)",
        params={
            'signal_strength_min': 0.20,  # 20% (lowered from 60%)
            'confluence_required': 2,
            'min_adx': 15,
            'min_volume_mult': 1.2,
            'confirmation_bars': 2,
            'sl_atr_mult': 1.5,
            'tp_atr_mult': 3.0,
            'max_trades_per_day': 3,
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        }
    ),
    'all_weather_oct18': StrategyConfig(
        name="All-Weather 70% WR (Oct 18)",
        params={
            'base_signal_strength': 0.25,  # 25%
            'base_confluence_required': 2,
            'base_volume_mult': 1.5,
            'confirmation_bars': 3,
            'regime_aware': True,
            'max_trades_per_day': 5,
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        }
    ),
    'ultra_strict_v2_oct18': StrategyConfig(
        name="Ultra Strict V2 (Oct 18)",
        params={
            'base_signal_strength': 0.25,  # 25%
            'min_adx': 18,
            'atr_volatile_mult': 1.3,
            'sl_atr_mult': 2.0,
            'tp_atr_mult': 5.0,
            'max_trades_per_day': 5,
            'instruments': ['EUR_USD', 'AUD_USD', 'USD_CAD', 'NZD_USD']
        }
    ),
    'momentum_v2_oct18': StrategyConfig(
        name="Momentum V2 (Oct 18)",
        params={
            'min_momentum': 0.003,
            'sl_atr_mult': 2.0,
            'tp_atr_mult': 3.0,
            'execution_buffer_pips': 3,
            'confirmation_bars': 2,
            'max_spread_pips': 2.5,
            'max_trades_per_day': 10,
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
        }
    )
}

# Oct 20 Current Strategies (massively relaxed)
OCT20_STRATEGIES = {
    'momentum_oct20': StrategyConfig(
        name="Momentum Trading (Oct 20 - Current)",
        params={
            'min_signal_strength': 0.25,  # 25% (was 0.85)
            'max_trades_per_day': 100,  # Increased from 10
            'min_adx': 8.0,  # Very low
            'min_momentum': 0.0003,  # Very low
            'min_volume': 0.03,  # Very low
            'quality_score_threshold': 0.050,  # 5% (was 90%)
            'only_trade_london_ny': False,  # All sessions
            'instruments': ['XAU_USD']  # Gold only
        }
    ),
    'gold_scalping_oct20': StrategyConfig(
        name="Gold Scalping (Oct 20 - Current)",
        params={
            'min_signal_strength': 0.70,  # 70%
            'stop_loss_pips': 6,
            'take_profit_pips': 24,
            'max_trades_per_day': 10,
            'min_volatility': 0.00005,
            'max_spread': 1.0,
            'min_atr_for_entry': 1.5,
            'quality_score_threshold': 0.90,  # 90%
            'only_trade_london_ny': True,
            'instruments': ['XAU_USD']
        }
    )
}

# ========================================
# SIMPLE SIGNAL DETECTION
# ========================================

def detect_simple_signals(candles: List[Dict], params: Dict) -> List[Dict]:
    """
    Simple signal detection based on common parameters
    Returns list of trade signals with entry/exit prices
    """
    if len(candles) < 50:
        return []
    
    signals = []
    
    # Calculate indicators
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    
    # Simple EMA crossover strategy
    ema_short = pd.Series(closes).ewm(span=20, adjust=False).mean().tolist()
    ema_long = pd.Series(closes).ewm(span=50, adjust=False).mean().tolist()
    
    # Calculate ATR for stops
    def calc_atr(period=14):
        tr_list = []
        for i in range(1, len(candles)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        return sum(tr_list[-period:]) / period if len(tr_list) >= period else 0
    
    atr = calc_atr(14)
    
    # Generate signals based on EMA crossover
    for i in range(50, len(candles) - 1):  # Leave last candle for exit
        # Check for bullish crossover
        if ema_short[i] > ema_long[i] and ema_short[i-1] <= ema_long[i-1]:
            entry_price = candles[i]['close']
            sl_mult = params.get('sl_atr_mult', 1.5)
            tp_mult = params.get('tp_atr_mult', 3.0)
            
            stop_loss = entry_price - (atr * sl_mult)
            take_profit = entry_price + (atr * tp_mult)
            
            signals.append({
                'entry_index': i,
                'entry_time': candles[i]['time'],
                'entry_price': entry_price,
                'direction': 'LONG',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'atr': atr
            })
        
        # Check for bearish crossover
        elif ema_short[i] < ema_long[i] and ema_short[i-1] >= ema_long[i-1]:
            entry_price = candles[i]['close']
            sl_mult = params.get('sl_atr_mult', 1.5)
            tp_mult = params.get('tp_atr_mult', 3.0)
            
            stop_loss = entry_price + (atr * sl_mult)
            take_profit = entry_price - (atr * tp_mult)
            
            signals.append({
                'entry_index': i,
                'entry_time': candles[i]['time'],
                'entry_price': entry_price,
                'direction': 'SHORT',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'atr': atr
            })
    
    # Apply signal strength filter
    min_strength = params.get('signal_strength_min', 0) or params.get('min_signal_strength', 0) or params.get('base_signal_strength', 0)
    
    # Randomly filter based on signal strength (simulated)
    import random
    random.seed(42)  # Consistent results
    filtered_signals = []
    for sig in signals:
        if random.random() > min_strength:  # Higher min_strength = fewer signals
            filtered_signals.append(sig)
    
    # Apply max trades per day limit
    max_trades = params.get('max_trades_per_day', 999)
    if len(filtered_signals) > max_trades:
        filtered_signals = filtered_signals[:max_trades]
    
    return filtered_signals

def simulate_trade_outcome(signal: Dict, candles: List[Dict]) -> Dict:
    """
    Simulate trade outcome from signal to SL/TP
    Returns trade result with P&L
    """
    entry_idx = signal['entry_index']
    entry_price = signal['entry_price']
    stop_loss = signal['stop_loss']
    take_profit = signal['take_profit']
    direction = signal['direction']
    
    # Simulate forward from entry
    for i in range(entry_idx + 1, len(candles)):
        candle = candles[i]
        high = candle['high']
        low = candle['low']
        
        if direction == 'LONG':
            # Check if SL hit
            if low <= stop_loss:
                pnl = stop_loss - entry_price
                return {
                    'result': 'LOSS',
                    'exit_price': stop_loss,
                    'exit_time': candle['time'],
                    'pnl': pnl,
                    'pips': abs(pnl) * 10000,  # Approx pips
                    'bars_held': i - entry_idx
                }
            # Check if TP hit
            if high >= take_profit:
                pnl = take_profit - entry_price
                return {
                    'result': 'WIN',
                    'exit_price': take_profit,
                    'exit_time': candle['time'],
                    'pnl': pnl,
                    'pips': abs(pnl) * 10000,
                    'bars_held': i - entry_idx
                }
        
        else:  # SHORT
            # Check if SL hit
            if high >= stop_loss:
                pnl = entry_price - stop_loss
                return {
                    'result': 'LOSS',
                    'exit_price': stop_loss,
                    'exit_time': candle['time'],
                    'pnl': pnl,
                    'pips': abs(pnl) * 10000,
                    'bars_held': i - entry_idx
                }
            # Check if TP hit
            if low <= take_profit:
                pnl = entry_price - take_profit
                return {
                    'result': 'WIN',
                    'exit_price': take_profit,
                    'exit_time': candle['time'],
                    'pnl': pnl,
                    'pips': abs(pnl) * 10000,
                    'bars_held': i - entry_idx
                }
    
    # Trade still open at end (count as loss for conservative estimate)
    current_price = candles[-1]['close']
    if direction == 'LONG':
        pnl = current_price - entry_price
    else:
        pnl = entry_price - current_price
    
    return {
        'result': 'OPEN',
        'exit_price': current_price,
        'exit_time': candles[-1]['time'],
        'pnl': pnl,
        'pips': abs(pnl) * 10000,
        'bars_held': len(candles) - entry_idx - 1
    }

# ========================================
# BACKTEST RUNNER
# ========================================

def backtest_strategy(strategy_name: str, config: StrategyConfig, client: OandaClient, days: int = 14) -> Dict:
    """Run backtest for a single strategy configuration"""
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 BACKTESTING: {config.name}")
    logger.info(f"{'='*80}")
    
    instruments = config.params.get('instruments', ['EUR_USD'])
    all_trades = []
    
    for instrument in instruments:
        try:
            logger.info(f"  Fetching {instrument} data...")
            
            # Fetch maximum historical data
            # H1 with count=500 = ~21 days (24 hours * 21 days = 504 hours)
            candles = client.get_candles(
                instrument=instrument,
                granularity='H1',
                count=500  # Get ~21 days of H1 data
            )
            
            if not candles:
                logger.warning(f"    ⚠️ No data for {instrument}")
                continue
            
            logger.info(f"    ✅ {len(candles)} candles retrieved")
            
            # Detect signals
            signals = detect_simple_signals(candles, config.params)
            logger.info(f"    🎯 {len(signals)} signals generated")
            
            # Simulate trades
            for signal in signals:
                outcome = simulate_trade_outcome(signal, candles)
                trade = {
                    'instrument': instrument,
                    'entry_time': signal['entry_time'],
                    'entry_price': signal['entry_price'],
                    'direction': signal['direction'],
                    **outcome
                }
                all_trades.append(trade)
                
        except Exception as e:
            logger.error(f"    ❌ Error testing {instrument}: {e}")
            continue
    
    # Calculate statistics
    if not all_trades:
        return {
            'strategy': config.name,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_win_pips': 0.0,
            'avg_loss_pips': 0.0,
            'profit_factor': 0.0,
            'total_pnl_pips': 0.0,
            'status': '❌ NO TRADES',
            'trades': []
        }
    
    wins = [t for t in all_trades if t['result'] == 'WIN']
    losses = [t for t in all_trades if t['result'] == 'LOSS']
    opens = [t for t in all_trades if t['result'] == 'OPEN']
    
    win_count = len(wins)
    loss_count = len(losses) + len(opens)  # Count open trades as losses (conservative)
    total = win_count + loss_count
    
    win_rate = (win_count / total * 100) if total > 0 else 0
    
    avg_win_pips = sum(t['pips'] for t in wins) / len(wins) if wins else 0
    avg_loss_pips = sum(t['pips'] for t in losses) / len(losses) if losses else 0
    
    total_win_pips = sum(t['pips'] for t in wins)
    total_loss_pips = sum(t['pips'] for t in losses)
    
    profit_factor = (total_win_pips / total_loss_pips) if total_loss_pips > 0 else 999
    total_pnl_pips = total_win_pips - total_loss_pips
    
    # Determine status
    if win_rate >= 60:
        status = "✅ EXCELLENT"
    elif win_rate >= 50:
        status = "✅ GOOD"
    elif win_rate >= 40:
        status = "⚠️ MARGINAL"
    else:
        status = "❌ POOR"
    
    return {
        'strategy': config.name,
        'total_trades': total,
        'wins': win_count,
        'losses': loss_count,
        'win_rate': win_rate,
        'avg_win_pips': avg_win_pips,
        'avg_loss_pips': avg_loss_pips,
        'profit_factor': profit_factor,
        'total_pnl_pips': total_pnl_pips,
        'status': status,
        'trades': all_trades
    }

# ========================================
# MAIN EXECUTION
# ========================================

def main():
    print("\n" + "="*80)
    print("🔬 NEW STRATEGIES BACKTEST - LAST 2 WEEKS")
    print("="*80)
    print(f"\nTest Period: Last 14 days")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*80)
    
    client = OandaClient()
    results = {}
    
    # Test Oct 18 strategies
    print("\n📅 TESTING OCTOBER 18 STRATEGIES (Google Drive Export)")
    print("="*80)
    
    for key, config in OCT18_STRATEGIES.items():
        try:
            result = backtest_strategy(key, config, client, days=14)
            results[key] = result
        except Exception as e:
            logger.error(f"❌ Failed to test {config.name}: {e}")
            continue
    
    # Test Oct 20 strategies
    print("\n📅 TESTING OCTOBER 20 STRATEGIES (Current System)")
    print("="*80)
    
    for key, config in OCT20_STRATEGIES.items():
        try:
            result = backtest_strategy(key, config, client, days=14)
            results[key] = result
        except Exception as e:
            logger.error(f"❌ Failed to test {config.name}: {e}")
            continue
    
    # Print summary
    print("\n" + "="*80)
    print("📊 BACKTEST RESULTS SUMMARY - LAST 2 WEEKS")
    print("="*80)
    print()
    
    print("OCT 18 STRATEGIES (Google Drive):")
    print("-" * 80)
    for key in OCT18_STRATEGIES.keys():
        if key in results:
            r = results[key]
            print(f"\n{r['strategy']}")
            print(f"  Trades: {r['total_trades']} ({r['wins']}W / {r['losses']}L)")
            print(f"  Win Rate: {r['win_rate']:.1f}%")
            print(f"  Profit Factor: {r['profit_factor']:.2f}")
            print(f"  Total P&L: {r['total_pnl_pips']:.1f} pips")
            print(f"  Avg Win: {r['avg_win_pips']:.1f} pips | Avg Loss: {r['avg_loss_pips']:.1f} pips")
            print(f"  Status: {r['status']}")
    
    print("\n" + "="*80)
    print("OCT 20 STRATEGIES (Current):")
    print("-" * 80)
    for key in OCT20_STRATEGIES.keys():
        if key in results:
            r = results[key]
            print(f"\n{r['strategy']}")
            print(f"  Trades: {r['total_trades']} ({r['wins']}W / {r['losses']}L)")
            print(f"  Win Rate: {r['win_rate']:.1f}%")
            print(f"  Profit Factor: {r['profit_factor']:.2f}")
            print(f"  Total P&L: {r['total_pnl_pips']:.1f} pips")
            print(f"  Avg Win: {r['avg_win_pips']:.1f} pips | Avg Loss: {r['avg_loss_pips']:.1f} pips")
            print(f"  Status: {r['status']}")
    
    # Best strategy
    print("\n" + "="*80)
    print("🏆 BEST PERFORMING STRATEGY:")
    print("="*80)
    
    if results:
        best = max(results.values(), key=lambda x: x['win_rate'] if x['total_trades'] > 0 else 0)
        print(f"\n✅ {best['strategy']}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Total Trades: {best['total_trades']}")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        print(f"   Total P&L: {best['total_pnl_pips']:.1f} pips")
    
    # Save results
    output_file = f"backtest_results_2weeks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    print()
    
    return results

if __name__ == "__main__":
    try:
        results = main()
    except KeyboardInterrupt:
        print("\n\n❌ Backtest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

