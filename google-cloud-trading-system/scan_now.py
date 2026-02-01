#!/usr/bin/env python3
"""
ON-DEMAND MARKET SCANNER
Run this ANYTIME to get current opportunities sent to Telegram
Usage: python3 scan_now.py
"""

import os
import sys
from datetime import datetime
import yaml

sys.path.insert(0, '.')

# Load credentials
with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"

from morning_scanner import scan_for_opportunities, send_opportunities_to_telegram

if __name__ == '__main__':
    print("\n🔍 SCANNING MARKET NOW...\n")
    opportunities = scan_for_opportunities()
    
    if opportunities:
        print(f"\n✅ Found {len(opportunities)} quality setups!")
        print("📱 Sending to Telegram...")
        send_opportunities_to_telegram(opportunities)
    else:
        print("\n⏸️ No quality setups right now")
        send_opportunities_to_telegram([])
    
    print("\n✅ Done!")




