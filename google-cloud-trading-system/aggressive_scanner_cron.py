#!/usr/bin/env python3
"""
Aggressive Scanner - Runs every 2 minutes, executes ALL signals
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load credentials
import yaml
with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']

with open('accounts.yaml') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']

os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"

from src.core.aggressive_auto_trader import get_aggressive_auto_trader

def aggressive_scan():
    """Run aggressive scan and execute"""
    logger.info("="*80)
    logger.info("🚀 AGGRESSIVE AUTO-SCAN STARTING")
    logger.info("="*80)
    
    trader = get_aggressive_auto_trader()
    trades = trader.scan_and_execute()
    
    logger.info(f"✅ Scan complete - {trades} trades executed")
    
    return f"Executed {trades} trades"

if __name__ == '__main__':
    aggressive_scan()
