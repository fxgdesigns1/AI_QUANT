#!/usr/bin/env python3
"""
Place Small Real Orders on OANDA Practice Accounts
Safely demonstrates end-to-end order placement and handling using the live OANDA
practice environment. Places tiny market orders for EUR_USD, XAU_USD, USD_JPY,
then attempts to close with a small profit within a short window; if not
profitable, closes at timeout to minimize risk.
"""

import os
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from typing import Dict, List

from src.core.oanda_client import OandaClient


def _price_precision(instrument: str) -> int:
    """Approximate OANDA display precision per instrument.
    Most FX: 5 dp, JPY pairs: 3 dp, XAU_USD: 2 dp.
    """
    if instrument.endswith('_JPY') or instrument.startswith('JPY_') or instrument == 'USD_JPY':
        return 3
    if instrument == 'XAU_USD':
        return 2
    return 5


def place_and_manage(
    client: OandaClient,
    instrument: str,
    units: int,
    tp_pct: float = 0.0002,
    sl_pct: float = 0.0002,
    max_wait_seconds: int = 60,
    min_profit_usd: float = 0.10,
) -> Dict:
    """Place a small market order with tight SL/TP, then try to close for a small profit.

    Returns a dict with summary info.
    """
    side = 'BUY' if units > 0 else 'SELL'
    prices = client.get_current_prices([instrument])
    price = prices[instrument]
    entry = price.ask if units > 0 else price.bid

    # Compute SL/TP prices
    if units > 0:
        sl = entry * (1 - sl_pct)
        tp = entry * (1 + tp_pct)
    else:
        sl = entry * (1 + sl_pct)
        tp = entry * (1 - tp_pct)

    # Round to OANDA-allowed precision
    dp = _price_precision(instrument)
    sl = float(f"{sl:.{dp}f}")
    tp = float(f"{tp:.{dp}f}")

    order = client.place_market_order(
        instrument=instrument,
        units=units,
        stop_loss=sl,
        take_profit=tp,
    )

    started = datetime.now()
    closed = False
    realized = None

    # Poll unrealized P&L via positions and close when tiny profit available or on timeout
    while (datetime.now() - started).total_seconds() < max_wait_seconds:
        time.sleep(2)
        positions = client.get_positions()
        pos = positions.get(instrument)
        if not pos:
            # Position may have auto-closed by TP/SL
            closed = True
            break
        unrealized = pos.unrealized_pl
        if unrealized >= min_profit_usd:
            client.close_position(instrument)
            closed = True
            break

    if not closed:
        # Timed out; close to minimize exposure
        client.close_position(instrument)

    # Refresh account info for realized P&L snapshot
    acct = client.get_account_info()
    return {
        'instrument': instrument,
        'side': side,
        'units': units,
        'entry_price': entry,
        'tp': tp,
        'sl': sl,
        'closed': True,
        'account_realized_pl': acct.realized_pl,
    }


def main():
    # Load env for OANDA practice credentials
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))

    # Initialize clients for practice accounts
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    if not all([primary_id, gold_id, alpha_id]):
        print('❌ Missing account IDs in oanda_config.env')
        sys.exit(1)

    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    api_key = os.getenv('OANDA_API_KEY')
    if not api_key:
        print('❌ Missing OANDA_API_KEY in oanda_config.env')
        sys.exit(1)

    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    # Verify connections
    for name, client in [('PRIMARY', primary), ('GOLD', gold), ('ALPHA', alpha)]:
        client.get_account_info()
        print(f"✅ Connected: {name}")

    # Define tiny orders per strategy/account
    tasks = [
        (primary, 'EUR_USD', +100),   # buy small size
        (gold, 'XAU_USD', +1),        # buy 1 unit
        (alpha, 'USD_JPY', -100),     # sell small size
    ]

    results: List[Dict] = []
    for client, instrument, units in tasks:
        print(f"\n🚀 Placing order: {instrument} {units} units")
        try:
            res = place_and_manage(
                client=client,
                instrument=instrument,
                units=units,
                tp_pct=0.0002 if instrument != 'XAU_USD' else 0.0001,
                sl_pct=0.0002 if instrument != 'XAU_USD' else 0.0001,
                max_wait_seconds=60,
                min_profit_usd=0.10,
            )
            dp = _price_precision(res['instrument'])
            print(f"✅ Done: {res['instrument']} {res['side']} {res['units']} | TP {res['tp']:.{dp}f} SL {res['sl']:.{dp}f}")
            results.append(res)
        except Exception as e:
            print(f"❌ Error placing/closing order for {instrument}: {e}")

    print("\n📊 Summary:")
    for r in results:
        print(f"  {r['instrument']} {r['side']} {r['units']} closed. Account realized P&L: {r['account_realized_pl']}")


if __name__ == '__main__':
    main()


