#!/usr/bin/env python3
"""
Probe Step 5: Execution Switch Probe
Ensure execution was actually enabled.
"""
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.execution_gate import ExecutionGuard

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_execution_flags")

def probe_execution_flags():
    logger.info("Probing execution flags...")
    
    try:
        guard = ExecutionGuard()
        decision = guard.decision()
        
        logger.info(f"Execution Allowed: {decision.allowed}")
        logger.info(f"Mode: {decision.mode}")
        logger.info(f"Reason Code: {decision.reason_code}")
        logger.info(f"Details: {decision.details}")
        
        # Check specific env vars manually to be sure
        env_vars = [
            "TRADING_MODE",
            "LIVE_TRADING_ENABLED",
            "KILL_SWITCH",
            "PAPER_EXECUTION_ENABLED",
            "EXECUTION_ENABLED"
        ]
        
        logger.info("--- Environment Variables ---")
        for var in env_vars:
            logger.info(f"{var}: {os.getenv(var, 'Not Set')}")
            
    except Exception as e:
        logger.error(f"Probe failed: {e}")

if __name__ == "__main__":
    probe_execution_flags()
