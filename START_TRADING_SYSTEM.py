#!/usr/bin/env python3
"""
RELIABLE STARTUP SCRIPT FOR TRADING SYSTEM
Handles startup gracefully, checks prerequisites, and ensures system runs
"""
import os
import sys
import time
import logging
import signal
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystemStarter:
    def __init__(self):
        self.system = None
        self.running = True
        
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        logger.info("🔍 Checking prerequisites...")
        
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 7):
            issues.append(f"Python 3.7+ required, found {sys.version}")
        else:
            logger.info(f"✓ Python version: {sys.version}")
        
        # Check required files
        required_files = [
            'ai_trading_system.py',
        ]
        
        for file in required_files:
            if Path(file).exists():
                logger.info(f"✓ Found {file}")
            else:
                issues.append(f"Missing required file: {file}")
        
        # Check API credentials
        try:
            sys.path.insert(0, '/workspace')
            with open('ai_trading_system.py', 'r') as f:
                content = f.read()
                if 'OANDA_API_KEY' in content and 'OANDA_ACCOUNT_ID' in content:
                    logger.info("✓ API credentials found in code")
                else:
                    issues.append("API credentials not found")
        except Exception as e:
            issues.append(f"Error checking credentials: {e}")
        
        if issues:
            logger.error("❌ Prerequisites check failed:")
            for issue in issues:
                logger.error(f"  • {issue}")
            return False
        
        logger.info("✅ All prerequisites met")
        return True
    
    def initialize_system(self):
        """Initialize the trading system"""
        logger.info("🚀 Initializing trading system...")
        
        try:
            sys.path.insert(0, '/workspace')
            from ai_trading_system import AITradingSystem
            
            logger.info("✓ Imported AITradingSystem")
            
            # Create system instance
            self.system = AITradingSystem()
            
            # Ensure trading is enabled
            if not self.system.trading_enabled:
                logger.warning("⚠ Trading disabled by default - enabling...")
                self.system.trading_enabled = True
            
            logger.info("✅ Trading system initialized")
            logger.info(f"  • Trading enabled: {self.system.trading_enabled}")
            logger.info(f"  • Account: {self.system.account_id}")
            logger.info(f"  • Instruments: {', '.join(self.system.instruments)}")
            logger.info(f"  • Max concurrent trades: {self.system.max_concurrent_trades}")
            logger.info(f"  • Risk per trade: {self.system.risk_per_trade*100}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize system: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_system(self):
        """Run the trading system"""
        if not self.system:
            logger.error("❌ System not initialized")
            return
        
        logger.info("🎯 Starting trading system...")
        
        # Send startup notification
        try:
            self.system.send_telegram_message(
                f"🚀 Trading System Started\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Account: {self.system.account_id}\n"
                f"Trading: ENABLED"
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")
        
        # Start Telegram command processor
        try:
            import threading
            telegram_thread = threading.Thread(
                target=self.system.telegram_command_loop,
                daemon=True
            )
            telegram_thread.start()
            logger.info("✓ Telegram command processor started")
        except Exception as e:
            logger.warning(f"Failed to start Telegram processor: {e}")
        
        # Start adaptive loop
        try:
            adaptive_thread = threading.Thread(
                target=self.system.adaptive_loop,
                daemon=True
            )
            adaptive_thread.start()
            logger.info("✓ Adaptive loop started")
        except Exception as e:
            logger.warning(f"Failed to start adaptive loop: {e}")
        
        # Main trading loop
        cycle_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        logger.info("🔄 Entering main trading loop...")
        
        while self.running:
            try:
                cycle_count += 1
                logger.info(f"🔄 Trading cycle #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Run trading cycle
                self.system.run_trading_cycle()
                
                consecutive_errors = 0  # Reset error counter on success
                
                # Wait before next cycle
                logger.info("⏰ Next cycle in 60 seconds...")
                for _ in range(60):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal")
                self.running = False
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ Error in trading cycle: {e}")
                import traceback
                traceback.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"❌ Too many consecutive errors ({consecutive_errors}). Stopping.")
                    self.running = False
                    break
                
                # Wait before retry
                logger.info(f"⏰ Waiting 30 seconds before retry...")
                time.sleep(30)
        
        logger.info("🛑 Trading system stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}")
        self.running = False
    
    def start(self):
        """Start the trading system with full checks"""
        logger.info("="*80)
        logger.info("TRADING SYSTEM STARTUP")
        logger.info("="*80)
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("❌ Prerequisites check failed. Exiting.")
            return False
        
        # Initialize system
        if not self.initialize_system():
            logger.error("❌ System initialization failed. Exiting.")
            return False
        
        # Run system
        try:
            self.run_system()
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        logger.info("✅ Trading system shutdown complete")
        return True

if __name__ == "__main__":
    starter = TradingSystemStarter()
    success = starter.start()
    sys.exit(0 if success else 1)
