#!/usr/bin/env python3
import os
import time
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import get_scanner
from src.core.dynamic_account_manager import get_dynamic_account_manager
from src.core.telegram_notifier import get_telegram_notifier


def format_account_summary(manager):
    lines = []
    for acc_id, cfg in manager.account_configs.items():
        if not cfg.active:
            continue
        client = manager.accounts.get(acc_id)
        try:
            open_trades = client.get_open_trades()
            lines.append(f"{cfg.display_name} ({acc_id[-3:]}): open_trades={len(open_trades)}")
        except Exception as e:
            lines.append(f"{cfg.display_name} ({acc_id[-3:]}): error={str(e)[:60]}")
    return "\n".join(lines)


def main():
    scanner = get_scanner()
    manager = get_dynamic_account_manager()
    notifier = None
    try:
        notifier = get_telegram_notifier()
    except Exception:
        notifier = None

    last_signal_count = 0

    print("[LIVE] Watcher started - streaming updates every 60s for all traded pairs")
    while True:
        try:
            # Run one scan (signals+entries handled internally by scanner)
            scanner._run_scan()

            # Summarize accounts and open trades
            summary = format_account_summary(manager)
            ts = datetime.now().strftime('%H:%M:%S')
            msg = f"\n[LIVE {ts}] Accounts status:\n{summary}"
            print(msg, flush=True)

            # Optionally mirror to Telegram if available
            if notifier:
                try:
                    notifier.send_message(f"📡 Live update {ts}\n" + summary, 'system_status')
                except Exception:
                    pass

        except KeyboardInterrupt:
            print("[LIVE] Watcher stopped by user")
            break
        except Exception as e:
            print(f"[LIVE] Error: {e}")

        time.sleep(60)


if __name__ == "__main__":
    main()







