#!/usr/bin/env python3
"""
ICT OTE Strategy Optimizer with Monte Carlo Simulation
Tests the ICT OTE strategy with different parameter combinations
"""

import sys
import os
import random
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

class ICTOTEOptimizer:
    """ICT OTE Strategy Optimizer with Monte Carlo Simulation"""
    
    def __init__(self):
        self.name = "ICT OTE Strategy Optimizer"
        self.instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Parameter ranges for optimization
        self.parameter_ranges = {
            'ote_min_retracement': (0.40, 0.60),  # 40-60%
            'ote_max_retracement': (0.70, 0.85),  # 70-85%
            'fvg_min_size': (0.0003, 0.001),     # 0.03-0.1%
            'ob_lookback': (10, 30),              # 10-30 candles
            'bos_confirmation': (2, 5),           # 2-5 candles
            'stop_loss_atr': (1.5, 3.0),         # 1.5-3.0 ATR
            'take_profit_atr': (2.0, 4.0),       # 2.0-4.0 ATR
            'min_confidence': (0.60, 0.85),      # 60-85%
            'max_positions': (1, 5),              # 1-5 positions
            'daily_trade_limit': (5, 20)          # 5-20 trades/day
        }
        
        # Results storage
        self.results = []
        
    def generate_random_parameters(self) -> Dict:
        """Generate random parameters within defined ranges"""
        params = {}
        for param, (min_val, max_val) in self.parameter_ranges.items():
            if isinstance(min_val, int):
                params[param] = random.randint(min_val, max_val)
            else:
                params[param] = round(random.uniform(min_val, max_val), 3)
        return params
    
    def simulate_ict_ote_strategy(self, params: Dict, days: int = 30) -> Dict:
        """Simulate ICT OTE strategy with given parameters"""
        
        # Generate simulated price data
        np.random.seed(42)  # For reproducible results
        
        # Simulate price movements for each instrument
        total_trades = 0
        winning_trades = 0
        total_pnl = 0.0
        max_drawdown = 0.0
        current_drawdown = 0.0
        peak_balance = 10000.0
        current_balance = 10000.0
        
        for instrument in self.instruments:
            # Generate price data (simplified simulation)
            price_data = self.generate_price_data(instrument, days)
            
            # Simulate ICT OTE trades
            trades = self.simulate_ict_trades(price_data, params, instrument)
            
            for trade in trades:
                total_trades += 1
                
                # Simulate trade outcome based on ICT OTE principles
                win_probability = self.calculate_win_probability(trade, params)
                is_winner = random.random() < win_probability
                
                if is_winner:
                    winning_trades += 1
                    pnl = trade['risk_reward'] * trade['risk_amount']
                else:
                    pnl = -trade['risk_amount']
                
                total_pnl += pnl
                current_balance += pnl
                
                # Track drawdown
                if current_balance > peak_balance:
                    peak_balance = current_balance
                    current_drawdown = 0.0
                else:
                    current_drawdown = (peak_balance - current_balance) / peak_balance
                    max_drawdown = max(max_drawdown, current_drawdown)
        
        # Calculate metrics
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit_factor = abs(total_pnl / max(1, total_pnl - total_pnl)) if total_pnl != 0 else 0
        sharpe_ratio = self.calculate_sharpe_ratio(total_pnl, max_drawdown)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'final_balance': current_balance,
            'trades_per_day': total_trades / days
        }
    
    def generate_price_data(self, instrument: str, days: int) -> List[Dict]:
        """Generate simulated price data for an instrument"""
        # Base price for different instruments
        base_prices = {
            'XAU_USD': 2650.0,
            'EUR_USD': 1.0850,
            'GBP_USD': 1.2500,
            'USD_JPY': 150.0
        }
        
        base_price = base_prices.get(instrument, 1.0)
        price_data = []
        
        # Generate hourly data for the specified days
        hours = days * 24
        current_price = base_price
        
        for hour in range(hours):
            # Simulate price movement with some trend and volatility
            trend = np.sin(hour / 24 * 2 * np.pi) * 0.001  # Daily cycle
            volatility = np.random.normal(0, 0.002)  # 0.2% hourly volatility
            change = trend + volatility
            
            current_price *= (1 + change)
            
            price_data.append({
                'timestamp': datetime.now() - timedelta(hours=hours-hour),
                'open': current_price,
                'high': current_price * (1 + abs(volatility)),
                'low': current_price * (1 - abs(volatility)),
                'close': current_price,
                'volume': random.uniform(1000, 5000)
            })
        
        return price_data
    
    def simulate_ict_trades(self, price_data: List[Dict], params: Dict, instrument: str) -> List[Dict]:
        """Simulate ICT OTE trades based on price data"""
        trades = []
        
        # Look for ICT OTE setups
        for i in range(params['ob_lookback'], len(price_data) - 10):
            current_candle = price_data[i]
            
            # Check for OTE retracement
            if self.is_ote_setup(price_data, i, params):
                # Calculate trade parameters
                entry_price = current_candle['close']
                
                # Calculate ATR for stop loss and take profit
                atr = self.calculate_atr(price_data, i, 14)
                
                stop_loss = entry_price * (1 - params['stop_loss_atr'] * atr)
                take_profit = entry_price * (1 + params['take_profit_atr'] * atr)
                
                risk_amount = abs(entry_price - stop_loss) / entry_price
                reward_amount = abs(take_profit - entry_price) / entry_price
                risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0
                
                # Only take trades with good risk/reward
                if risk_reward >= 1.5:  # Minimum 1:1.5 R:R
                    trades.append({
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_amount': risk_amount * 1000,  # $1000 position
                        'risk_reward': risk_reward,
                        'confidence': random.uniform(params['min_confidence'], 0.95)
                    })
        
        return trades
    
    def is_ote_setup(self, price_data: List[Dict], index: int, params: Dict) -> bool:
        """Check if current position is an ICT OTE setup"""
        if index < params['ob_lookback']:
            return False
        
        # Look for recent swing high/low
        recent_data = price_data[index-params['ob_lookback']:index+1]
        swing_high = max(candle['high'] for candle in recent_data)
        swing_low = min(candle['low'] for candle in recent_data)
        
        current_price = price_data[index]['close']
        
        # Check for OTE retracement (50-79% of recent move)
        if current_price < swing_high and current_price > swing_low:
            move_size = swing_high - swing_low
            retracement = (swing_high - current_price) / move_size
            
            if params['ote_min_retracement'] <= retracement <= params['ote_max_retracement']:
                return True
        
        return False
    
    def calculate_atr(self, price_data: List[Dict], index: int, period: int) -> float:
        """Calculate Average True Range"""
        if index < period:
            return 0.01  # Default ATR
        
        true_ranges = []
        for i in range(index - period + 1, index + 1):
            high = price_data[i]['high']
            low = price_data[i]['low']
            prev_close = price_data[i-1]['close'] if i > 0 else price_data[i]['open']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges)
    
    def calculate_win_probability(self, trade: Dict, params: Dict) -> float:
        """Calculate win probability based on ICT OTE principles"""
        base_probability = 0.65  # Base ICT OTE win rate
        
        # Adjust based on confidence
        confidence_factor = trade['confidence'] / 0.8  # Normalize to 0.8
        
        # Adjust based on risk/reward ratio
        rr_factor = min(trade['risk_reward'] / 2.0, 1.0)  # Cap at 2:1
        
        # Adjust based on OTE retracement quality
        ote_factor = 1.0  # Could be enhanced with actual retracement calculation
        
        final_probability = base_probability * confidence_factor * rr_factor * ote_factor
        return min(max(final_probability, 0.3), 0.9)  # Clamp between 30-90%
    
    def calculate_sharpe_ratio(self, total_pnl: float, max_drawdown: float) -> float:
        """Calculate simplified Sharpe ratio"""
        if max_drawdown == 0:
            return 0.0
        return total_pnl / (max_drawdown * 10000)  # Simplified calculation
    
    def run_optimization(self, iterations: int = 1000) -> List[Dict]:
        """Run Monte Carlo optimization"""
        logger.info(f"🎲 Starting ICT OTE Monte Carlo Optimization")
        logger.info(f"📊 Testing {iterations} parameter combinations")
        logger.info(f"📊 Instruments: {', '.join(self.instruments)}")
        logger.info(f"📊 Target: 5-15 trades per day")
        
        for i in range(iterations):
            if (i + 1) % 100 == 0:
                logger.info(f"   Progress: {i+1}/{iterations}...")
            
            # Generate random parameters
            params = self.generate_random_parameters()
            
            # Simulate strategy
            results = self.simulate_ict_ote_strategy(params, days=30)
            
            # Calculate fitness score
            fitness = self.calculate_fitness(results)
            
            # Store results
            result_entry = {
                'iteration': i + 1,
                'parameters': params,
                'results': results,
                'fitness': fitness
            }
            self.results.append(result_entry)
        
        # Sort by fitness score
        self.results.sort(key=lambda x: x['fitness'], reverse=True)
        
        return self.results[:10]  # Return top 10
    
    def calculate_fitness(self, results: Dict) -> float:
        """Calculate fitness score for optimization"""
        # Weighted fitness function
        win_rate_score = min(results['win_rate'] / 100, 1.0) * 0.3
        profit_score = min(results['total_pnl'] / 1000, 1.0) * 0.25  # Normalize to $1000
        drawdown_score = max(0, 1.0 - results['max_drawdown']) * 0.2
        trades_score = min(results['trades_per_day'] / 10, 1.0) * 0.15  # Target 10 trades/day
        sharpe_score = min(results['sharpe_ratio'] / 2.0, 1.0) * 0.1
        
        return win_rate_score + profit_score + drawdown_score + trades_score + sharpe_score
    
    def print_results(self, top_results: List[Dict]):
        """Print optimization results"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🏆 ICT OTE STRATEGY OPTIMIZATION RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Tested {len(self.results)} parameter combinations")
        logger.info(f"📊 Top 10 configurations:")
        logger.info(f"{'='*80}")
        
        logger.info(f"{'Rank':<4} {'Win Rate':<8} {'Trades/Day':<10} {'P&L':<8} {'Drawdown':<9} {'Fitness':<7}")
        logger.info(f"{'-'*80}")
        
        for i, result in enumerate(top_results[:10], 1):
            r = result['results']
            logger.info(f"{i:<4} {r['win_rate']:<7.1f}% {r['trades_per_day']:<9.1f} ${r['total_pnl']:<6.0f} {r['max_drawdown']*100:<8.1f}% {result['fitness']:<6.3f}")
        
        # Print best configuration details
        if top_results:
            best = top_results[0]
            logger.info(f"\n🏆 BEST CONFIGURATION:")
            logger.info(f"{'='*50}")
            logger.info(f"Win Rate: {best['results']['win_rate']:.1f}%")
            logger.info(f"Total Trades: {best['results']['total_trades']}")
            logger.info(f"Trades/Day: {best['results']['trades_per_day']:.1f}")
            logger.info(f"Total P&L: ${best['results']['total_pnl']:.0f}")
            logger.info(f"Max Drawdown: {best['results']['max_drawdown']*100:.1f}%")
            logger.info(f"Profit Factor: {best['results']['profit_factor']:.2f}")
            logger.info(f"Sharpe Ratio: {best['results']['sharpe_ratio']:.2f}")
            logger.info(f"Fitness Score: {best['fitness']:.3f}")
            
            logger.info(f"\n📋 OPTIMAL PARAMETERS:")
            logger.info(f"{'='*50}")
            for param, value in best['parameters'].items():
                logger.info(f"{param}: {value}")

def main():
    """Main optimization function"""
    optimizer = ICTOTEOptimizer()
    
    # Run optimization
    top_results = optimizer.run_optimization(iterations=1000)
    
    # Print results
    optimizer.print_results(top_results)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"ict_ote_optimization_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_iterations': len(optimizer.results),
            'top_10_results': top_results[:10],
            'all_results': optimizer.results
        }, f, indent=2, default=str)
    
    logger.info(f"\n💾 Results saved to {filename}")
    
    return top_results

if __name__ == "__main__":
    main()