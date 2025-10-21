#!/usr/bin/env python3
"""
CONTINUOUS AGGRESSIVE TRADER - Runs 24/7, catches EVERY move
No cron dependency - pure background execution
"""
import os
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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

from src.core.aggressive_auto_trader import get_aggressive_auto_trader

def run_continuous():
    """Run aggressive scanner continuously"""
    logger.info("="*80)
    logger.info("🚀 CONTINUOUS AGGRESSIVE TRADER STARTING")
    logger.info("Scan interval: 2 minutes")
    logger.info("Mode: FULL AUTO-EXECUTION")
    logger.info("="*80)
    
    trader = get_aggressive_auto_trader()
    scan_count = 0
    
    while True:
        try:
            scan_count += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"{'='*80}")
            
            trades = trader.scan_and_execute()
            
            logger.info(f"✅ Scan #{scan_count} complete: {trades} trades executed")
            logger.info(f"⏰ Next scan in 2 minutes...")
            
            # Wait 2 minutes
            time.sleep(120)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping continuous trader...")
            break
        except Exception as e:
            logger.error(f"❌ Error in continuous loop: {e}")
            logger.info("⏰ Retrying in 2 minutes...")
            time.sleep(120)

if __name__ == '__main__':
    run_continuous()
