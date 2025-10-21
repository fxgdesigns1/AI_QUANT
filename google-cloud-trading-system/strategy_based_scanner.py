#!/usr/bin/env python3
"""
STRATEGY-BASED SCANNER - Uses YOUR strategy rules, not arbitrary thresholds
Executes when YOUR strategies generate signals
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def strategy_scan():
    """Run all strategies and execute THEIR signals"""
    from src.core.simple_timer_scanner import SimpleTimerScanner
    
    logger.info("🎯 STRATEGY SCAN - Using YOUR strategy rules")
    
    try:
        scanner = SimpleTimerScanner()
        
        # This uses all 10 strategies with THEIR OWN rules
        scanner._run_scan()
        
        logger.info("✅ Strategy scan complete")
        return "Success"
        
    except Exception as e:
        logger.error(f"❌ Strategy scan error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}"

if __name__ == '__main__':
    strategy_scan()
