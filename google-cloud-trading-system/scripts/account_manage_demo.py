#!/usr/bin/env python3
"""
Account management helper (demo): prints recommendations to close or take partials
based on simple secure/profit lines across the three practice accounts.

Rules (per position):
- Secure line: if move in favor ≥ 0.15%, recommend moving SL to breakeven.
- TP1: if move in favor ≥ 0.30%, recommend taking 50% off.
- Cut loss: if move against ≤ -0.30%, recommend closing the position.

This script only prints recommendations; it does not execute changes.
"""

import os
import sys
from typing import Dict
from dotenv import load_dotenv
from datetime import datetime

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient, OandaPosition


SECURE_LINE_PCT = 0.0015  # 0.15%
TP1_PCT = 0.0030          # 0.30%
CUT_LOSS_PCT = -0.0030     # -0.30%


def current_price_for(instrument: str, prices: Dict) -> float:
    p = prices[instrument]
    return (p.bid + p.ask) / 2.0


def pct_move_long(entry: float, current: float) -> float:
    if not entry:
        return 0.0
    return (current - entry) / entry


def pct_move_short(entry: float, current: float) -> float:
    if not entry:
        return 0.0
    return (entry - current) / entry


def summarize_account(name: str, client: OandaClient):
    acct = client.get_account_info()
    positions = client.get_positions()
    open_pos = {k: v for k, v in positions.items() if v.long_units != 0 or v.short_units != 0}

    if not open_pos:
        print(f"\n{name}: No open positions.")
        return

    prices = client.get_current_prices(list(open_pos.keys()))

    print(f"\n{name} | Balance {acct.balance} {acct.currency} | Open {len(open_pos)}")
    for inst, pos in open_pos.items():
        mid = current_price_for(inst, prices)
        if pos.long_units > 0:
            entry = pos.long_avg_price or mid
            pct = pct_move_long(entry, mid)
            side = 'LONG'
            units = pos.long_units
        else:
            entry = pos.short_avg_price or mid
            pct = pct_move_short(entry, mid)
            side = 'SHORT'
            units = pos.short_units

        action = 'HOLD'
        detail = ''
        if pct >= TP1_PCT:
            action = 'TAKE_PARTIAL_50'
            detail = 'TP1 hit (~0.3%), consider closing 50%.'
        elif pct >= SECURE_LINE_PCT:
            action = 'MOVE_SL_TO_BE'
            detail = 'Secure line hit (~0.15%), move stop to breakeven.'
        elif pct <= CUT_LOSS_PCT:
            action = 'CLOSE_FULL'
            detail = 'Drawdown beyond -0.3%, consider closing.'

        print(f"  - {inst} {side} {units} | entry {entry} -> now {mid} | move {pct*100:.2f}% | UPL {pos.unrealized_pl} | {action} {detail}")


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    api_key = os.getenv('OANDA_API_KEY')
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"📋 Account Management Recommendations @ {timestamp}")
    summarize_account('PRIMARY', primary)
    summarize_account('GOLD', gold)
    summarize_account('ALPHA', alpha)


if __name__ == '__main__':
    main()


