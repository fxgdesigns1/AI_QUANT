#!/usr/bin/env python3
"""Test backtest with quality filters"""
import os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml') as f:
    accounts_data = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts_data['accounts'][0]['id']

from datetime import datetime
from src.core.oanda_client import OandaClient
from src.core.trade_quality_filter import get_trade_quality_filter
import requests

print("="*80)
print("2-WEEK BACKTEST - WITH QUALITY FILTERS")
print("="*80)
print()

client = OandaClient(account_id=os.environ['OANDA_ACCOUNT_ID'])
quality_filter = get_trade_quality_filter()

# Test strategies
strategies = [
    {'name': 'Momentum Trading', 'instrument': 'XAU_USD', 'is_gold': True},
    {'name': 'Gold Scalping', 'instrument': 'XAU_USD', 'is_gold': True},
    {'name': 'Momentum V2', 'instrument': 'USD_JPY', 'is_gold': False},
    {'name': 'Ultra Strict Forex', 'instrument': 'EUR_USD', 'is_gold': False},
    {'name': 'GBP Strategy #1', 'instrument': 'GBP_USD', 'is_gold': False},
]

results = []

for strategy in strategies:
    print(f"Testing {strategy['name']} ({strategy['instrument']})...")
    
    try:
        headers = {
            'Authorization': f'Bearer {os.environ["OANDA_API_KEY"]}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://api-fxpractice.oanda.com/v3/instruments/{strategy['instrument']}/candles"
        response = requests.get(
            url,
            headers=headers,
            params={'count': 1000, 'granularity': 'M15', 'price': 'M'},
            timeout=10
        )
        
        data = response.json()
        
        if 'candles' not in data:
            print(f"   ⚠️ No data\n")
            continue
        
        candles = data['candles']
        
        # Backtest with filters
        signals_generated = 0
        signals_passed_filter = 0
        trades_executed = 0
        wins = 0
        losses = 0
        total_pnl = 0
        
        for i in range(30, len(candles) - 20):
            try:
                # Calculate indicators
                closes = [float(c['mid']['c']) for c in candles[i-20:i]]
                highs = [float(c['mid']['h']) for c in candles[i-20:i]]
                lows = [float(c['mid']['l']) for c in candles[i-20:i]]
                
                current = closes[-1]
                ma_5 = sum(closes[-5:]) / 5
                ma_10 = sum(closes[-10:]) / 10
                ma_20 = sum(closes) / 20
                
                # Momentum
                momentum = (closes[-1] - closes[-10]) / closes[-10]
                
                # ADX (simplified)
                tr_values = []
                for j in range(1, 15):
                    high_low = highs[-j] - lows[-j]
                    tr_values.append(high_low)
                atr = sum(tr_values) / len(tr_values)
                
                # Simple ADX proxy
                adx = abs(ma_5 - ma_20) / ma_20 * 1000
                
                # Spread (estimate)
                spread = atr * 0.3
                
                # Signal generation
                signal = None
                if ma_5 > ma_10 and momentum > 0.001:
                    signal = 'BUY'
                    signals_generated += 1
                elif ma_5 < ma_10 and momentum < -0.001:
                    signal = 'SELL'
                    signals_generated += 1
                
                if signal:
                    # Apply quality filter
                    filter_result = quality_filter.filter_trade(
                        instrument=strategy['instrument'],
                        direction=signal,
                        momentum=momentum,
                        adx=adx,
                        atr=atr,
                        spread=spread,
                        current_price=current,
                        ma_5=ma_5,
                        ma_10=ma_10,
                        ma_20=ma_20,
                        current_time=datetime.now()
                    )
                    
                    if filter_result.passes:
                        signals_passed_filter += 1
                        trades_executed += 1
                        
                        # Check outcome
                        entry = current
                        
                        # Check next candles for TP/SL
                        if strategy['is_gold']:
                            tp_distance = 15.0
                            sl_distance = 2.5
                        else:
                            pip_value = 0.01 if 'JPY' in strategy['instrument'] else 0.0001
                            tp_distance = 30.0 * pip_value
                            sl_distance = 10.0 * pip_value
                        
                        hit_tp = False
                        hit_sl = False
                        
                        for j in range(i+1, min(i+20, len(candles))):
                            future_high = float(candles[j]['mid']['h'])
                            future_low = float(candles[j]['mid']['l'])
                            
                            if signal == 'BUY':
                                if future_high >= entry + tp_distance:
                                    hit_tp = True
                                    break
                                elif future_low <= entry - sl_distance:
                                    hit_sl = True
                                    break
                            else:  # SELL
                                if future_low <= entry - tp_distance:
                                    hit_tp = True
                                    break
                                elif future_high >= entry + sl_distance:
                                    hit_sl = True
                                    break
                        
                        if hit_tp:
                            wins += 1
                            total_pnl += tp_distance if strategy['is_gold'] else tp_distance * 1000000
                        elif hit_sl:
                            losses += 1
                            total_pnl -= sl_distance if strategy['is_gold'] else sl_distance * 1000000
            
            except Exception as e:
                continue
        
        win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0
        filter_rate = (signals_passed_filter / signals_generated * 100) if signals_generated > 0 else 0
        
        results.append({
            'name': strategy['name'],
            'instrument': strategy['instrument'],
            'signals_generated': signals_generated,
            'signals_filtered': signals_generated - signals_passed_filter,
            'filter_rate': filter_rate,
            'trades': trades_executed,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'pnl': total_pnl
        })
        
        print(f"   Signals: {signals_generated} generated, {signals_filtered} filtered ({100-filter_rate:.0f}% rejected)")
        print(f"   Trades: {trades_executed}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   P&L: ${total_pnl:,.0f}")
        print()
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}\n")

print("="*80)
print("FILTERED vs UNFILTERED COMPARISON")
print("="*80)
print()

for result in results:
    print(f"{result['name']} ({result['instrument']}):")
    print(f"  Signals Generated: {result['signals_generated']}")
    print(f"  Filtered Out: {result['signals_filtered']} ({100-result['filter_rate']:.0f}%)")
    print(f"  Trades Executed: {result['trades']}")
    print(f"  Win Rate: {result['win_rate']:.1f}%")
    print(f"  P&L: ${result['pnl']:+,.0f}")
    print()

# Overall
total_signals = sum([r['signals_generated'] for r in results])
total_filtered = sum([r['signals_filtered'] for r in results])
total_trades = sum([r['trades'] for r in results])
total_wins = sum([r['wins'] for r in results])
total_losses = sum([r['losses'] for r in results])
total_pnl = sum([r['pnl'] for r in results])

print("-"*80)
print("OVERALL WITH FILTERS:")
print(f"  Signals: {total_signals} generated, {total_filtered} filtered ({total_filtered/total_signals*100:.0f}% rejected)")
print(f"  Trades: {total_trades}")
print(f"  Win Rate: {(total_wins/total_trades*100) if total_trades > 0 else 0:.1f}%")
print(f"  Total P&L: ${total_pnl:+,.0f}")
print()
print("="*80)

