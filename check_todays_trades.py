#!/usr/bin/env python3
"""
Check today's trading activity - signals generated vs trades executed
"""
import os
import sys
import logging
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, 'google-cloud-trading-system')

logging.basicConfig(level=logging.WARNING)  # Suppress most logs

print("="*80)
print("TODAY'S TRADING ACTIVITY ANALYSIS")
print("="*80)
print(f"Date: {date.today()}\n")

# Check for signals and trades in logs
today_str = date.today().isoformat()
signals_found = []
trades_executed = []
trades_rejected = []
confidence_too_low = []
session_blocks = []
daily_limit_blocks = []

log_files = [
    Path("google-cloud-trading-system/working_server.log"),
    Path("google-cloud-trading-system/main_system.log"),
    Path("google-cloud-trading-system/trading_system.log"),
    Path("google-cloud-trading-system/server.log"),
]

print("📊 Checking log files for activity...")
for log_file in log_files:
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-5000:]  # Last 5000 lines
            
            for line in lines:
                if today_str in line or datetime.now().strftime('%Y-%m-%d') in line:
                    line_upper = line.upper()
                    
                    # Signals generated
                    if 'SIGNAL' in line_upper and ('GENERATED' in line_upper or 'SNIPER' in line_upper):
                        signals_found.append(line.strip())
                    
                    # Trades executed
                    if 'TRADE EXECUTED' in line_upper or 'EXECUTED' in line_upper and 'TRADE' in line_upper:
                        trades_executed.append(line.strip())
                    
                    # Trades rejected
                    if 'REJECTED' in line_upper and 'TRADE' in line_upper:
                        trades_rejected.append(line.strip())
                    
                    # Confidence too low
                    if 'CONFIDENCE' in line_upper and ('TOO LOW' in line_upper or '<' in line or '0.7' in line or '0.8' in line):
                        confidence_too_low.append(line.strip())
                    
                    # Session blocks
                    if 'SESSION' in line_upper and ('OUTSIDE' in line_upper or 'HOURS' in line_upper):
                        session_blocks.append(line.strip())
                    
                    # Daily limit blocks
                    if 'DAILY' in line_upper and ('LIMIT' in line_upper or 'REACHED' in line_upper):
                        daily_limit_blocks.append(line.strip())
        except Exception as e:
            print(f"  ⚠️  Error reading {log_file.name}: {e}")

print(f"\n📈 SIGNALS GENERATED: {len(signals_found)}")
if signals_found:
    print("Recent signals:")
    for sig in signals_found[-5:]:
        print(f"  • {sig[:120]}")

print(f"\n✅ TRADES EXECUTED: {len(trades_executed)}")
if trades_executed:
    print("Executed trades:")
    for trade in trades_executed[-5:]:
        print(f"  • {trade[:120]}")

print(f"\n❌ TRADES REJECTED: {len(trades_rejected)}")
if trades_rejected:
    print("Rejected trades:")
    for reject in trades_rejected[-5:]:
        print(f"  • {reject[:120]}")

print(f"\n⚠️  CONFIDENCE TOO LOW: {len(confidence_too_low)}")
if confidence_too_low:
    print("Low confidence blocks:")
    for conf in confidence_too_low[-5:]:
        print(f"  • {conf[:120]}")

print(f"\n⏰ SESSION BLOCKS: {len(session_blocks)}")
if session_blocks:
    print("Session blocks:")
    for sess in session_blocks[-5:]:
        print(f"  • {sess[:120]}")

print(f"\n🚫 DAILY LIMIT BLOCKS: {len(daily_limit_blocks)}")
if daily_limit_blocks:
    print("Daily limit blocks:")
    for limit in daily_limit_blocks[-5:]:
        print(f"  • {limit[:120]}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Signals Generated: {len(signals_found)}")
print(f"Trades Executed: {len(trades_executed)}")
print(f"Trades Rejected: {len(trades_rejected)}")
print(f"Confidence Blocks: {len(confidence_too_low)}")
print(f"Session Blocks: {len(session_blocks)}")
print(f"Daily Limit Blocks: {len(daily_limit_blocks)}")

if len(trades_executed) == 0:
    print("\n🔍 REASONS WHY NO TRADES WERE EXECUTED:")
    print("  1. Signals generated but confidence too low? " + ("YES" if len(confidence_too_low) > 0 else "NO"))
    print("  2. Outside trading session? " + ("YES" if len(session_blocks) > 0 else "NO"))
    print("  3. Daily limit reached? " + ("YES" if len(daily_limit_blocks) > 0 else "NO"))
    print("  4. Signals rejected by order manager? " + ("YES" if len(trades_rejected) > 0 else "NO"))
    print("  5. No signals generated at all? " + ("YES" if len(signals_found) == 0 else "NO"))

print("="*80)

