#!/usr/bin/env python3
"""
Monte Carlo Optimization - GOLD ONLY
Focus on XAU_USD which showed 89% WR and +1.0% profit
"""

import sys
sys.path.insert(0, '.')

import random
import numpy as np
from datetime import datetime
from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🥇 MONTE CARLO OPTIMIZATION - GOLD ONLY")
print("="*100)
print("Optimizing for XAU_USD which showed 89% WR")
print("="*100)

# Get Gold data (7 days)
fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['XAU_USD'], hours=168)
gold_candles = historical_data['XAU_USD']

print(f"\n✅ Retrieved {len(gold_candles)} Gold candles (7 days)")

# Calculate market move
start = float(gold_candles[0]['close'])
end = float(gold_candles[-1]['close'])
move = ((end - start) / start) * 100
print(f"✅ Gold moved {move:+.2f}%\n")

# Parameter ranges for Gold-specific optimization
PARAM_RANGES = {
    'momentum_period': [30, 40, 50, 60, 80, 100],  # Test different lookback periods
    'trend_period': [50, 80, 100, 150, 200],
    'min_momentum': [0.0001, 0.0002, 0.0003, 0.0005, 0.0008, 0.001],
    'min_adx': [3.0, 5.0, 8.0, 10.0, 12.0, 15.0],
    'min_quality_score': [5, 8, 10, 12, 15, 20],
    'stop_loss_atr': [1.5, 2.0, 2.5, 3.0, 4.0],
    'take_profit_atr': [7.5, 10.0, 12.5, 15.0, 20.0],
}

def simulate_strategy(params, gold_candles):
    """Simulate strategy with given parameters"""
    try:
        # Load fresh strategy
        strategy = get_momentum_trading_strategy()
        
        # Apply parameters
        strategy.momentum_period = params['momentum_period']
        strategy.trend_period = params['trend_period']
        strategy.min_momentum = params['min_momentum']
        strategy.min_adx = params['min_adx']
        strategy.min_quality_score = params['min_quality_score']
        strategy.stop_loss_atr = params['stop_loss_atr']
        strategy.take_profit_atr = params['take_profit_atr']
        
        # Focus ONLY on Gold
        strategy.instruments = ['XAU_USD']
        
        # Clear prefill
        strategy.price_history['XAU_USD'] = []
        
        # Disable time gap
        strategy.min_time_between_trades_minutes = 0
        
        # Disable problematic filters
        strategy.max_trades_per_day = 1000
        
        # Generate signals
        all_signals = []
        
        for candle_idx, candle in enumerate(gold_candles):
            close_price = float(candle['close'])
            
            market_data = MarketData(
                pair='XAU_USD',
                bid=close_price,
                ask=close_price + 0.1,
                timestamp=candle['time'],
                is_live=False,
                data_source='OANDA_Historical',
                spread=0.1,
                last_update_age=0
            )
            
            signals = strategy.analyze_market({'XAU_USD': market_data})
            
            if signals:
                for signal in signals:
                    all_signals.append({
                        'entry_idx': candle_idx,
                        'entry_price': close_price,
                        'side': signal.side.value,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                    })
        
        # Simulate all trades
        wins = 0
        losses = 0
        total_pnl = 0
        
        for signal in all_signals:
            entry_idx = signal['entry_idx']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            side = signal['side']
            
            # Get subsequent candles
            remaining = gold_candles[entry_idx+1:]
            max_check = min(len(remaining), 288)  # 24 hours max
            
            outcome = None
            exit_price = entry_price
            
            for candle in remaining[:max_check]:
                high = float(candle['high'])
                low = float(candle['low'])
                
                if side == 'BUY':
                    if high >= take_profit:
                        outcome = 'WIN'
                        exit_price = take_profit
                        break
                    elif low <= stop_loss:
                        outcome = 'LOSS'
                        exit_price = stop_loss
                        break
                elif side == 'SELL':
                    if low <= take_profit:
                        outcome = 'WIN'
                        exit_price = take_profit
                        break
                    elif high >= stop_loss:
                        outcome = 'LOSS'
                        exit_price = stop_loss
                        break
            
            # Calculate P&L
            if outcome == 'WIN':
                wins += 1
                if side == 'BUY':
                    pnl = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - exit_price) / entry_price) * 100
                total_pnl += pnl
            elif outcome == 'LOSS':
                losses += 1
                if side == 'BUY':
                    pnl = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl = ((entry_price - exit_price) / entry_price) * 100
                total_pnl += pnl
        
        total_trades = wins + losses
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        # Fitness score: Maximize profit and win rate
        fitness = total_pnl * (1 + win_rate)  # Bonus for high win rate
        
        return {
            'signals': len(all_signals),
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'fitness': fitness,
            'signals_per_day': len(all_signals) / 7
        }
        
    except Exception as e:
        return {
            'signals': 0,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_pnl': -100,
            'fitness': -100,
            'error': str(e)
        }

