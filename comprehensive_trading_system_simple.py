#!/usr/bin/env python3
"""
COMPREHENSIVE TRADING SYSTEM - SIMPLE FALLBACK
Uses AI trading system as comprehensive system when full Google Cloud system unavailable
"""
import os
import sys
import time
import logging
from datetime import datetime

# Set up environment
os.environ['OANDA_API_KEY'] = os.getenv('OANDA_API_KEY', "REMOVED_SECRET")
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Import AI trading system as comprehensive system
sys.path.insert(0, '/workspace')
from ai_trading_system import AITradingSystem

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTradingSystemSimple:
    """Simple comprehensive system using AI trading system"""
    def __init__(self):
        self.ai_system = AITradingSystem()
        self.is_running = False
        self.scan_count = 0
        
        logger.info(f"🎯 COMPREHENSIVE SYSTEM (Simple) initialized")
        logger.info(f"📊 Using AI Trading System as comprehensive system")
    
    def comprehensive_scan_and_execute(self):
        """Comprehensive scan - runs AI trading cycle"""
        self.scan_count += 1
        logger.info(f"🎯 COMPREHENSIVE SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Run AI trading cycle
            self.ai_system.run_trading_cycle()
            logger.info(f"🎯 COMPREHENSIVE SCAN #{self.scan_count} COMPLETE")
            return 1
        except Exception as e:
            logger.error(f"❌ Comprehensive scan error: {e}")
            return 0
    
    def start_comprehensive_scanning(self):
        """Start comprehensive scanning - EVERY 5 MINUTES"""
        self.is_running = True
        logger.info("🎯 STARTING COMPREHENSIVE SCANNING - EVERY 5 MINUTES...")
        
        while self.is_running:
            try:
                executed = self.comprehensive_scan_and_execute()
                logger.info(f"🎯 Next comprehensive scan in 5 minutes...")
                time.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                logger.info("🛑 Comprehensive system stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Comprehensive system error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop scanning"""
        self.is_running = False
        logger.info("🛑 Comprehensive system stopped")

def main():
    """Main comprehensive system loop"""
    logger.info("🎯 STARTING COMPREHENSIVE TRADING SYSTEM (Simple)")
    
    system = ComprehensiveTradingSystemSimple()
    
    try:
        system.start_comprehensive_scanning()
    except KeyboardInterrupt:
        logger.info("🛑 Comprehensive system stopped by user")
        system.stop()

if __name__ == "__main__":
    main()
