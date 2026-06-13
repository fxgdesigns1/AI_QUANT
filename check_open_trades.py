#!/usr/bin/env python3
"""
Quick script to check open trades across all accounts
"""

import os
import sys
import requests
from pathlib import Path

# Load environment
env_file = Path('/etc/ai-quant/.env')
if not env_file.exists():
    env_file = Path('.env')
    
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

api_key = os.getenv('OANDA_API_KEY', '').strip()
base_url = os.getenv('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com').strip()
account_id_prefix = '101-004-30719775-'

if not api_key:
    print('ERROR: OANDA_API_KEY not found')
    sys.exit(1)

headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

# Check allocated lanes only (legacy 001-006 + active 010-011).
# Do not invent 007-009 or assume they exist.
all_positions = []
total_pl = 0.0

print("=" * 80)
print("OPEN TRADES CHECK")
print("=" * 80)
print()

for suffix in ['001', '002', '003', '004', '005', '006', '010', '011']:
    account_id = account_id_prefix + suffix
    url = f'{base_url}/v3/accounts/{account_id}/openPositions'
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            positions = data.get('positions', [])
            for pos in positions:
                long_units = float(pos.get('long', {}).get('units', 0))
                short_units = float(pos.get('short', {}).get('units', 0))
                if long_units != 0 or short_units != 0:
                    instrument = pos.get('instrument', 'UNKNOWN')
                    side = 'LONG' if long_units > 0 else 'SHORT'
                    units = long_units if long_units > 0 else abs(short_units)
                    avg_price = float(pos.get('long', {}).get('averagePrice', 0) or pos.get('short', {}).get('averagePrice', 0))
                    unrealized_pl = float(pos.get('long', {}).get('unrealizedPL', 0) or pos.get('short', {}).get('unrealizedPL', 0))
                    total_pl += unrealized_pl
                    
                    all_positions.append({
                        'account': suffix,
                        'instrument': instrument,
                        'side': side,
                        'units': units,
                        'price': avg_price,
                        'pl': unrealized_pl
                    })
        elif r.status_code == 404:
            # Account doesn't exist, skip
            pass
    except Exception as e:
        print(f'Error checking account {suffix}: {e}', file=sys.stderr)

if all_positions:
    print(f'Total Open Positions: {len(all_positions)}')
    print(f'Total Unrealized P&L: ${total_pl:,.2f}')
    print()
    print('Positions by Account:')
    print('-' * 80)
    
    # Group by account
    by_account = {}
    for pos in all_positions:
        acc = pos['account']
        if acc not in by_account:
            by_account[acc] = []
        by_account[acc].append(pos)
    
    for acc in sorted(by_account.keys()):
        positions = by_account[acc]
        acc_pl = sum(p['pl'] for p in positions)
        print(f'\nAccount {acc}: {len(positions)} position(s) | P&L: ${acc_pl:,.2f}')
        for pos in positions:
            print(f'  - {pos["instrument"]} {pos["side"]} {pos["units"]:,.0f} units @ {pos["price"]:.5f} | P&L: ${pos["pl"]:,.2f}')
else:
    print('No open positions across all accounts')
    print()
    print('Note: Based on earlier verification, accounts were at daily limit (3 trades).')
    print('Daily limit has been raised to 10, so new trades may execute on next signal.')

print()
print("=" * 80)
