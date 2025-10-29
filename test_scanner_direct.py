#!/usr/bin/env python3
"""
TEST SCANNER DIRECTLY - NO FLASK, JUST SCANNER
"""

import os
import sys
import logging

# Set up environment
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.simple_timer_scanner import get_simple_scanner

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_scanner():
    """Test the scanner directly"""
    logger.info("🚀 TESTING SCANNER DIRECTLY...")
    
    try:
        # Get scanner
        scanner = get_simple_scanner()
        if not scanner:
            logger.error("❌ Failed to get scanner")
            return
        
        logger.info("✅ Scanner obtained")
        
        # Run scan
        logger.info("🔄 Running scan...")
        scanner._run_scan()
        logger.info("✅ Scan completed")
        
    except Exception as e:
        logger.error(f"❌ Scanner test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scanner()


