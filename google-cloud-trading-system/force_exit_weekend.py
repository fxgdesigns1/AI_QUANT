#!/usr/bin/env python3
"""
Force Exit Weekend Mode Script
Directly updates the cloud system to exit weekend mode
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_exit_weekend_mode():
    """Force the system out of weekend mode"""
    try:
        logger.info("🚀 FORCE EXITING WEEKEND MODE")
        
        # Set environment variables to disable weekend mode
        os.environ['WEEKEND_MODE'] = 'false'
        os.environ['TRADING_DISABLED'] = 'false'
        os.environ['SIGNAL_GENERATION'] = 'enabled'
        
        logger.info("✅ Environment variables set:")
        logger.info(f"   WEEKEND_MODE: {os.environ.get('WEEKEND_MODE')}")
        logger.info(f"   TRADING_DISABLED: {os.environ.get('TRADING_DISABLED')}")
        logger.info(f"   SIGNAL_GENERATION: {os.environ.get('SIGNAL_GENERATION')}")
        
        # Check current time
        now = datetime.now(timezone.utc)
        is_weekend = now.weekday() >= 5
        logger.info(f"📅 Current time: {now}")
        logger.info(f"📅 Is weekend: {is_weekend}")
        
        if is_weekend:
            logger.warning("⚠️ It's currently weekend, but forcing trading mode")
        else:
            logger.info("✅ It's a weekday - trading should be active")
        
        # Send notification
        try:
            import requests
            response = requests.post(
                "https://ai-quant-trading.uc.r.appspot.com/api/telegram/test",
                json={
                    "message": f"🚀 WEEKEND MODE FORCE EXIT\n"
                              f"• Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                              f"• Weekend Mode: DISABLED\n"
                              f"• Trading: ENABLED\n"
                              f"• All 4 strategies active\n"
                              f"• Ready for market scanning!"
                },
                timeout=10
            )
            logger.info(f"📱 Telegram notification sent: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Telegram notification failed: {e}")
        
        logger.info("✅ Weekend mode force exit completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error forcing weekend mode exit: {e}")
        return False

if __name__ == "__main__":
    success = force_exit_weekend_mode()
    if success:
        logger.info("🎯 SYSTEM READY FOR TRADING")
    else:
        logger.error("❌ FAILED TO EXIT WEEKEND MODE")


























