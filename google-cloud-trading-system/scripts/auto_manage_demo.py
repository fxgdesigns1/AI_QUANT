#!/usr/bin/env python3
"""
Automated demo account manager:
- Every 5 minutes: applies secure line and TP1 rules
- Sends Telegram notifications for actions taken

Demo only (OANDA_ENVIRONMENT must be 'practice').
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import get_telegram_notifier, TelegramMessage

SECURE_LINE_PCT = 0.0015  # 0.15%
TP1_PCT = 0.0030          # 0.30%
TP2_PCT = 0.0080          # 0.80%
TRAIL_PCT = 0.0030        # 0.30%


def mid_price(client: OandaClient, instrument: str) -> float:
    prices = client.get_current_prices([instrument])
    p = prices[instrument]
    return (p.bid + p.ask) / 2.0


def manage_once(name: str, client: OandaClient, notifier) -> int:
    """Apply management rules once. Returns number of actions taken."""
    actions = 0
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

        # TP2 reached -> close all remaining immediately
        if move_pct >= TP2_PCT:
            if side == 'LONG':
                client.place_market_order(instrument=inst, units=-total_units)
                msg = f"{name} {inst}: TP2 -> closed remaining {total_units} at ~{mpx}"
            else:
                client.place_market_order(instrument=inst, units=+total_units)
                msg = f"{name} {inst}: TP2 -> covered remaining {total_units} at ~{mpx}"
            actions += 1
            notifier.send_message(TelegramMessage(text=f"🏁 {msg}"), message_type="manage_action")

        # TP1 reached -> close 50% and set trailing stop for remaining
        elif move_pct >= TP1_PCT:
            half = max(1, total_units // 2)
            if side == 'LONG':
                client.place_market_order(instrument=inst, units=-half)
                trail_stop = max(entry, mpx * (1 - TRAIL_PCT))
                client.place_stop_order(instrument=inst, units=-(total_units - half), price=trail_stop)
                msg = f"{name} {inst}: TP1 -> closed {half}, TRAIL stop {total_units - half} @ {trail_stop}"
            else:
                client.place_market_order(instrument=inst, units=+half)
                trail_stop = min(entry, mpx * (1 + TRAIL_PCT))
                client.place_stop_order(instrument=inst, units=+(total_units - half), price=trail_stop)
                msg = f"{name} {inst}: TP1 -> covered {half}, TRAIL stop {total_units - half} @ {trail_stop}"
            actions += 1
            notifier.send_message(TelegramMessage(text=f"✅ {msg}"), message_type="manage_action")

        # Secure line -> move SL to BE if not already actioned
        elif move_pct >= SECURE_LINE_PCT:
            if side == 'LONG':
                client.place_stop_order(instrument=inst, units=-total_units, price=entry)
            else:
                client.place_stop_order(instrument=inst, units=+total_units, price=entry)
            msg = f"{name} {inst}: Secure -> BE stop set for {total_units} @ {entry}"
            actions += 1
            notifier.send_message(TelegramMessage(text=f"🟡 {msg}"), message_type="manage_action")

    return actions


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    api_key = os.getenv('OANDA_API_KEY')
    primary_id = os.getenv('PRIMARY_ACCOUNT')
    gold_id = os.getenv('GOLD_SCALP_ACCOUNT')
    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')

    if env != 'practice':
        print('❌ Refusing to manage: environment is not practice (demo).')
        sys.exit(1)

    notifier = get_telegram_notifier()
    if not notifier.enabled:
        print('⚠️ Telegram notifier disabled (missing TELEGRAM_TOKEN/TELEGRAM_CHAT_ID). Continuing without alerts.')

    primary = OandaClient(api_key=api_key, account_id=primary_id, environment=env)
    gold = OandaClient(api_key=api_key, account_id=gold_id, environment=env)
    alpha = OandaClient(api_key=api_key, account_id=alpha_id, environment=env)

    print('✅ Auto manager started. Running every 5 minutes (demo only).')
    while True:
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            total_actions = 0
            total_actions += manage_once('PRIMARY', primary, notifier)
            total_actions += manage_once('GOLD', gold, notifier)
            total_actions += manage_once('ALPHA', alpha, notifier)
            if total_actions > 0 and notifier.enabled:
                notifier.send_message(TelegramMessage(text=f"📊 Auto-manage cycle {ts}: {total_actions} action(s)."), message_type="manage_cycle")
        except Exception as e:
            if notifier.enabled:
                notifier.send_message(TelegramMessage(text=f"⚠️ Auto-manage error: {e}"), message_type="manage_error")
            print(f"Auto-manage error: {e}")

        time.sleep(300)


if __name__ == '__main__':
    main()


