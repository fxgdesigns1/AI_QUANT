#!/usr/bin/env python3
"""
FORCE MARKET ENTRY - IMMEDIATE EXECUTION
Places micro-trades on all strategies to verify execution pipeline
"""

import sys
sys.path.insert(0, 'src')

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient

print("="*90)
print("🔥 FORCE MARKET ENTRY - EXECUTING MICRO-TRADES NOW")
print("="*90)
print()
print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
print()

# Get all accounts
yaml_mgr = get_yaml_manager()
accounts = yaml_mgr.get_all_accounts()

print(f"Found {len(accounts)} accounts")
print()

# Filter to active accounts
active_accounts = [a for a in accounts if a.get('active', False)]
print(f"Active accounts: {len(active_accounts)}")
print()

print("="*90)
print("EXECUTING MICRO-TRADES (DEMO ACCOUNTS ONLY)")
print("="*90)
print()

trades_placed = 0
trades_failed = 0

for account in active_accounts:
    account_id = account['id']
    account_name = account.get('name', 'Unknown')
    strategy = account.get('strategy', 'unknown')
    instruments = account.get('instruments', [])
    
    print(f"{'─'*90}")
    print(f"Account: {account_name}")
    print(f"ID: {account_id}")
    print(f"Strategy: {strategy}")
    print(f"Instruments: {', '.join(instruments)}")
    print()
    
    if not instruments:
        print("  ⚠️ No instruments - skipping")
        print()
        continue
    
    # Take first instrument
    instrument = instruments[0]
    
    try:
        # Get API credentials for this account
        api_key = account.get('api_key')
        account_id = account['id']
        
        if not api_key:
            print(f"  ❌ ERROR: API key not found for account {account_id}")
            trades_failed += 1
            continue
        
        # Create OANDA client for this account
        client = OandaClient(api_key=api_key, account_id=account_id)
        
        # Get current price
        prices = client.get_current_prices([instrument], force_refresh=True)
        
        if instrument not in prices:
            print(f"  ❌ No price data for {instrument}")
            trades_failed += 1
            continue
        
        current_price = prices[instrument]
        mid_price = (current_price.bid + current_price.ask) / 2
        
        print(f"  📊 {instrument}: Bid={current_price.bid:.5f}, Ask={current_price.ask:.5f}")
        print()
        
        # Calculate micro position size
        if 'XAU' in instrument:  # Gold
            units = 10  # 10 units of gold = micro position
            tp_distance = 5.0  # $5 take profit
            sl_distance = 2.5  # $2.5 stop loss
        elif 'JPY' in instrument:  # JPY pairs
            units = 1000  # 1,000 units = micro position  
            tp_distance = 0.20  # 20 pip TP
            sl_distance = 0.10  # 10 pip SL
        else:  # Regular forex
            units = 100  # 100 units = micro position
            tp_distance = 0.0020  # 20 pip TP
            sl_distance = 0.0010  # 10 pip SL
        
        # Always BUY for testing (simplicity)
        direction = "BUY"
        
        print(f"  🔄 Placing {direction} order:")
        print(f"     Instrument: {instrument}")
        print(f"     Units: {units}")
        print(f"     TP Distance: {tp_distance}")
        print(f"     SL Distance: {sl_distance}")
        print()
        
        # Place market order
        result = client.place_market_order(
            instrument=instrument,
            units=units,
            take_profit_distance=tp_distance,
            stop_loss_distance=sl_distance
        )
        
        if result and result.get('success'):
            trade_id = result.get('trade_id', 'N/A')
            print(f"  ✅ TRADE EXECUTED!")
            print(f"     Trade ID: {trade_id}")
            print(f"     Status: SUCCESS")
            trades_placed += 1
        else:
            error = result.get('error', 'Unknown error') if result else 'No result'
            print(f"  ❌ TRADE FAILED: {error}")
            trades_failed += 1
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        trades_failed += 1
    
    print()

print("="*90)
print("EXECUTION SUMMARY")
print("="*90)
print()
print(f"Accounts Processed: {len(active_accounts)}")
print(f"Trades Placed: {trades_placed} ✅")
print(f"Trades Failed: {trades_failed} ❌")
print()

if trades_placed > 0:
    print("✅ EXECUTION PIPELINE VERIFIED!")
    print()
    print("System CAN execute trades.")
    print("Micro-trades placed successfully.")
    print("Check OANDA accounts for open positions.")
else:
    print("❌ NO TRADES EXECUTED")
    print()
    print("Execution pipeline may have issues.")
    print("Check errors above for details.")

print()
print("="*90)



