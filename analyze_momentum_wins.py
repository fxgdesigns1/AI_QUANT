#!/usr/bin/env python3
"""
Analyze Momentum Trading strategy wins vs losses to find patterns
"""
import csv
import pandas as pd
from datetime import datetime
from collections import defaultdict
import pytz

# Read the blotter
blotter_path = 'backtest_blotter_sync/blotter_101-004-30719775-008.csv'

df = pd.read_csv(blotter_path)

# Convert timestamps
london_tz = pytz.timezone('Europe/London')
# Parse timestamps - CSV has format like "2025-11-13T00:30:16+00:00"
df['entry_dt'] = pd.to_datetime(df['entry_timestamp'], utc=True).dt.tz_convert(london_tz)
df['exit_dt'] = pd.to_datetime(df['exit_timestamp'], utc=True).dt.tz_convert(london_tz)

# Classify trades
df['is_win'] = df['pnl'] > 0
df['is_loss'] = df['pnl'] < 0
df['entry_hour_london'] = df['entry_dt'].dt.hour
df['entry_day'] = df['entry_dt'].dt.day_name()

# Session classification
def classify_session(hour):
    if 8 <= hour < 13:  # London session
        return 'London'
    elif 13 <= hour < 17:  # London/NY overlap (prime time)
        return 'Prime (London/NY)'
    elif 17 <= hour < 21:  # NY session
        return 'NY'
    else:
        return 'Off-hours'

df['session'] = df['entry_hour_london'].apply(classify_session)

# Position size classification
df['position_size_category'] = df['units'].apply(lambda x: 'Large (200k)' if x >= 100000 else 'Small (10k)')

print("=" * 80)
print("MOMENTUM TRADING - WIN/LOSS PATTERN ANALYSIS")
print("=" * 80)
print(f"\nTotal Trades: {len(df)}")
print(f"Wins: {df['is_win'].sum()} ({df['is_win'].sum()/len(df)*100:.1f}%)")
print(f"Losses: {df['is_loss'].sum()} ({df['is_loss'].sum()/len(df)*100:.1f}%)")
print(f"Total P&L: ${df['pnl'].sum():.2f}")
print(f"Average Win: ${df[df['is_win']]['pnl'].mean():.2f}")
print(f"Average Loss: ${df[df['is_loss']]['pnl'].mean():.2f}")

