#!/usr/bin/env python3
"""
Disable Weekend Trading - Immediate Fix
Sets environment variable to disable trading signals during weekends
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_weekend():
    """Check if it's weekend"""
    now = datetime.now(timezone.utc)
    return now.weekday() >= 5  # Saturday=5, Sunday=6

def disable_weekend_trading():
    """Disable trading signals for weekend"""
    try:
        if is_weekend():
            logger.info("📅 WEEKEND DETECTED - Disabling trading signals")
            
            # Set environment variable to disable trading
            os.environ['WEEKEND_MODE'] = 'true'
            os.environ['TRADING_DISABLED'] = 'true'
            os.environ['SIGNAL_GENERATION'] = 'disabled'
            
            logger.info("✅ Weekend trading disabled")
            logger.info("   • WEEKEND_MODE=true")
            logger.info("   • TRADING_DISABLED=true") 
            logger.info("   • SIGNAL_GENERATION=disabled")
            
            return True
        else:
            logger.info("📅 MARKET HOURS - Trading enabled")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error disabling weekend trading: {e}")
        return False

def enable_trading():
    """Enable trading signals"""
    try:
        logger.info("🚀 MARKET HOURS - Enabling trading signals")
        
        # Remove weekend mode environment variables
        os.environ.pop('WEEKEND_MODE', None)
        os.environ.pop('TRADING_DISABLED', None)
        os.environ.pop('SIGNAL_GENERATION', None)
        
        logger.info("✅ Trading enabled")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enabling trading: {e}")
        return False

if __name__ == "__main__":
    if is_weekend():
        disable_weekend_trading()
        print("🛑 WEEKEND TRADING DISABLED")
        print("   • No more trade signals will be sent")
        print("   • System will resume Monday")
        print("   • Cost savings active")
    else:
        enable_trading()
        print("🚀 TRADING ENABLED")
        print("   • Trade signals active")
        print("   • Full system operational")






















