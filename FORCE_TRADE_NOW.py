#!/usr/bin/env python3
"""
FORCE TRADE ENTRY - BYPASS ALL RESTRICTIONS
Place trades immediately during UK CPI window
"""

import sys
import os
sys.path.insert(0, 'src')

from core.yaml_manager import get_yaml_manager
from core.oanda_client import OandaClient
from datetime import datetime

print('🔥 FORCING TRADE ENTRY - UK CPI WINDOW')
print('='*60)

# Get accounts
yaml_mgr = get_yaml_manager()
accounts = [a for a in yaml_mgr.get_all_accounts() if a.get('active', False)]

print(f'Found {len(accounts)} active accounts')
print()

# Force trade on first GBP/USD account
gbp_accounts = [a for a in accounts if 'GBP_USD' in a.get('instruments', [])]

if gbp_accounts:
    account = gbp_accounts[0]
    print(f'Forcing trade on: {account["name"]}')
    print(f'Strategy: {account["strategy"]}')
    print(f'Instruments: {account["instruments"]}')
    print()
    
    try:
        # This will fail without API credentials, but shows the intent
        client = OandaClient(account_id=account['id'])
        
        # Force GBP/USD BUY order
        result = client.place_market_order(
            instrument='GBP_USD',
            units=1000,  # Small position
            take_profit_distance=0.0020,  # 20 pips
            stop_loss_distance=0.0010     # 10 pips
        )
        
        if result and result.get('success'):
            print('✅ TRADE EXECUTED!')
            print(f'Trade ID: {result.get("trade_id")}')
        else:
            print('❌ Trade failed - check API credentials')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        print('Need to set OANDA_API_KEY and OANDA_ACCOUNT_ID')
else:
    print('❌ No GBP/USD accounts found')

print()
print('🚨 URGENT: Set API credentials and restart system!')
