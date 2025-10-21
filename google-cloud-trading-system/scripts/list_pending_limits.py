#!/usr/bin/env python3
"""
List pending LIMIT orders across the three OANDA practice accounts.
Outputs instrument, units, price, TIF, and order id per account.
"""

import os
import sys
from typing import List, Dict
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient


def list_pending_limits(name: str, client: OandaClient):
    # Use the client's authenticated request helper for consistency
    url = f"{client.orders_endpoint}?state=PENDING"
    data = client._make_request('GET', url)
    orders = data.get('orders', [])

    print(f"[{name}] LIMIT orders:")
    found = False
    for order in orders:
        if order.get('type') == 'LIMIT':
            found = True
            instrument = order.get('instrument')
            units = order.get('units')
            price = order.get('price')
            tif = order.get('timeInForce')
            oid = order.get('id')
            print(f"  - {instrument} {units} @ {price} (TIF {tif}) id={oid}")
    if not found:
        print("  - none")


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))

    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    if env != 'practice':
        print('❌ Refusing to list orders: environment is not practice (demo).')
        sys.exit(1)

    api_key = os.getenv('OANDA_API_KEY')
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    if not all([api_key, primary_id, gold_id, alpha_id]):
        print('❌ Missing API key or practice account IDs in oanda_config.env')
        sys.exit(1)

    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    list_pending_limits('PRIMARY', primary)
    list_pending_limits('GOLD', gold)
    list_pending_limits('ALPHA', alpha)


if __name__ == '__main__':
    main()