# 1. INSTRUMENT ANALYSIS
print("\n" + "=" * 80)
print("1. INSTRUMENT PATTERNS")
print("=" * 80)
for instrument in df['instrument'].unique():
    inst_df = df[df['instrument'] == instrument]
    wins = inst_df['is_win'].sum()
    losses = inst_df['is_loss'].sum()
    total = len(inst_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = inst_df['pnl'].sum()
    avg_win = inst_df[inst_df['is_win']]['pnl'].mean() if wins > 0 else 0
    avg_loss = inst_df[inst_df['is_loss']]['pnl'].mean() if losses > 0 else 0
    
    print(f"\n{instrument}:")
    print(f"  Total: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")
    print(f"  Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")

# 2. POSITION SIZE ANALYSIS
print("\n" + "=" * 80)
print("2. POSITION SIZE PATTERNS")
print("=" * 80)
for size_cat in df['position_size_category'].unique():
    size_df = df[df['position_size_category'] == size_cat]
    wins = size_df['is_win'].sum()
    losses = size_df['is_loss'].sum()
    total = len(size_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = size_df['pnl'].sum()
    
    print(f"\n{size_cat}:")
    print(f"  Total: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")

# 3. SESSION ANALYSIS
print("\n" + "=" * 80)
print("3. TRADING SESSION PATTERNS")
print("=" * 80)
for session in df['session'].unique():
    session_df = df[df['session'] == session]
    wins = session_df['is_win'].sum()
    losses = session_df['is_loss'].sum()
    total = len(session_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = session_df['pnl'].sum()
    
    print(f"\n{session}:")
    print(f"  Total: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")

# 4. HOUR OF DAY ANALYSIS
print("\n" + "=" * 80)
print("4. HOUR OF DAY PATTERNS (London Time)")
print("=" * 80)
hour_stats = []
for hour in sorted(df['entry_hour_london'].unique()):
    hour_df = df[df['entry_hour_london'] == hour]
    wins = hour_df['is_win'].sum()
    losses = hour_df['is_loss'].sum()
    total = len(hour_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = hour_df['pnl'].sum()
    
    hour_stats.append({
        'hour': hour,
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'pnl': total_pnl
    })
    
    if total >= 3:  # Only show hours with meaningful data
        print(f"  {hour:02d}:00 - Total: {total:2d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {win_rate:5.1f}% | P&L: ${total_pnl:7.2f}")

# 5. SIDE (BUY vs SELL) ANALYSIS
print("\n" + "=" * 80)
print("5. BUY vs SELL PATTERNS")
print("=" * 80)
for side in df['side'].unique():
    side_df = df[df['side'] == side]
    wins = side_df['is_win'].sum()
    losses = side_df['is_loss'].sum()
    total = len(side_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = side_df['pnl'].sum()
    
    print(f"\n{side}:")
    print(f"  Total: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")

# 6. HOLDING TIME ANALYSIS
print("\n" + "=" * 80)
print("6. HOLDING TIME PATTERNS")
print("=" * 80)
df['holding_category'] = pd.cut(df['holding_minutes'], 
                                 bins=[0, 5, 15, 60, 1440], 
                                 labels=['0-5min', '5-15min', '15-60min', '60min+'])

for cat in df['holding_category'].cat.categories:
    cat_df = df[df['holding_category'] == cat]
    if len(cat_df) == 0:
        continue
    wins = cat_df['is_win'].sum()
    losses = cat_df['is_loss'].sum()
    total = len(cat_df)
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = cat_df['pnl'].sum()
    avg_hold = cat_df['holding_minutes'].mean()
    
    print(f"\n{cat} (avg: {avg_hold:.1f} min):")
    print(f"  Total: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")

# 7. COMBINED PATTERNS - Best combinations
print("\n" + "=" * 80)
print("7. BEST WINNING COMBINATIONS")
print("=" * 80)

# Instrument + Session
print("\nBy Instrument + Session:")
for inst in df['instrument'].unique():
    for session in df['session'].unique():
        combo_df = df[(df['instrument'] == inst) & (df['session'] == session)]
        if len(combo_df) >= 3:  # Minimum 3 trades
            wins = combo_df['is_win'].sum()
            total = len(combo_df)
            win_rate = (wins / total * 100) if total > 0 else 0
            total_pnl = combo_df['pnl'].sum()
            if win_rate >= 50 or total_pnl > 0:
                print(f"  {inst} + {session}: {total} trades, {win_rate:.1f}% WR, ${total_pnl:.2f} P&L")

# Instrument + Position Size
print("\nBy Instrument + Position Size:")
for inst in df['instrument'].unique():
    for size in df['position_size_category'].unique():
        combo_df = df[(df['instrument'] == inst) & (df['position_size_category'] == size)]
        if len(combo_df) >= 3:
            wins = combo_df['is_win'].sum()
            total = len(combo_df)
            win_rate = (wins / total * 100) if total > 0 else 0
            total_pnl = combo_df['pnl'].sum()
            if win_rate >= 50 or total_pnl > 0:
                print(f"  {inst} + {size}: {total} trades, {win_rate:.1f}% WR, ${total_pnl:.2f} P&L")

# 8. KEY INSIGHTS
print("\n" + "=" * 80)
print("8. KEY INSIGHTS & RECOMMENDATIONS")
print("=" * 80)

# Find best performing combinations
best_instrument = df.groupby('instrument').apply(lambda x: (x['is_win'].sum() / len(x) * 100, x['pnl'].sum())).sort_values(ascending=False).head(1)
best_session = df.groupby('session').apply(lambda x: (x['is_win'].sum() / len(x) * 100, x['pnl'].sum())).sort_values(ascending=False).head(1)
best_size = df.groupby('position_size_category').apply(lambda x: (x['is_win'].sum() / len(x) * 100, x['pnl'].sum())).sort_values(ascending=False).head(1)

print("\n✅ STRONGEST PATTERNS:")
print(f"  - Best Instrument: {best_instrument.index[0]}")
print(f"  - Best Session: {best_session.index[0]}")
print(f"  - Best Position Size: {best_size.index[0]}")

# Find worst performing combinations
worst_instrument = df.groupby('instrument').apply(lambda x: (x['is_win'].sum() / len(x) * 100, x['pnl'].sum())).sort_values(ascending=True).head(1)
worst_session = df.groupby('session').apply(lambda x: (x['is_win'].sum() / len(x) * 100, x['pnl'].sum())).sort_values(ascending=True).head(1)

print("\n❌ WEAKEST PATTERNS:")
print(f"  - Worst Instrument: {worst_instrument.index[0]}")
print(f"  - Worst Session: {worst_session.index[0]}")

print("\n" + "=" * 80)

