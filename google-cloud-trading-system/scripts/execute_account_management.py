#!/usr/bin/env python3
"""
Execute account management actions in practice (demo):
- Close 50% of positions meeting TP1 condition
- Move stop to breakeven for remaining size on those positions

Only operates on the three practice accounts.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from typing import Dict

from src.core.oanda_client import OandaClient

SECURE_LINE_PCT = 0.0015  # 0.15%
TP1_PCT = 0.0030          # 0.30%


def mid_price(client: OandaClient, instrument: str) -> float:
    prices = client.get_current_prices([instrument])
    p = prices[instrument]
    return (p.bid + p.ask) / 2.0


def maybe_partial_and_breakeven(name: str, client: OandaClient):
    acct = client.get_account_info()
    positions = client.get_positions()
    open_pos = {k: v for k, v in positions.items() if v.long_units != 0 or v.short_units != 0}

    for inst, pos in open_pos.items():
        mpx = mid_price(client, inst)
        if pos.long_units > 0:
            entry = pos.long_avg_price or mpx
            move_pct = (mpx - entry) / entry
            total_units = pos.long_units
            side = 'LONG'
        else:
            entry = pos.short_avg_price or mpx
            move_pct = (entry - mpx) / entry
            total_units = abs(pos.short_units)
            side = 'SHORT'

        # TP1 reached -> close 50%
        if move_pct >= TP1_PCT:
            half = max(1, total_units // 2)
            if side == 'LONG':
                # Close half long => sell market
                client.place_market_order(instrument=inst, units=-half)
                # Set breakeven stop for remaining: sell stop at entry
                client.place_stop_order(instrument=inst, units=-(total_units - half), price=entry)
                print(f"✅ {name} {inst}: closed {half} (50%), set BE stop for {total_units - half} @ {entry}")
            else:
                # Close half short => buy market
                client.place_market_order(instrument=inst, units=+half)
                # Set breakeven stop for remaining: buy stop at entry
                client.place_stop_order(instrument=inst, units=+(total_units - half), price=entry)
                print(f"✅ {name} {inst}: covered {half} (50%), set BE stop for {total_units - half} @ {entry}")
        elif move_pct >= SECURE_LINE_PCT:
            # Only move SL to breakeven (no partial)
            if side == 'LONG':
                client.place_stop_order(instrument=inst, units=-total_units, price=entry)
                print(f"✅ {name} {inst}: set BE stop for {total_units} @ {entry}")
            else:
                client.place_stop_order(instrument=inst, units=+total_units, price=entry)
                print(f"✅ {name} {inst}: set BE stop for {total_units} @ {entry}")


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    api_key = os.getenv('OANDA_API_KEY')
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    if env != 'practice':
        print('❌ Refusing to manage positions: environment is not practice (demo).')
        sys.exit(1)

    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    maybe_partial_and_breakeven('PRIMARY', primary)
    maybe_partial_and_breakeven('GOLD', gold)
    maybe_partial_and_breakeven('ALPHA', alpha)


if __name__ == '__main__':
    main()
