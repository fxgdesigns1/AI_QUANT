#!/usr/bin/env python3
"""
Check Current Market Status - What Should System Have Entered?
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src'))

from core.yaml_manager import get_yaml_manager
from core.oanda_client import OandaClient
from datetime import datetime
import pytz

print('='*90)
print('🔍 LIVE MARKET CHECK - What Should System Have Entered?')
print('='*90)
london_tz = pytz.timezone('Europe/London')
london_time = datetime.now(london_tz)
print(f'Time: {london_time.strftime("%H:%M:%S %Z")} on {london_time.strftime("%A, %B %d, %Y")}')
print()

# Get all active accounts
yaml_mgr = get_yaml_manager()
accounts = [a for a in yaml_mgr.get_all_accounts() if a.get('active', False)]

print(f'📊 Checking {len(accounts)} active accounts...')
print()

# Check first account for market data
account = accounts[0]
client = OandaClient(account_id=account['id'])

# Get account info and positions
try:
    account_info = client.get_account_info()
    
    print(f'Account: {account["name"]}')
    print(f'Balance: {account_info.balance:,.2f} {account_info.currency}')
    print(f'Open Positions: {account_info.open_position_count}')
    print(f'Open Trades: {account_info.open_trade_count}')
    print(f'Pending Orders: {account_info.pending_order_count}')
    print()
except Exception as e:
    print(f'Error getting account info: {e}')
    print()

# Get current prices for all instruments
all_instruments = set()
for acc in accounts:
    all_instruments.update(acc.get('instruments', []))

print('📈 CURRENT MARKET PRICES:')
print('-'*90)
try:
    prices = client.get_current_prices(list(all_instruments), force_refresh=True)
    for inst in sorted(all_instruments):
        if inst in prices:
            p = prices[inst]
            age = (datetime.now(pytz.UTC) - p.timestamp).total_seconds()
            print(f'{inst:12} Bid: {p.bid:>10.5f}  Ask: {p.ask:>10.5f}  Spread: {p.spread:.5f}  Age: {age:.1f}s')
except Exception as e:
    print(f'Error getting prices: {e}')
print()

# Check all accounts for positions
print('🎯 OPEN POSITIONS ACROSS ALL ACCOUNTS:')
print('-'*90)
total_positions = 0
total_pl = 0.0
for acc in accounts:
    try:
        client = OandaClient(account_id=acc['id'])
        positions = client.get_open_positions()
        if positions:
            print(f"\n{acc['name']} ({acc['id'][-3:]})")
            for pos in positions:
                total_positions += 1
                units = pos.long_units + pos.short_units
                total_pl += pos.unrealized_pl
                print(f"  {pos.instrument}: Units={units:>8}  P/L={pos.unrealized_pl:>8.2f} {account_info.currency}")
        else:
            print(f"{acc['name']}: No positions")
    except Exception as e:
        print(f"{acc['name']}: Error - {e}")

print()
print(f'Total Open Positions: {total_positions}')
print(f'Total Unrealized P/L: {total_pl:,.2f}')
print()

# Check for pending orders
print('📋 PENDING ORDERS ACROSS ALL ACCOUNTS:')
print('-'*90)
total_pending = 0
for acc in accounts:
    try:
        client = OandaClient(account_id=acc['id'])
        orders = client.get_pending_orders()
        if orders:
            print(f"\n{acc['name']} ({acc['id'][-3:]})")
            for order in orders:
                total_pending += 1
                print(f"  {order.type} {order.instrument}: {order.units} units @ {order.price} (ID: {order.order_id})")
        else:
            print(f"{acc['name']}: No pending orders")
    except Exception as e:
        print(f"{acc['name']}: Error - {e}")

print()
print(f'Total Pending Orders: {total_pending}')
print()
print('='*90)

