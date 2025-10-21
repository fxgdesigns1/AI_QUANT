#!/usr/bin/env python3
"""
Monitor OANDA Practice Positions
Polls all three practice accounts every 15 seconds, printing positions,
unrealized P&L, and basic TP/SL status until interrupted.
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Ensure project src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient


def summarize_positions(name: str, client: OandaClient):
    try:
        acct = client.get_account_info()
        positions = client.get_positions()
        open_pos = {k: v for k, v in positions.items() if v.long_units != 0 or v.short_units != 0}
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {name} | Balance: {acct.balance} {acct.currency} | Open: {len(open_pos)}")
        for inst, p in open_pos.items():
            side = 'LONG' if p.long_units > 0 else ('SHORT' if p.short_units < 0 else 'FLAT')
            units = p.long_units if p.long_units > 0 else p.short_units
            print(f"  - {inst}: {side} {units} | UPL: {p.unrealized_pl} | LongAvg: {p.long_avg_price} ShortAvg: {p.short_avg_price}")
    except Exception as e:
        print(f"❌ {name} monitor error: {e}")


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

    print("✅ Monitor started. Polling every 15s. Press Ctrl+C to stop.")
    try:
        while True:
            summarize_positions('PRIMARY', primary)
            summarize_positions('GOLD', gold)
            summarize_positions('ALPHA', alpha)
            time.sleep(15)
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped by user")


if __name__ == '__main__':
    main()


