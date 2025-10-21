#!/usr/bin/env python3
"""
ICT OTE Strategy Backtester
Comprehensive backtesting with multiple pairs and detailed analysis
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ICTOTEBacktester:
    """Comprehensive ICT OTE Strategy Backtester"""
    
    def __init__(self):
        self.name = "ICT OTE Strategy Backtester"
        self.instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
        
        # Optimal parameters from optimization
        self.optimal_params = {
            'ote_min_retracement': 0.483,
            'ote_max_retracement': 0.841,
            'fvg_min_size': 0.001,
            'ob_lookback': 23,
            'bos_confirmation': 4,
            'stop_loss_atr': 1.571,
            'take_profit_atr': 3.106,
            'min_confidence': 0.834,
            'max_positions': 3,
            'daily_trade_limit': 13
        }
        
        # Results storage
        self.results = {}
        
    def generate_realistic_price_data(self, instrument: str, days: int = 30) -> pd.DataFrame:
        """Generate realistic price data with proper market behavior"""
        
        # Base prices and characteristics for different instruments
        instrument_configs = {
            'XAU_USD': {'base_price': 2650.0, 'daily_volatility': 0.015, 'trend_strength': 0.3},
            'EUR_USD': {'base_price': 1.0850, 'daily_volatility': 0.008, 'trend_strength': 0.2},
            'GBP_USD': {'base_price': 1.2500, 'daily_volatility': 0.012, 'trend_strength': 0.25},
            'USD_JPY': {'base_price': 150.0, 'daily_volatility': 0.010, 'trend_strength': 0.2},
            'AUD_USD': {'base_price': 0.6400, 'daily_volatility': 0.010, 'trend_strength': 0.2},
            'NZD_USD': {'base_price': 0.5900, 'daily_volatility': 0.012, 'trend_strength': 0.2}
        }
        
        config = instrument_configs.get(instrument, instrument_configs['EUR_USD'])
        base_price = config['base_price']
        daily_vol = config['daily_volatility']
        trend_strength = config['trend_strength']
        
        # Generate hourly data
        hours = days * 24
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(days=days),
            periods=hours,
            freq='H'
        )
        
        # Generate price series with realistic behavior
        np.random.seed(hash(instrument) % 2**32)  # Different seed per instrument
        
        prices = []
        current_price = base_price
        
        for i in range(hours):
            # Market session awareness
            hour = timestamps[i].hour
            session_multiplier = self.get_session_multiplier(hour)
            
            # Trend component (longer-term movement)
            trend = np.sin(i / (24 * 7) * 2 * np.pi) * trend_strength * daily_vol / 24
            
            # Random walk component
            random_walk = np.random.normal(0, daily_vol / np.sqrt(24))
            
            # Mean reversion component
            mean_reversion = -0.1 * (current_price - base_price) / base_price * daily_vol / 24
            
            # Combine components
            price_change = (trend + random_walk + mean_reversion) * session_multiplier
            current_price *= (1 + price_change)
            
            # Generate OHLC from current price
            volatility = abs(np.random.normal(0, daily_vol / 24))
            high = current_price * (1 + volatility)
            low = current_price * (1 - volatility)
            open_price = current_price * (1 + np.random.normal(0, daily_vol / 48))
            close_price = current_price
            
            prices.append({
                'timestamp': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': np.random.uniform(1000, 5000)
            })
        
        return pd.DataFrame(prices)
    
    def get_session_multiplier(self, hour: int) -> float:
        """Get volatility multiplier based on trading session"""
        # London session (8-17 GMT)
        if 8 <= hour <= 17:
            return 1.5
        # NY session (13-22 GMT) 
        elif 13 <= hour <= 22:
            return 1.3
        # Asian session (0-8 GMT)
        elif 0 <= hour <= 8:
            return 0.8
        # Overlap periods
        elif 13 <= hour <= 17:  # London-NY overlap
            return 2.0
        else:
            return 0.5
    
    def detect_ict_levels(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """Detect ICT levels (Order Blocks, FVGs, etc.)"""
        levels = []
        
        for i in range(params['ob_lookback'], len(df) - 5):
            # Look for Order Blocks (previous high/low areas)
            recent_data = df.iloc[i-params['ob_lookback']:i+1]
            
            # Find swing points
            highs = recent_data['high'].rolling(window=5, center=True).max()
            lows = recent_data['low'].rolling(window=5, center=True).min()
            
            # Check for Order Block formations
            if i >= 5:
                current_high = df.iloc[i]['high']
                current_low = df.iloc[i]['low']
                
                # Bullish Order Block: Previous high that was broken
                if current_high > recent_data['high'].max():
                    ob_level = recent_data['high'].max()
                    levels.append({
                        'type': 'bullish_ob',
                        'price': ob_level,
                        'timestamp': df.iloc[i]['timestamp'],
                        'strength': 0.8
                    })
                
                # Bearish Order Block: Previous low that was broken
                if current_low < recent_data['low'].min():
                    ob_level = recent_data['low'].min()
                    levels.append({
                        'type': 'bearish_ob',
                        'price': ob_level,
                        'timestamp': df.iloc[i]['timestamp'],
                        'strength': 0.8
                    })
            
            # Check for Fair Value Gaps (FVG)
            if i >= 2:
                fvg = self.detect_fvg(df.iloc[i-2:i+1], params['fvg_min_size'])
                if fvg:
                    levels.append(fvg)
        
        return levels
    
    def detect_fvg(self, candles: pd.DataFrame, min_size: float) -> Dict:
        """Detect Fair Value Gap in 3-candle pattern"""
        if len(candles) != 3:
            return None
        
        c1, c2, c3 = candles.iloc[0], candles.iloc[1], candles.iloc[2]
        
        # Bullish FVG: Gap between c1 high and c3 low
        if c1['high'] < c3['low']:
            gap_size = (c3['low'] - c1['high']) / c1['high']
            if gap_size >= min_size:
                return {
                    'type': 'bullish_fvg',
                    'price': (c1['high'] + c3['low']) / 2,
                    'timestamp': c2['timestamp'],
                    'strength': min(gap_size / min_size, 1.0)
                }
        
        # Bearish FVG: Gap between c1 low and c3 high
        elif c1['low'] > c3['high']:
            gap_size = (c1['low'] - c3['high']) / c1['high']
            if gap_size >= min_size:
                return {
                    'type': 'bearish_fvg',
                    'price': (c1['low'] + c3['high']) / 2,
                    'timestamp': c2['timestamp'],
                    'strength': min(gap_size / min_size, 1.0)
                }
        
        return None
    
    def find_ote_entries(self, df: pd.DataFrame, levels: List[Dict], params: Dict) -> List[Dict]:
        """Find Optimal Trade Entry (OTE) setups"""
        entries = []
        
        for i in range(20, len(df) - 10):
            current_price = df.iloc[i]['close']
            
            # Look for recent swing move
            lookback = 20
            recent_data = df.iloc[i-lookback:i+1]
            
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            swing_range = swing_high - swing_low
            
            if swing_range == 0:
                continue
            
            # Check for OTE retracement
            if swing_low < current_price < swing_high:
                retracement = (swing_high - current_price) / swing_range
                
                if params['ote_min_retracement'] <= retracement <= params['ote_max_retracement']:
                    # Determine direction based on recent trend
                    trend = (swing_high - swing_low) / swing_low
                    direction = 'long' if trend > 0 else 'short'
                    
                    # Check for nearby ICT levels
                    nearby_levels = [l for l in levels 
                                   if abs(l['price'] - current_price) / current_price < 0.01]
                    
                    if nearby_levels:
                        # Calculate trade parameters
                        atr = self.calculate_atr(df, i, 14)
                        
                        if direction == 'long':
                            stop_loss = current_price * (1 - params['stop_loss_atr'] * atr)
                            take_profit = current_price * (1 + params['take_profit_atr'] * atr)
                        else:
                            stop_loss = current_price * (1 + params['stop_loss_atr'] * atr)
                            take_profit = current_price * (1 - params['take_profit_atr'] * atr)
                        
                        risk_amount = abs(current_price - stop_loss) / current_price
                        reward_amount = abs(take_profit - current_price) / current_price
                        risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0
                        
                        # Only take trades with good risk/reward
                        if risk_reward >= 1.5:
                            entries.append({
                                'timestamp': df.iloc[i]['timestamp'],
                                'instrument': 'UNKNOWN',  # Will be set by caller
                                'direction': direction,
                                'entry_price': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'risk_amount': risk_amount,
                                'reward_amount': reward_amount,
                                'risk_reward': risk_reward,
                                'confidence': min(0.6 + retracement * 0.3, 0.95),
                                'ote_retracement': retracement,
                                'nearby_levels': len(nearby_levels)
                            })
        
        return entries
    
    def calculate_atr(self, df: pd.DataFrame, index: int, period: int) -> float:
        """Calculate Average True Range"""
        if index < period:
            return 0.01
        
        true_ranges = []
        for i in range(index - period + 1, index + 1):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_close = df.iloc[i-1]['close'] if i > 0 else df.iloc[i]['open']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges)
    
    def simulate_trades(self, entries: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Simulate trade execution and outcomes"""
        trades = []
        
        for entry in entries:
            # Find entry index in dataframe
            entry_time = entry['timestamp']
            entry_idx = df[df['timestamp'] == entry_time].index
            
            if len(entry_idx) == 0:
                continue
            
            entry_idx = entry_idx[0]
            
            # Simulate trade execution
            trade = {
                'entry_time': entry_time,
                'instrument': entry['instrument'],
                'direction': entry['direction'],
                'entry_price': entry['entry_price'],
                'stop_loss': entry['stop_loss'],
                'take_profit': entry['take_profit'],
                'risk_reward': entry['risk_reward'],
                'confidence': entry['confidence'],
                'ote_retracement': entry['ote_retracement']
            }
            
            # Check if trade hits stop loss or take profit
            hit_sl = False
            hit_tp = False
            exit_price = 0
            exit_time = None
            
            # Look ahead for exit conditions
            for i in range(entry_idx + 1, min(entry_idx + 100, len(df))):  # Max 100 hours
                candle = df.iloc[i]
                
                if entry['direction'] == 'long':
                    # Check for stop loss hit
                    if candle['low'] <= entry['stop_loss']:
                        hit_sl = True
                        exit_price = entry['stop_loss']
                        exit_time = candle['timestamp']
                        break
                    # Check for take profit hit
                    elif candle['high'] >= entry['take_profit']:
                        hit_tp = True
                        exit_price = entry['take_profit']
                        exit_time = candle['timestamp']
                        break
                else:  # short
                    # Check for stop loss hit
                    if candle['high'] >= entry['stop_loss']:
                        hit_sl = True
                        exit_price = entry['stop_loss']
                        exit_time = candle['timestamp']
                        break
                    # Check for take profit hit
                    elif candle['low'] <= entry['take_profit']:
                        hit_tp = True
                        exit_price = entry['take_profit']
                        exit_time = candle['timestamp']
                        break
            
            # If no exit found, close at end of data
            if not hit_sl and not hit_tp:
                exit_price = df.iloc[-1]['close']
                exit_time = df.iloc[-1]['timestamp']
            
            # Calculate P&L
            if entry['direction'] == 'long':
                pnl_pct = (exit_price - entry['entry_price']) / entry['entry_price']
            else:
                pnl_pct = (entry['entry_price'] - exit_price) / entry['entry_price']
            
            # Determine if trade was profitable
            is_winner = pnl_pct > 0
            
            trade.update({
                'exit_time': exit_time,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'is_winner': is_winner,
                'hit_sl': hit_sl,
                'hit_tp': hit_tp,
                'duration_hours': (exit_time - entry_time).total_seconds() / 3600
            })
            
            trades.append(trade)
        
        return trades
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive trading metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'max_pnl': 0,
                'min_pnl': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'avg_trade_duration': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['is_winner'])
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        pnls = [t['pnl_pct'] for t in trades]
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        max_pnl = max(pnls)
        min_pnl = min(pnls)
        
        # Profit factor
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown calculation
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = max(drawdown) if len(drawdown) > 0 else 0
        
        # Trade duration
        durations = [t['duration_hours'] for t in trades]
        avg_trade_duration = np.mean(durations) if durations else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'max_pnl': max_pnl,
            'min_pnl': min_pnl,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'avg_trade_duration': avg_trade_duration,
            'best_trade': max_pnl,
            'worst_trade': min_pnl
        }
    
    def run_backtest(self, days: int = 30) -> Dict:
        """Run comprehensive backtest"""
        logger.info(f"🎯 Starting ICT OTE Strategy Backtest")
        logger.info(f"📊 Period: {days} days")
        logger.info(f"📊 Instruments: {', '.join(self.instruments)}")
        logger.info(f"📊 Parameters: {self.optimal_params}")
        
        all_trades = []
        instrument_results = {}
        
        for instrument in self.instruments:
            logger.info(f"\n📈 Backtesting {instrument}...")
            
            # Generate price data
            df = self.generate_realistic_price_data(instrument, days)
            
            # Detect ICT levels
            levels = self.detect_ict_levels(df, self.optimal_params)
            logger.info(f"   Found {len(levels)} ICT levels")
            
            # Find OTE entries
            entries = self.find_ote_entries(df, levels, self.optimal_params)
            logger.info(f"   Found {len(entries)} OTE entries")
            
            # Set instrument for entries
            for entry in entries:
                entry['instrument'] = instrument
            
            # Simulate trades
            trades = self.simulate_trades(entries, df)
            logger.info(f"   Executed {len(trades)} trades")
            
            # Calculate metrics for this instrument
            metrics = self.calculate_metrics(trades)
            instrument_results[instrument] = {
                'trades': trades,
                'metrics': metrics
            }
            
            all_trades.extend(trades)
        
        # Calculate overall metrics
        overall_metrics = self.calculate_metrics(all_trades)
        
        # Group trades by day for daily analysis
        daily_trades = {}
        for trade in all_trades:
            day = trade['entry_time'].date()
            if day not in daily_trades:
                daily_trades[day] = []
            daily_trades[day].append(trade)
        
        # Calculate daily metrics
        daily_metrics = {}
        for day, day_trades in daily_trades.items():
            daily_metrics[str(day)] = self.calculate_metrics(day_trades)
        
        results = {
            'overall_metrics': overall_metrics,
            'instrument_results': instrument_results,
            'daily_metrics': daily_metrics,
            'all_trades': all_trades,
            'parameters': self.optimal_params,
            'backtest_period': f"{days} days",
            'instruments_tested': self.instruments
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print comprehensive backtest results"""
        metrics = results['overall_metrics']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🏆 ICT OTE STRATEGY BACKTEST RESULTS")
        logger.info(f"{'='*80}")
        
        logger.info(f"📊 OVERALL PERFORMANCE:")
        logger.info(f"   Total Trades: {metrics['total_trades']}")
        logger.info(f"   Win Rate: {metrics['win_rate']:.1f}%")
        logger.info(f"   Winning Trades: {metrics['winning_trades']}")
        logger.info(f"   Losing Trades: {metrics['losing_trades']}")
        logger.info(f"   Total P&L: {metrics['total_pnl']:.2f}%")
        logger.info(f"   Average P&L: {metrics['avg_pnl']:.2f}%")
        logger.info(f"   Best Trade: {metrics['best_trade']:.2f}%")
        logger.info(f"   Worst Trade: {metrics['worst_trade']:.2f}%")
        logger.info(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        logger.info(f"   Max Drawdown: {metrics['max_drawdown']:.2f}%")
        logger.info(f"   Avg Duration: {metrics['avg_trade_duration']:.1f} hours")
        
        logger.info(f"\n📈 INSTRUMENT BREAKDOWN:")
        logger.info(f"{'Instrument':<10} {'Trades':<6} {'Win Rate':<8} {'P&L':<8} {'Best':<8} {'Worst':<8}")
        logger.info(f"{'-'*60}")
        
        for instrument, data in results['instrument_results'].items():
            m = data['metrics']
            logger.info(f"{instrument:<10} {m['total_trades']:<6} {m['win_rate']:<7.1f}% {m['total_pnl']:<7.2f}% {m['best_trade']:<7.2f}% {m['worst_trade']:<7.2f}%")
        
        # Show top 5 trades
        if results['all_trades']:
            logger.info(f"\n🏆 TOP 5 TRADES:")
            sorted_trades = sorted(results['all_trades'], key=lambda x: x['pnl_pct'], reverse=True)
            for i, trade in enumerate(sorted_trades[:5], 1):
                logger.info(f"   {i}. {trade['instrument']} {trade['direction']} - {trade['pnl_pct']:.2f}% ({trade['duration_hours']:.1f}h)")
        
        # Show worst 5 trades
        if results['all_trades']:
            logger.info(f"\n💔 WORST 5 TRADES:")
            sorted_trades = sorted(results['all_trades'], key=lambda x: x['pnl_pct'])
            for i, trade in enumerate(sorted_trades[:5], 1):
                logger.info(f"   {i}. {trade['instrument']} {trade['direction']} - {trade['pnl_pct']:.2f}% ({trade['duration_hours']:.1f}h)")

def main():
    """Main backtesting function"""
    backtester = ICTOTEBacktester()
    
    # Run backtest
    results = backtester.run_backtest(days=30)
    
    # Print results
    backtester.print_results(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"ict_ote_backtest_{timestamp}.json"
    
    # Convert datetime objects to strings for JSON serialization
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=convert_datetime)
    
    logger.info(f"\n💾 Results saved to {filename}")
    
    return results

if __name__ == "__main__":
    main()