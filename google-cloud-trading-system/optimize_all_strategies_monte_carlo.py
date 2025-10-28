#!/usr/bin/env python3
"""
Monte Carlo Optimization for ALL Strategies (Phase 5)
Focus on Trump DNA, 75% Champion, and Ultra Strict first, then test others
Lookback: 48 hours (weekly cycle as specified)
"""

import sys
sys.path.insert(0, '.')

import os
import importlib
import random
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData

print("🎲 MONTE CARLO OPTIMIZATION - ALL STRATEGIES")
print("="*100)
print("Lookback: 48 hours (weekly cycle)")
print("="*100)

# Strategy configurations
PRIORITY_STRATEGIES = [
    {
        'name': 'Trump DNA (Momentum Trading)',
        'module': 'src.strategies.momentum_trading',
        'function': 'get_momentum_trading_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
        'iterations': 300,  # More iterations for priority
        'priority': 1
    },
    {
        'name': '75% WR Champion',
        'module': 'src.strategies.champion_75wr',
        'class': 'UltraSelective75WRChampion',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
        'iterations': 300,
        'priority': 1
    },
    {
        'name': 'Ultra Strict Forex',
        'module': 'src.strategies.ultra_strict_forex',
        'function': 'get_ultra_strict_forex_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'iterations': 300,
        'priority': 1
    },
]

OTHER_STRATEGIES = [
    {
        'name': 'Gold Scalping',
        'module': 'src.strategies.gold_scalping',
        'function': 'get_gold_scalping_strategy',
        'instruments': ['XAU_USD'],
        'iterations': 100
    },
    {
        'name': 'Range Trading',
        'module': 'src.strategies.range_trading',
        'function': 'get_range_trading_strategy',
        'instruments': ['EUR_USD', 'GBP_USD'],
        'iterations': 100
    },
]

# Parameter ranges for Monte Carlo (based on real market analysis)
PARAM_RANGES = {
    'min_adx': (5, 15),              # ADX threshold
    'min_momentum': (0.0003, 0.0015), # Momentum threshold (0.03% - 0.15%)
    'min_volume': (0.03, 0.15),       # Volume threshold
    'quality_threshold': (10, 25),    # Quality score
    'min_quality_score': (10, 25),    # Quality score (alternate name)
    'confidence_threshold': (0.40, 0.65),  # Confidence
    'min_signal_strength': (0.15, 0.35),   # Signal strength
    'quality_score_threshold': (0.40, 0.70),  # Quality (0-1 scale)
    'signal_strength_min': (0.15, 0.35),  # Signal strength (alternate name)
}

def generate_random_params(strategy_name: str) -> Dict:
    """Generate random parameters for a strategy"""
    params = {}
    
    # Randomly vary each parameter within its range
    for param_name, (min_val, max_val) in PARAM_RANGES.items():
        params[param_name] = random.uniform(min_val, max_val)
    
    return params

def apply_params_to_strategy(strategy, params: Dict):
    """Apply parameters to a strategy object"""
    applied = []
    for param_name, value in params.items():
        if hasattr(strategy, param_name):
            setattr(strategy, param_name, value)
            applied.append(param_name)
    return applied

def evaluate_strategy(strategy, historical_data: Dict, instruments: List[str]) -> Dict:
    """Evaluate strategy performance on historical data"""
    signals_generated = 0
    total_bars = 0
    
    try:
        # Build price history if strategy uses it
        if hasattr(strategy, 'price_history'):
            for instrument in instruments:
                if instrument not in strategy.price_history:
                    strategy.price_history[instrument] = []
                
                if instrument in historical_data:
                    for candle in historical_data[instrument]:
                        strategy.price_history[instrument].append({
                            'time': candle['time'],
                            'close': float(candle['close']),
                            'high': float(candle['high']),
                            'low': float(candle['low']),
                            'volume': float(candle['volume'])
                        })
                    total_bars += len(historical_data[instrument])
        
        # Disable time gap filter for backtest
        if hasattr(strategy, 'min_time_between_trades_minutes'):
            original_gap = strategy.min_time_between_trades_minutes
            strategy.min_time_between_trades_minutes = 0
        
        # Test signal generation on each bar
        for instrument in instruments:
            if instrument not in historical_data:
                continue
            
            for candle in historical_data[instrument]:
                # Create MarketData
                close_price = float(candle['close'])
                market_data = MarketData(
                    pair=instrument,
                    bid=close_price,
                    ask=close_price + 0.0001,
                    timestamp=candle['time'],
                    is_live=False,
                    data_source='OANDA_Historical',
                    spread=0.0001,
                    last_update_age=0
                )
                
                # Try to generate signal (different methods for different strategies)
                signal = None
                if hasattr(strategy, 'analyze_market'):
                    # Momentum trading style
                    signals = strategy.analyze_market({instrument: market_data})
                    if signals:
                        signal = signals[0]
                elif hasattr(strategy, 'generate_signals'):
                    # Champion style - needs DataFrame
                    pass  # Skip for now, different interface
                
                if signal:
                    signals_generated += 1
        
        # Restore time gap
        if hasattr(strategy, 'min_time_between_trades_minutes'):
            strategy.min_time_between_trades_minutes = original_gap
        
        # Calculate fitness score
        # Target: 3-10 signals per day over 48 hours (2 days) = 6-20 signals
        target_min = 6
        target_max = 20
        
        if target_min <= signals_generated <= target_max:
            # Perfect range
            fitness = 100.0
        elif signals_generated < target_min:
            # Too few signals - penalize
            fitness = max(0, (signals_generated / target_min) * 100)
        else:
            # Too many signals - slight penalty
            excess = signals_generated - target_max
            fitness = max(50, 100 - excess * 2)
        
        return {
            'signals': signals_generated,
            'bars': total_bars,
            'fitness': fitness,
            'signals_per_day': signals_generated / 2  # 48h = 2 days
        }
        
    except Exception as e:
        return {
            'signals': 0,
            'bars': total_bars,
            'fitness': 0.0,
            'signals_per_day': 0.0,
            'error': str(e)
        }

