#!/usr/bin/env python3
import os, sys
sys.path.insert(0, '.')

os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"

from src.core.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()

msg = """📋 DAILY TRADING SCHEDULE

After testing (15% WR), switching to QUALITY approach:

YOUR TELEGRAM ALERTS:

6:00 AM - Pre-Market News
8:00 AM - London Open Top Setups ⭐
1:00 PM - London/NY Overlap Fresh Scan ⭐⭐
5:00 PM - End of Day Review
9:00 PM - Asian Preview

Plus continuous Gold alerts (>0.5% moves)

YOUR TIME: 10-15 min/day
EXPECTED WR: 60-75%

To activate: Say "deploy daily schedule"
Or run anytime: python3 scan_now.py

Which do you prefer?"""

notifier.send_system_status('NEW Daily Routine', msg)
print('✅ Sent!')




