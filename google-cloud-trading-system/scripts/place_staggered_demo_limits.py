#!/usr/bin/env python3
"""
Place staggered LIMIT orders across practice accounts (demo-only), enforcing:
- ~2% max per-trade risk heuristic
- ~10% portfolio exposure cap across all pending orders

Creates 5 staggered limits per instrument with moderate sizes.
"""

import os
import sys
from math import isfinite
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient


def price_precision(instrument: str) -> int:
    if instrument.endswith('_JPY') or instrument == 'USD_JPY':
        return 3
    if instrument == 'XAU_USD':
        return 2
    return 5


def est_margin_required(instrument: str, units: int, price: float, leverage: float = 30.0) -> float:
    notional = abs(units) * price
    return notional / leverage


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))

    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    if env != 'practice':
        print('❌ Refusing to place orders: environment is not practice (demo).')
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

    # Snapshot balances
    acct_primary = primary.get_account_info()
    acct_gold = gold.get_account_info()
    acct_alpha = alpha.get_account_info()

    # Exposure caps
    total_balance = acct_primary.balance + acct_gold.balance + acct_alpha.balance
    exposure_cap_usd = total_balance * 0.10  # 10%

    # Instruments and base sizes (moderate)
    instruments = [
        (primary, 'EUR_USD', +25000),
        (alpha, 'USD_JPY', +25000),
        (gold, 'XAU_USD', +5),
    ]

    # Create 5 staggered limits per instrument
    stagger_levels = 5
    created = []

    current_exposure = 0.0

    for client, instrument, base_units in instruments:
        prices = client.get_current_prices([instrument])
        p = prices[instrument]
        dp = price_precision(instrument)

        # Use mid price for reference
        mid = (p.bid + p.ask) / 2.0

        for i in range(stagger_levels):
            # Price offsets: place increasingly favorable limits
            if base_units > 0:
                # Buys below market: 0.02% increments
                offset = mid * (1 - 0.0002 * (i + 1))
                limit_price = float(f"{offset:.{dp}f}")
                sl = float(f"{(limit_price * 0.998):.{dp}f}")  # ~0.2% SL
                tp = float(f"{(limit_price * 1.003):.{dp}f}")  # ~0.3% TP
                units = base_units
            else:
                # Sells above market
                offset = mid * (1 + 0.0002 * (i + 1))
                limit_price = float(f"{offset:.{dp}f}")
                sl = float(f"{(limit_price * 1.002):.{dp}f}")
                tp = float(f"{(limit_price * 0.997):.{dp}f}")
                units = base_units

            # Heuristic per-trade risk: keep notional small enough that 0.2% move ≈ 2% of per-account balance
            acct = client.get_account_info()
            # target risk amount ≈ 2% of balance
            target_risk = acct.balance * 0.02
            # risk per trade ≈ abs(units) * limit_price * 0.002
            est_risk = abs(units) * limit_price * 0.002
            if est_risk > target_risk and est_risk > 0:
                scale = target_risk / est_risk
                scaled_units = max(1, int(abs(units) * scale))
                units = scaled_units if base_units > 0 else -scaled_units

            # Check exposure cap roughly via margin estimate
            add_margin = est_margin_required(instrument, units, limit_price)
            if current_exposure + add_margin > exposure_cap_usd:
                print(f"⚠️ Skipping {instrument} level {i+1}: exposure cap would be exceeded")
                continue

            print(f"📝 LIMIT {instrument} {units} @ {limit_price} (SL {sl} TP {tp})")
            try:
                order = client.place_limit_order(
                    instrument=instrument,
                    units=units,
                    price=limit_price,
                    time_in_force='GTC',
                    stop_loss=sl,
                    take_profit=tp,
                )
                created.append((instrument, units, limit_price, order.order_id, order.status))
                current_exposure += add_margin
            except Exception as e:
                print(f"❌ Failed {instrument} level {i+1}: {e}")

    print("\n📊 Created staggered LIMIT orders:")
    for inst, units, px, oid, st in created:
        print(f"  {inst} {units} @ {px} -> {oid} ({st})")


if __name__ == '__main__':
    main()


