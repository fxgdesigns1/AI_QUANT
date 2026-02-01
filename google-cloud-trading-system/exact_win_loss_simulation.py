#!/usr/bin/env python3
"""
EXACT WIN/LOSS SIMULATION - Previous Week
Simulate all trades with real SL/TP and determine exact outcomes
"""

import sys
sys.path.insert(0, '.')

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy
from datetime import datetime

print("💰 EXACT WIN/LOSS SIMULATION - PREVIOUS WEEK")
print("="*100)
print("Simulating all trades with real stop-loss and take-profit levels")
print("="*100)

# Get data
fetcher = get_historical_fetcher()
all_instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
historical_data = fetcher.get_recent_data_for_strategy(all_instruments, hours=168)

print(f"\n✅ Retrieved 7-day data for {len(all_instruments)} instruments")

# Load strategy
strategy = get_momentum_trading_strategy()

# Clear prefill
for inst in all_instruments:
    if inst in strategy.price_history:
        strategy.price_history[inst] = []

# Disable time gap
strategy.min_time_between_trades_minutes = 0

# Get strategy instruments
strategy_instruments = [inst for inst in strategy.instruments if inst in all_instruments]

print(f"\n⚙️  GENERATING SIGNALS:")
print("-"*100)

# Find shortest history
min_length = min(len(historical_data[inst]) for inst in strategy_instruments if inst in historical_data)

all_signals = []

# Process all instruments together to generate signals
for candle_idx in range(min_length):
    market_data_dict = {}
    
    for instrument in strategy_instruments:
        if instrument not in historical_data:
            continue
        
        candle = historical_data[instrument][candle_idx]
        close_price = float(candle['close'])
        
        market_data_dict[instrument] = MarketData(
            pair=instrument,
            bid=close_price,
            ask=close_price + 0.0001,
            timestamp=candle['time'],
            is_live=False,
            data_source='OANDA_Historical',
            spread=0.0001,
            last_update_age=0
        )
    
    signals = strategy.analyze_market(market_data_dict)
    
    if signals:
        for signal in signals:
            # Store signal with entry candle index for simulation
            all_signals.append({
                'instrument': signal.instrument,
                'side': signal.side.value,
                'entry_idx': candle_idx,
                'entry_price': signal.side == 1 and market_data_dict[signal.instrument].ask or market_data_dict[signal.instrument].bid,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'confidence': signal.confidence,
                'timestamp': historical_data[signal.instrument][candle_idx]['time']
            })

print(f"✅ Generated {len(all_signals)} signals")

# Now simulate each trade
print(f"\n💰 SIMULATING TRADES:")
print("="*100)

trade_results = []

for idx, signal in enumerate(all_signals, 1):
    instrument = signal['instrument']
    entry_idx = signal['entry_idx']
    entry_price = signal['entry_price']
    stop_loss = signal['stop_loss']
    take_profit = signal['take_profit']
    side = signal['side']
    
    print(f"\n{'─'*100}")
    print(f"Trade #{idx}: {instrument} {side}")
    print(f"{'─'*100}")
    print(f"Entry: ${entry_price:.4f} at {signal['timestamp']}")
    print(f"Stop Loss: ${stop_loss:.4f}")
    print(f"Take Profit: ${take_profit:.4f}")
    
    # Get subsequent candles to simulate trade
    remaining_candles = historical_data[instrument][entry_idx+1:]
    
    # Simulate trade outcome
    outcome = None
    exit_idx = None
    exit_price = None
    bars_held = 0
    max_bars_to_check = min(len(remaining_candles), 288)  # Max 24 hours (288 x 5min)
    
    for candle_offset, candle in enumerate(remaining_candles[:max_bars_to_check]):
        bars_held = candle_offset + 1
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])
        
        if side == 'BUY':
            # Check if TP hit
            if high >= take_profit:
                outcome = 'WIN'
                exit_price = take_profit
                exit_idx = entry_idx + candle_offset + 1
                break
            # Check if SL hit
            elif low <= stop_loss:
                outcome = 'LOSS'
                exit_price = stop_loss
                exit_idx = entry_idx + candle_offset + 1
                break
        
        elif side == 'SELL':
            # Check if TP hit
            if low <= take_profit:
                outcome = 'WIN'
                exit_price = take_profit
                exit_idx = entry_idx + candle_offset + 1
                break
            # Check if SL hit
            elif high >= stop_loss:
                outcome = 'LOSS'
                exit_price = stop_loss
                exit_idx = entry_idx + candle_offset + 1
                break
    
    # If no hit, still open or would have closed at end
    if outcome is None:
        outcome = 'OPEN/TIMEOUT'
        exit_price = remaining_candles[min(bars_held-1, len(remaining_candles)-1)]['close'] if remaining_candles else entry_price
        bars_held = min(bars_held, len(remaining_candles))
    
    # Calculate P&L
    if side == 'BUY':
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:  # SELL
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
    
    result_icon = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "⏳"
    
    print(f"Exit: ${exit_price:.4f} after {bars_held} bars ({bars_held*5:.0f} minutes)")
    print(f"{result_icon} Outcome: {outcome}")
    print(f"P&L: {pnl_pct:+.2f}%")
    
    trade_results.append({
        'trade_num': idx,
        'instrument': instrument,
        'side': side,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'outcome': outcome,
        'pnl_pct': pnl_pct,
        'bars_held': bars_held,
        'timestamp': signal['timestamp']
    })