# Run Monte Carlo
print("🎲 Running Monte Carlo Optimization...")
print("-"*100)

ITERATIONS = 500
results = []

for i in range(ITERATIONS):
    # Generate random parameters
    params = {
        'momentum_period': random.choice(PARAM_RANGES['momentum_period']),
        'trend_period': random.choice(PARAM_RANGES['trend_period']),
        'min_momentum': random.choice(PARAM_RANGES['min_momentum']),
        'min_adx': random.choice(PARAM_RANGES['min_adx']),
        'min_quality_score': random.choice(PARAM_RANGES['min_quality_score']),
        'stop_loss_atr': random.choice(PARAM_RANGES['stop_loss_atr']),
        'take_profit_atr': random.choice(PARAM_RANGES['take_profit_atr']),
    }
    
    # Simulate
    performance = simulate_strategy(params, gold_candles)
    
    result = {
        'iteration': i + 1,
        'params': params,
        'performance': performance
    }
    results.append(result)
    
    if (i + 1) % 50 == 0:
        print(f"  Completed {i+1}/{ITERATIONS} iterations...")

# Sort by fitness
results.sort(key=lambda x: x['performance']['fitness'], reverse=True)

# Show top 10
print(f"\n{'='*100}")
print("TOP 10 CONFIGURATIONS:")
print(f"{'='*100}\n")

for i, result in enumerate(results[:10], 1):
    perf = result['performance']
    params = result['params']
    
    print(f"#{i} - Fitness: {perf['fitness']:.2f}")
    print(f"   Signals: {perf['signals']} ({perf['signals_per_day']:.1f}/day)")
    print(f"   Trades: {perf['trades']} ({perf['wins']}W/{perf['losses']}L)")
    print(f"   Win Rate: {perf['win_rate']*100:.1f}%")
    print(f"   Total P&L: {perf['total_pnl']:+.2f}%")
    print(f"   Parameters:")
    print(f"      momentum_period: {params['momentum_period']}")
    print(f"      trend_period: {params['trend_period']}")
    print(f"      min_momentum: {params['min_momentum']}")
    print(f"      min_adx: {params['min_adx']}")
    print(f"      min_quality_score: {params['min_quality_score']}")
    print(f"      stop_loss_atr: {params['stop_loss_atr']}")
    print(f"      take_profit_atr: {params['take_profit_atr']}")
    print()

# Best configuration
best = results[0]
print(f"{'='*100}")
print("BEST CONFIGURATION:")
print(f"{'='*100}\n")

print(f"🏆 Configuration #{best['iteration']}")
print(f"\n📊 Performance:")
print(f"   Signals: {best['performance']['signals']} ({best['performance']['signals_per_day']:.1f}/day)")
print(f"   Trades: {best['performance']['trades']}")
print(f"   Wins: {best['performance']['wins']} ✅")
print(f"   Losses: {best['performance']['losses']} ❌")
print(f"   Win Rate: {best['performance']['win_rate']*100:.1f}%")
print(f"   Total P&L: {best['performance']['total_pnl']:+.2f}%")
print(f"   Fitness Score: {best['performance']['fitness']:.2f}")

print(f"\n⚙️  Optimal Parameters:")
for param, value in best['params'].items():
    print(f"   {param}: {value}")

# Financial projections with best config
pnl = best['performance']['total_pnl']
print(f"\n💰 Financial Projections (Best Config on $10,000):")
print(f"   Weekly: {pnl:+.2f}% = ${10000*(pnl/100):+,.0f}")
print(f"   Monthly: {pnl*4.3:+.1f}% = ${10000*(pnl*4.3/100):+,.0f}")
print(f"   Annual: {pnl*52:+.0f}% = ${10000*(pnl*52/100):+,.0f}")

if pnl > 5:
    print(f"\n✅ EXCELLENT - Profitable configuration found!")
elif pnl > 0:
    print(f"\n⚠️  PROFITABLE but below target")
else:
    print(f"\n❌ Still losing - need different approach")

print(f"\n{'='*100}")
print("NEXT STEPS:")
print(f"{'='*100}\n")

print(f"1. Apply best configuration to momentum_trading.py")
print(f"2. Configure strategy for GOLD ONLY (remove forex pairs)")
print(f"3. Test with wider SL/TP if needed")
print(f"4. Deploy Gold-only strategy")
print(f"5. Monitor live performance")

print(f"\n{'='*100}")




