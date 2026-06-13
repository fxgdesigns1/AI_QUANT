#!/usr/bin/env python3
"""
Check What Specific Opportunities Each Strategy Sees
Parses logs to extract actual signal generation details
"""

import sys
import re
from collections import defaultdict
from datetime import datetime

log_path = "/tmp/runner.out"

print("=== STRATEGY OPPORTUNITIES ANALYSIS ===\n")

try:
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    # Get last 200 lines
    recent_lines = lines[-200:] if len(lines) > 200 else lines
    
    # Parse STRAT_EVIDENCE lines
    opportunities = defaultdict(list)
    
    for line in recent_lines:
        if "STRAT_EVIDENCE" in line:
            # Extract: account=001 strategy=momentum instrument=EUR_USD price_mid=1.08510 decision=BUY
            account_match = re.search(r'account=(\d{3})', line)
            strategy_match = re.search(r'strategy=([^\s]+)', line)
            instrument_match = re.search(r'instrument=([^\s]+)', line)
            price_match = re.search(r'price_mid=([0-9.]+)', line)
            decision_match = re.search(r'decision=([A-Z]+)', line)
            signals_match = re.search(r'signals_generated=(\d+)', line)
            
            if account_match and strategy_match and instrument_match:
                account = account_match.group(1)
                strategy = strategy_match.group(1)
                instrument = instrument_match.group(1)
                price = price_match.group(1) if price_match else "N/A"
                decision = decision_match.group(1) if decision_match else "N/A"
                signals = signals_match.group(1) if signals_match else "0"
                
                key = f"{account}:{strategy}"
                opportunities[key].append({
                    'account': account,
                    'strategy': strategy,
                    'instrument': instrument,
                    'price': price,
                    'decision': decision,
                    'signals': signals
                })
    
    # Also check for "Generated BUY signal" lines
    signal_details = defaultdict(list)
    for line in recent_lines:
        if "Generated BUY signal" in line or "Generated SELL signal" in line:
            # Extract: XAU_USD @ 2650.50000 (confidence: 0.55)
            instrument_match = re.search(r'([A-Z_]+)\s+@\s+([0-9.]+)', line)
            confidence_match = re.search(r'confidence:\s+([0-9.]+)', line)
            
            if instrument_match:
                # Find which account/strategy this belongs to (look back in recent lines)
                for prev_line in reversed(recent_lines[:recent_lines.index(line)+1]):
                    if "STRAT_EVIDENCE" in prev_line and "account=" in prev_line:
                        account_match = re.search(r'account=(\d{3})', prev_line)
                        strategy_match = re.search(r'strategy=([^\s]+)', prev_line)
                        if account_match and strategy_match:
                            key = f"{account_match.group(1)}:{strategy_match.group(1)}"
                            signal_details[key].append({
                                'instrument': instrument_match.group(1),
                                'price': instrument_match.group(2),
                                'confidence': confidence_match.group(1) if confidence_match else "N/A"
                            })
                            break
    
    # Print summary
    print("OPPORTUNITIES BY STRATEGY:\n")
    
    for key in sorted(opportunities.keys()):
        account, strategy = key.split(':')
        opps = opportunities[key]
        
        # Count unique instruments
        instruments = set(o['instrument'] for o in opps)
        decisions = set(o['decision'] for o in opps)
        total_signals = sum(int(o['signals']) for o in opps)
        
        print(f"Account {account} ({strategy}):")
        print(f"  Instruments Seen: {', '.join(sorted(instruments))}")
        print(f"  Decisions: {', '.join(decisions)}")
        print(f"  Total Signals (last 200 lines): {total_signals}")
        
        # Latest signal details
        if key in signal_details and signal_details[key]:
            latest = signal_details[key][-1]
            print(f"  Latest Signal: {latest['instrument']} @ {latest['price']} (confidence: {latest['confidence']})")
        
        # Sample prices
        if opps:
            latest_opp = opps[-1]
            print(f"  Latest Price: {latest_opp['price']} ({latest_opp['instrument']})")
        
        print()
    
    print("=" * 60)
    print("\nSUMMARY:")
    print(f"Total strategies analyzed: {len(opportunities)}")
    print(f"Total signals found: {sum(len(opps) for opps in opportunities.values())}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
