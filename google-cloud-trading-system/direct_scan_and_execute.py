#!/usr/bin/env python3
"""Direct market scan and execution bypassing cloud"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
import yaml
with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']

with open('accounts.yaml') as f:
    accounts_data = yaml.safe_load(f)
    first_account = accounts_data['accounts'][0]
    os.environ['OANDA_ACCOUNT_ID'] = first_account['id']

os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"

from src.core.simple_timer_scanner import SimpleTimerScanner
from datetime import datetime

print("="*80)
print(f"DIRECT MARKET SCAN - {datetime.now().strftime('%H:%M:%S')} London Time")
print("="*80)
print()

scanner = SimpleTimerScanner()
print("✅ Scanner initialized")
print()

print("🔍 Running market scan across all accounts...")
result = scanner.run_manual_scan()

if result:
    opps = result.get('opportunities', [])
    trades = result.get('executed_trades', [])
    
    print(f"\n📊 RESULTS:")
    print(f"   Opportunities: {len(opps)}")
    print(f"   Trades executed: {len(trades)}")
    
    if trades:
        print("\n✅ TRADES EXECUTED:")
        for trade in trades:
            print(f"   • {trade.get('instrument')} {trade.get('direction')}")
            print(f"     Units: {trade.get('units')}")
            print(f"     ID: {trade.get('trade_id')}")
    else:
        print("\n⚪ No high-probability setups detected")
        print("   Market conditions not aligned with strategy criteria")
else:
    print("❌ Scan returned no results")

print("\n" + "="*80)
