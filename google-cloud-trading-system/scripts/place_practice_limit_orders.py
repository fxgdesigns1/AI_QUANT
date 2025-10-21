#!/usr/bin/env python3
"""
Place LIMIT Orders on OANDA Practice Accounts (Demo Only)
Creates small limit orders with tight SL/TP at slightly favorable prices
to ensure pending entries exist today in demo accounts.
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from typing import Dict, List, Tuple

from src.core.oanda_client import OandaClient


def price_precision(instrument: str) -> int:
    if instrument.endswith('_JPY') or instrument == 'USD_JPY':
        return 3
    if instrument == 'XAU_USD':
        return 2
    return 5


def main():
    # Load env
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))

    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    if env != 'practice':
        print('❌ Refusing to place limit orders: environment is not practice (demo).')
        sys.exit(1)

    api_key = os.getenv('OANDA_API_KEY')
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    if not all([api_key, primary_id, gold_id, alpha_id]):
        print('❌ Missing API key or practice account IDs in oanda_config.env')
        sys.exit(1)

    # Initialize clients
    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    # Verify connections
    for name, client in [('PRIMARY', primary), ('GOLD', gold), ('ALPHA', alpha)]:
        acct = client.get_account_info()
        print(f"✅ Connected {name} - Balance {acct.balance} {acct.currency}")

    # Instruments and sizes
    tasks: List[Tuple[OandaClient, str, int]] = [
        (primary, 'EUR_USD', +5000),
        (gold, 'XAU_USD', +2),
        (alpha, 'USD_JPY', -5000),
    ]

    created: List[Dict] = []

    for client, instrument, units in tasks:
        prices = client.get_current_prices([instrument])
        p = prices[instrument]
        dp = price_precision(instrument)

        # Favorable limit: for buys, a few ticks below bid; for sells, above ask
        if units > 0:
            limit_price = float(f"{(p.bid - p.spread * 0.5):.{dp}f}")
            sl = float(f"{(p.ask * 0.998):.{dp}f}")  # ~0.2% SL
            tp = float(f"{(p.ask * 1.003):.{dp}f}")  # ~0.3% TP
        else:
            limit_price = float(f"{(p.ask + p.spread * 0.5):.{dp}f}")
            sl = float(f"{(p.bid * 1.002):.{dp}f}")
            tp = float(f"{(p.bid * 0.997):.{dp}f}")

        print(f"\n📝 Creating LIMIT {instrument} {units} @ {limit_price} (SL {sl} TP {tp})")

        try:
            order = client.place_limit_order(
                instrument=instrument,
                units=units,
                price=limit_price,
                time_in_force='GTC',
                stop_loss=sl,
                take_profit=tp,
            )
            print(f"✅ Created pending order {order.order_id} for {instrument}")
            created.append({
                'instrument': instrument,
                'units': units,
                'price': limit_price,
                'order_id': order.order_id,
                'status': order.status,
            })
        except Exception as e:
            print(f"❌ Failed to create limit order for {instrument}: {e}")

    print("\n📊 Created LIMIT orders:")
    for c in created:
        print(f"  {c['instrument']} {c['units']} @ {c['price']} -> {c['order_id']} ({c['status']})")


if __name__ == '__main__':
    main()


