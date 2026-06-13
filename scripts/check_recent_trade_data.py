#!/usr/bin/env python3
"""
Check for recent trade data from accounts 001, 002, 003 in the last week.
Checks multiple sources: OANDA transactions, trade ledger, processed data.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'

def check_oanda_transactions():
    """Check OANDA transaction files for accounts 001-003"""
    print("=" * 70)
    print("📊 CHECKING OANDA TRANSACTION FILES")
    print("=" * 70)
    
    accounts = ['001', '002', '003']
    recent_cutoff = datetime.now() - timedelta(days=7)
    
    for acc in accounts:
        file_path = RAW_DIR / f'101-004-30719775-{acc}_transactions.json'
        print(f"\nAccount {acc}:")
        
        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            continue
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            transactions = data.get('transactions', [])
            print(f"  Total transactions: {len(transactions)}")
            
            if not transactions:
                print("  ⚠️  No transactions in file")
                continue
                
            # Find ORDER_FILL transactions (actual trades)
            fills = [t for t in transactions if t.get('type') == 'ORDER_FILL']
            print(f"  ORDER_FILL transactions: {len(fills)}")
            
            # Check for recent ones
            recent_fills = []
            for fill in fills:
                time_str = fill.get('time', '')
                if time_str:
                    try:
                        fill_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        if fill_time.replace(tzinfo=None) > recent_cutoff:
                            recent_fills.append(fill)
                    except:
                        pass
                        
            print(f"  Fills in last 7 days: {len(recent_fills)}")
            
            if fills:
                latest = fills[-1].get('time', 'Unknown')
                print(f"  Latest fill: {latest}")
                
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")

def check_trade_ledger():
    """Check trade_ledger.jsonl"""
    print("\n" + "=" * 70)
    print("📊 CHECKING TRADE LEDGER (VM Execution Logs)")
    print("=" * 70)
    
    ledger_path = DATA_DIR / 'trade_ledger.jsonl'
    if not ledger_path.exists():
        print(f"  ❌ {ledger_path} not found")
        return
        
    trades = []
    with open(ledger_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    trades.append(json.loads(line))
                except:
                    pass
                    
    print(f"  Total trades in ledger: {len(trades)}")
    
    accounts = ['001', '002', '003']
    for acc in accounts:
        acc_trades = [t for t in trades if acc in str(t.get('account_id', ''))]
        print(f"  Account {acc}: {len(acc_trades)} trades")
        
        if acc_trades:
            latest = acc_trades[-1].get('openTime', 'Unknown')
            print(f"    Latest: {latest}")

def check_processed_data():
    """Check processed VM trades"""
    print("\n" + "=" * 70)
    print("📊 CHECKING PROCESSED VM TRADES")
    print("=" * 70)
    
    vm_file = PROCESSED_DIR / 'vm_trades_flat.json'
    if not vm_file.exists():
        print(f"  ❌ {vm_file} not found")
        return
        
    with open(vm_file, 'r') as f:
        data = json.load(f)
        
    trades = data.get('trades', [])
    print(f"  Total processed trades: {len(trades)}")
    
    accounts = ['001', '002', '003']
    for acc in accounts:
        acc_trades = [t for t in trades if t.get('account_suffix') == acc]
        print(f"  Account {acc}: {len(acc_trades)} trades")
        
        if acc_trades:
            latest = acc_trades[-1].get('timestamp', 'Unknown')
            print(f"    Latest: {latest}")

if __name__ == "__main__":
    check_oanda_transactions()
    check_trade_ledger()
    check_processed_data()
    
    print("\n" + "=" * 70)
    print("💡 SUMMARY")
    print("=" * 70)
    print("If no recent data found:")
    print("  1. VM may not be executing trades (check VM status)")
    print("  2. Trade ledger may not be writing (check VM logs)")
    print("  3. OANDA sync may not be running (check local_oanda_trade_pull.py)")
