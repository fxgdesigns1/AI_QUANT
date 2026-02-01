#!/usr/bin/env python3
"""
Weekend Trading Shutdown System
Properly stops trading signals during weekends and market closures
"""

import os
import sys
import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeekendTradingShutdown:
    """Properly stops trading signals during weekends and market closures"""
    
    def __init__(self):
        self.system_url = "https://ai-quant-trading.uc.r.appspot.com"
        self.is_weekend_mode = False
        self.is_running = False
        
        logger.info("✅ WeekendTradingShutdown initialized")
    
    def is_weekend(self) -> bool:
        """Check if it's weekend (Saturday or Sunday) - DISABLED FOR TESTING"""
        # Temporarily disabled to wake system out of weekend mode
        return False
        # now = datetime.now(timezone.utc)
        # return now.weekday() >= 5  # Saturday=5, Sunday=6
    
    def is_market_closed(self) -> bool:
        """Check if markets are closed (weekends)"""
        return self.is_weekend()
    
    def stop_trading_system(self):
        """Stop the trading system via API"""
        try:
            logger.info("🛑 Stopping trading system for weekend...")
            
            # Try to stop the system via API
            try:
                response = requests.post(f"{self.system_url}/tasks/full_scan", 
                                       json={"action": "stop"}, 
                                       timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Trading system stopped via API")
                else:
                    logger.warning(f"⚠️ API stop failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ API stop failed: {e}")
            
            # Send weekend notification
            try:
                response = requests.post(f"{self.system_url}/api/telegram/test", 
                                       json={
                                           "message": "🛑 WEEKEND MODE ACTIVATED\n"
                                                    "• Trading system stopped for weekend\n"
                                                    "• No trade signals will be sent\n"
                                                    "• System will resume Monday\n"
                                                    "• Cost savings: $20-30/month"
                                       }, 
                                       timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Weekend notification sent")
            except Exception as e:
                logger.warning(f"⚠️ Weekend notification failed: {e}")
            
            self.is_weekend_mode = True
            logger.info("✅ Weekend trading shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error stopping trading system: {e}")
    
    def start_trading_system(self):
        """Start the trading system for market hours"""
        try:
            logger.info("🚀 Starting trading system for market hours...")
            
            # Try to start the system via API
            try:
                response = requests.post(f"{self.system_url}/tasks/full_scan", 
                                       json={"action": "start"}, 
                                       timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Trading system started via API")
                else:
                    logger.warning(f"⚠️ API start failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ API start failed: {e}")
            
            # Send market open notification
            try:
                response = requests.post(f"{self.system_url}/api/telegram/test", 
                                       json={
                                           "message": "🚀 MARKET HOURS MODE ACTIVATED\n"
                                                    "• Trading system started\n"
                                                    "• Trade signals will resume\n"
                                                    "• Full capacity active\n"
                                                    "• Ready for trading opportunities"
                                       }, 
                                       timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Market open notification sent")
            except Exception as e:
                logger.warning(f"⚠️ Market open notification failed: {e}")
            
            self.is_weekend_mode = False
            logger.info("✅ Market hours trading started")
            
        except Exception as e:
            logger.error(f"❌ Error starting trading system: {e}")
    
    def check_and_manage_weekend_mode(self):
        """Check current time and manage weekend mode"""
        try:
            is_weekend = self.is_weekend()
            
            if is_weekend and not self.is_weekend_mode:
                logger.info("📅 Weekend detected - stopping trading system")
                self.stop_trading_system()
                
            elif not is_weekend and self.is_weekend_mode:
                logger.info("📅 Market hours detected - starting trading system")
                self.start_trading_system()
                
            else:
                # Log current status
                status = "WEEKEND MODE" if is_weekend else "MARKET HOURS"
                logger.info(f"📊 Current status: {status}")
                
        except Exception as e:
            logger.error(f"❌ Error in weekend mode check: {e}")
    
    def start_monitoring(self):
        """Start weekend monitoring"""
        if self.is_running:
            logger.warning("⚠️ Monitoring already running")
            return
        
        logger.info("🚀 Starting weekend trading monitoring...")
        self.is_running = True
        
        # Initial check
        self.check_and_manage_weekend_mode()
        
        # Start monitoring thread
        def monitor_loop():
            while self.is_running:
                try:
                    self.check_and_manage_weekend_mode()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"❌ Monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("✅ Weekend trading monitoring started")
        logger.info("📅 Monitoring schedule:")
        logger.info("   • Check every 5 minutes")
        logger.info("   • Stop trading on weekends")
        logger.info("   • Start trading on weekdays")
    
    def stop_monitoring(self):
        """Stop weekend monitoring"""
        self.is_running = False
        logger.info("🛑 Weekend trading monitoring stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'is_running': self.is_running,
            'is_weekend': self.is_weekend(),
            'is_weekend_mode': self.is_weekend_mode,
            'current_time': datetime.now(timezone.utc).isoformat(),
            'status': 'WEEKEND MODE' if self.is_weekend_mode else 'MARKET HOURS'
        }

# Global shutdown manager
weekend_shutdown = WeekendTradingShutdown()

def get_weekend_shutdown():
    """Get the weekend shutdown manager"""
    return weekend_shutdown

if __name__ == "__main__":
    # Run weekend check and shutdown if needed
    shutdown_manager = WeekendTradingShutdown()
    
    if shutdown_manager.is_weekend():
        logger.info("📅 WEEKEND DETECTED - Stopping trading system")
        shutdown_manager.stop_trading_system()
    else:
        logger.info("📅 MARKET HOURS - Trading system should be active")
    
    # Start monitoring
    shutdown_manager.start_monitoring()
    
    try:
        # Keep running
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down weekend monitoring")
        shutdown_manager.stop_monitoring()
