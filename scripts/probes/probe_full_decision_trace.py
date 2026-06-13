#!/usr/bin/env python3
"""
Probe Step 7: End-to-End Decision Trace
Trace ONE candle from data -> signal -> gate -> execution decision.
"""
import sys
import os
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.strategies.session_regime_aligned import SessionRegimeAlignedStrategy
from src.control_plane.market_data_provider import get_latest_price, get_candles
from src.core.execution_gate import ExecutionGuard

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_trace")

def probe_full_trace():
    instrument = "XAU_USD"
    logger.info(f"Starting End-to-End Trace for {instrument}...")
    
    trace = {}
    
    try:
        # 1. Market Data
        logger.info("[1] Checking Market Data...")
        price = get_latest_price(instrument)
        trace['market_data'] = {'price': price.mid, 'time': price.ts_utc}
        logger.info(f"   Price: {price.mid} (Spread: {price.ask - price.bid:.2f})")
        
        # 2. Strategy Logic (Gatekeeper)
        logger.info("[2] Checking Session Regime Gate...")
        gate = SessionRegimeAlignedStrategy()
        timestamp_utc = datetime.now(timezone.utc)
        
        # Mock context for now, assuming probe_session_gate verified the details
        # We define a helper to capture the emit
        # But for this trace, we can just call it and rely on the return
        
        allowed = gate.should_allow_trade(instrument, {instrument: price}, {"state": "normal"}, timestamp_utc)
        trace['gate_allowed'] = allowed
        
        if not allowed:
             logger.warning("   GATE BLOCKED. Check probe_session_gate output for details.")
        else:
             logger.info("   Gate ALLOWED.")

        # 3. Execution Guard
        logger.info("[3] Checking Execution Guard...")
        guard = ExecutionGuard()
        decision = guard.decision()
        trace['execution_guard'] = {'allowed': decision.allowed, 'reason': decision.reason_code}
        
        if not decision.allowed:
            logger.warning(f"   EXECUTION BLOCKED: {decision.reason_code}")
        else:
            logger.info("   Execution Guard ALLOWED.")
            
        # 4. Conclusion
        logger.info("--- TRACE CONCLUSION ---")
        if trace['gate_allowed'] and trace['execution_guard']['allowed']:
            logger.info("✅ SYSTEM SHOULD BE TRADING (if signals exist).")
        else:
            blockers = []
            if not trace['gate_allowed']: blockers.append("SessionRegimeGate")
            if not trace['execution_guard']['allowed']: blockers.append(f"ExecutionGuard({decision.reason_code})")
            logger.info(f"❌ BLOCKED BY: {', '.join(blockers)}")

    except Exception as e:
        logger.error(f"Trace failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_full_trace()