def monte_carlo_optimize(strategy_config: Dict, historical_data: Dict) -> List[Dict]:
    """Run Monte Carlo optimization on a strategy"""
    print(f"\n{'='*100}")
    print(f"Optimizing: {strategy_config['name']}")
    print(f"Instruments: {', '.join(strategy_config['instruments'])}")
    print(f"Iterations: {strategy_config['iterations']}")
    print(f"{'='*100}\n")
    
    results = []
    
    for i in range(strategy_config['iterations']):
        try:
            # Load fresh strategy instance
            if 'function' in strategy_config:
                module = importlib.import_module(strategy_config['module'])
                get_strategy = getattr(module, strategy_config['function'])
                strategy = get_strategy()
            elif 'class' in strategy_config:
                module = importlib.import_module(strategy_config['module'])
                StrategyClass = getattr(module, strategy_config['class'])
                strategy = StrategyClass()
            else:
                raise ValueError("Must specify 'function' or 'class'")
            
            # Generate random parameters
            params = generate_random_params(strategy_config['name'])
            
            # Apply parameters
            applied = apply_params_to_strategy(strategy, params)
            
            # Evaluate
            performance = evaluate_strategy(
                strategy,
                historical_data,
                strategy_config['instruments']
            )
            
            result = {
                'iteration': i + 1,
                'params': params,
                'applied_params': applied,
                'performance': performance
            }
            results.append(result)
            
            if (i + 1) % 50 == 0:
                print(f"  Completed {i+1}/{strategy_config['iterations']} iterations...")
        
        except Exception as e:
            print(f"  ⚠️  Iteration {i+1} failed: {e}")
            continue
    
    # Sort by fitness
    results.sort(key=lambda x: x['performance']['fitness'], reverse=True)
    
    # Show top 5
    print(f"\n📊 TOP 5 CONFIGURATIONS:")
    print("-"*100)
    for i, result in enumerate(results[:5], 1):
        perf = result['performance']
        print(f"\n#{i} - Fitness: {perf['fitness']:.1f}, Signals/day: {perf['signals_per_day']:.1f}")
        print(f"   Parameters applied: {', '.join(result['applied_params'])}")
        for param in result['applied_params']:
            print(f"     {param}: {result['params'][param]:.4f}")
    
    return results

# ====================================================================================================
# MAIN EXECUTION
# ====================================================================================================

print("\n📥 Fetching 48-hour historical data...")
fetcher = get_historical_fetcher()

# Get all unique instruments
all_instruments = set()
for strat in PRIORITY_STRATEGIES + OTHER_STRATEGIES:
    all_instruments.update(strat['instruments'])

historical_data = fetcher.get_recent_data_for_strategy(list(all_instruments), hours=48)
print(f"✅ Retrieved data for {len(all_instruments)} instruments")

# Show market moves
print(f"\n📊 MARKET MOVES (48 hours):")
print("-"*100)
for instrument in sorted(all_instruments):
    if instrument in historical_data and len(historical_data[instrument]) > 0:
        candles = historical_data[instrument]
        start = float(candles[0]['close'])
        end = float(candles[-1]['close'])
        move_pct = ((end - start) / start) * 100
        print(f"{instrument}: {move_pct:+.2f}% ({len(candles)} bars)")

# Optimize priority strategies
print(f"\n{'='*100}")
print("PHASE 1: PRIORITY STRATEGIES")
print(f"{'='*100}")

priority_results = {}
for strat_config in PRIORITY_STRATEGIES:
    results = monte_carlo_optimize(strat_config, historical_data)
    priority_results[strat_config['name']] = results

# Optimize other strategies
print(f"\n{'='*100}")
print("PHASE 2: OTHER STRATEGIES")
print(f"{'='*100}")

other_results = {}
for strat_config in OTHER_STRATEGIES:
    try:
        results = monte_carlo_optimize(strat_config, historical_data)
        other_results[strat_config['name']] = results
    except Exception as e:
        print(f"❌ {strat_config['name']}: {e}")

# Final summary
print(f"\n{'='*100}")
print("FINAL SUMMARY")
print(f"{'='*100}\n")

print("PRIORITY STRATEGIES:")
for name, results in priority_results.items():
    if results:
        best = results[0]
        fitness = best['performance']['fitness']
        spd = best['performance']['signals_per_day']
        status = "✅" if spd >= 3 else "❌"
        print(f"{status} {name}: {spd:.1f} signals/day (fitness: {fitness:.1f})")

print("\nOTHER STRATEGIES:")
for name, results in other_results.items():
    if results:
        best = results[0]
        fitness = best['performance']['fitness']
        spd = best['performance']['signals_per_day']
        status = "✅" if spd >= 3 else "⚠️"
        print(f"{status} {name}: {spd:.1f} signals/day (fitness: {fitness:.1f})")

print(f"\n{'='*100}")
print("NEXT STEPS:")
print(f"{'='*100}")
print("1. Review top configurations above")
print("2. Apply best parameters to strategy files")
print("3. Test dashboards and strategy switcher")
print("4. Deploy to Google Cloud")
print(f"{'='*100}")













