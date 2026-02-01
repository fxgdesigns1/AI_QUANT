#!/usr/bin/env python3
"""
Startup Script to Initialize Trading Scanner
This script is called after main application starts
"""
import os
import sys
import logging
import threading
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_trading_scanner():
    """Initialize and start the trading scanner"""
    try:
        logger.info("🚀 STARTING TRADING SCANNER...")
        
        # Import scanner
        from src.core.candle_based_scanner import get_candle_scanner
        
        # Get scanner instance
        scanner = get_candle_scanner()
        
        logger.info(f"✅ Scanner initialized")
        logger.info(f"✅ Strategies: {list(scanner.strategies.keys())}")
        logger.info(f"✅ Accounts: {scanner.accounts}")
        
        # Start scanning
        scanner.start_scanning()
        
        logger.info("✅ TRADING SCANNER STARTED SUCCESSFULLY")
        
        # Keep running
        while True:
            time.sleep(60)
            logger.info(f"📊 Scanner running - Scan count: {scanner.scan_count}, Signals: {scanner.total_signals}")
            
    except Exception as e:
        logger.error(f"❌ Failed to start scanner: {e}")
        logger.exception("Full traceback:")

if __name__ == "__main__":
    start_trading_scanner()





