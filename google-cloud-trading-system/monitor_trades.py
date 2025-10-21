#!/usr/bin/env python3
"""
Trade Monitor Script
Monitors the trading system and alerts if no trades are generated within a specified time period.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
import json

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_for_trades(max_wait_minutes=30):
    """Check if trades have been executed within the specified time period"""
    from src.core.order_manager import get_order_manager
    
    logger.info(f"🔍 Monitoring for trades (max wait: {max_wait_minutes} minutes)")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=max_wait_minutes)
    
    order_manager = get_order_manager()
    initial_trade_count = len(order_manager.get_trade_history())
    
    logger.info(f"📊 Initial trade count: {initial_trade_count}")
    
    while datetime.now() < end_time:
        # Check current trade count
        current_trade_count = len(order_manager.get_trade_history())
        new_trades = current_trade_count - initial_trade_count
        
        if new_trades > 0:
            logger.info(f"✅ {new_trades} new trades detected!")
            return True
        
        # Check if trading is allowed
        trading_allowed, reason = order_manager.is_trading_allowed()
        if not trading_allowed:
            logger.warning(f"⚠️ Trading not allowed: {reason}")
        
        # Sleep for a bit
        logger.info(f"⏳ Waiting for trades... ({int((end_time - datetime.now()).total_seconds())} seconds remaining)")
        time.sleep(60)  # Check every minute
    
    logger.warning(f"❌ No trades detected within {max_wait_minutes} minutes")
    return False

def alert_no_trades():
    """Alert that no trades have been generated"""
    logger.error("🚨 ALERT: No trades generated within the specified time period")
    logger.error("🔧 Consider checking the following:")
    logger.error("   1. Market conditions (low volatility?)")
    logger.error("   2. Strategy parameters (still too strict?)")
    logger.error("   3. Data feed issues (receiving fresh data?)")
    logger.error("   4. Order execution issues (OANDA connection?)")
    
    # You could add additional alerting mechanisms here
    # e.g., send email, SMS, or Telegram notification

def main():
    """Main monitoring function"""
    logger.info("🚀 Starting Trade Monitor")
    
    # Check for trades with a 30-minute timeout
    trades_detected = check_for_trades(max_wait_minutes=30)
    
    if not trades_detected:
        alert_no_trades()
        return False
    
    logger.info("✅ Trading system is active and generating trades")
    return True

if __name__ == '__main__':
    main()
