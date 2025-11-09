#!/usr/bin/env python3
"""
Check why strategies are not entering trades
"""

import sys
import os
sys.path.insert(0, 'src')

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient

# Set environment variables
os.environ['OANDA_API_KEY'] = '${OANDA_API_KEY}'
os.environ['OANDA_ENVIRONMENT'] = 'practice'

def main():
    print('🚨 CRITICAL ANALYSIS: WHY NO TRADES?')
    print('='*80)

    # Get all accounts
    yaml_mgr = get_yaml_manager()
    accounts = yaml_mgr.get_all_accounts()

    print(f'Found {len(accounts)} accounts to analyze')
    print()

    for i, account in enumerate(accounts, 1):
        account_id = account.get('id')
        account_name = account.get('name', 'Unknown')
        strategy = account.get('strategy', 'unknown')
        active = account.get('active', False)
        
        print(f'{i:2d}. {account_name} ({account_id})')
        print(f'    Strategy: {strategy}')
        print(f'    Active: {active}')
        
        if not active:
            print(f'    ❌ INACTIVE - Not running')
            print()
            continue
        
        try:
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            trades = client.get_open_trades()
            positions = client.get_positions()
            
            balance = account_info.balance
            print(f'    💰 Balance: ${balance:,.2f}')
            print(f'    📊 Open trades: {len(trades)}')
            print(f'    📈 Positions: {len(positions)}')
            
            if len(trades) == 0 and len(positions) == 0:
                print(f'    ⚠️  NO ACTIVE TRADES - WHY?')
                print(f'    🔍 Checking if strategy is running...')
                
                try:
                    prices = client.get_current_prices(['EUR_USD', 'GBP_USD', 'XAU_USD'], force_refresh=True)
                    eur_price = prices['EUR_USD'].bid
                    print(f'    ✅ Can get prices: EUR/USD {eur_price:.5f}')
                except Exception as e:
                    print(f'    ❌ Cannot get prices: {e}')
            
            print()
            
        except Exception as e:
            print(f'    ❌ ERROR: {e}')
            print()

if __name__ == "__main__":
    main()