# COMPREHENSIVE SUMMARY
print(f"\n{'='*100}")
print("EXACT WIN/LOSS RESULTS - TRUMP DNA STRATEGY")
print(f"{'='*100}\n")

wins = [t for t in trade_results if t['outcome'] == 'WIN']
losses = [t for t in trade_results if t['outcome'] == 'LOSS']
open_trades = [t for t in trade_results if t['outcome'] == 'OPEN/TIMEOUT']

print(f"📊 TRADE STATISTICS:")
print(f"   Total Trades: {len(trade_results)}")
print(f"   Wins: {len(wins)} ✅")
print(f"   Losses: {len(losses)} ❌")
print(f"   Open/Timeout: {len(open_trades)} ⏳")
print(f"   Win Rate: {len(wins)/len(trade_results)*100:.1f}%" if len(trade_results) > 0 else "   Win Rate: N/A")

# Calculate total P&L
total_pnl = sum(t['pnl_pct'] for t in trade_results)
avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

print(f"\n💰 PROFIT & LOSS:")
print(f"   Total P&L: {total_pnl:+.2f}%")
print(f"   Average Win: {avg_win:+.2f}%")
print(f"   Average Loss: {avg_loss:+.2f}%")
print(f"   Profit Factor: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   Profit Factor: N/A")

print(f"\n📅 DAILY BREAKDOWN:")
for day in range(7):
    day_trades = [t for t in trade_results if day*288 <= t['trade_num'] <= (day+1)*288]
    day_wins = len([t for t in day_trades if t['outcome'] == 'WIN'])
    day_losses = len([t for t in day_trades if t['outcome'] == 'LOSS'])
    day_pnl = sum(t['pnl_pct'] for t in day_trades)
    
    print(f"   Day {day+1}: {len(day_trades)} trades ({day_wins}W/{day_losses}L) = {day_pnl:+.1f}%")

# Breakdown by instrument
print(f"\n📊 BREAKDOWN BY PAIR:")
for instrument in strategy_instruments:
    inst_trades = [t for t in trade_results if t['instrument'] == instrument]
    if inst_trades:
        inst_wins = len([t for t in inst_trades if t['outcome'] == 'WIN'])
        inst_losses = len([t for t in inst_trades if t['outcome'] == 'LOSS'])
        inst_pnl = sum(t['pnl_pct'] for t in inst_trades)
        inst_wr = inst_wins / len(inst_trades) * 100 if inst_trades else 0
        
        print(f"   {instrument}: {len(inst_trades)} trades ({inst_wins}W/{inst_losses}L) = {inst_pnl:+.1f}% (WR: {inst_wr:.0f}%)")

# Financial projections
print(f"\n💵 FINANCIAL PROJECTIONS (on $10,000 account):")
print("-"*100)

if total_pnl != 0:
    weekly_profit = 10000 * (total_pnl / 100)
    monthly_profit = weekly_profit * 4.3
    annual_profit = monthly_profit * 12
    
    print(f"Weekly Return: {total_pnl:+.1f}% = ${weekly_profit:+,.0f}")
    print(f"Monthly Projection: {total_pnl*4.3:+.0f}% = ${monthly_profit:+,.0f}")
    print(f"Annual Projection: {total_pnl*52:+.0f}% = ${annual_profit:+,.0f}")

print(f"\n{'='*100}")
print("IF ALL 10 STRATEGIES WERE WORKING:")
print(f"{'='*100}\n")

# Extrapolate to full system
if len(trade_results) > 0:
    # Conservative: Assume all strategies perform similarly
    projected_trades = len(trade_results) * 10
    projected_wins = len(wins) * 10
    projected_losses = len(losses) * 10
    projected_pnl = total_pnl * 10
    
    print(f"Projected Trades: {projected_trades}")
    print(f"Projected Wins: {projected_wins} ✅")
    print(f"Projected Losses: {projected_losses} ❌")
    print(f"Projected Win Rate: {len(wins)/len(trade_results)*100:.1f}%")
    print(f"\nProjected Total P&L: {projected_pnl:+.1f}%")
    
    full_weekly = 10000 * (projected_pnl / 100)
    full_monthly = full_weekly * 4.3
    
    print(f"\nOn $10,000 account:")
    print(f"   Weekly: ${full_weekly:+,.0f}")
    print(f"   Monthly: ${full_monthly:+,.0f}")
    
    if full_monthly >= 300000:
        print(f"\n✅ EXCEEDS $300k MONTHLY TARGET!")
    elif full_monthly >= 100000:
        print(f"\n⚠️  Good but below $300k target")
    else:
        print(f"\n❌ Below target - needs optimization")

print(f"\n{'='*100}")
print("SUMMARY:")
print(f"{'='*100}\n")

print(f"✅ TRUMP DNA ALONE (Current Working State):")
print(f"   - {len(trade_results)} trades this week")
print(f"   - {len(wins)} wins, {len(losses)} losses")
print(f"   - {total_pnl:+.1f}% total return")
print(f"   - ${10000 * (total_pnl/100):+,.0f} on $10k account")

print(f"\n⏳ IF ALL 10 STRATEGIES WORKING:")
print(f"   - {projected_trades if len(trade_results) > 0 else 0} trades (estimated)")
print(f"   - {projected_wins if len(trade_results) > 0 else 0} wins, {projected_losses if len(trade_results) > 0 else 0} losses")
print(f"   - {projected_pnl if len(trade_results) > 0 else 0:+.0f}% total return")
print(f"   - ${(10000 * (projected_pnl/100)) if len(trade_results) > 0 else 0:+,.0f} on $10k account")

print(f"\n{'='*100}")




