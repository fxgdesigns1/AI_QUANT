#!/usr/bin/env python3
"""
Probe Step 3: Session Regime Gate Probe
Determine if signals were blocked AFTER generation by the SessionRegimeAlignedStrategy.
"""
import sys
import os
import logging
from datetime import datetime, timezone
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.strategies.session_regime_aligned import SessionRegimeAlignedStrategy
from src.control_plane.market_data_provider import get_latest_price

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_session_gate")

def probe_session_gate():
    instrument = "XAU_USD"
    logger.info(f"Probing Session Regime Gate for {instrument}...")
    
    try:
        # Initialize Gate
        gate = SessionRegimeAlignedStrategy()
        
        # Build Context
        # We need market data
        try:
            price = get_latest_price(instrument)
            market_data = {instrument: price}
        except Exception as e:
            logger.warning(f"Could not fetch live price: {e}. Using mock.")
            from src.control_plane.market_data_provider import Price
            import time
            market_data = {instrument: Price(instrument, 2000.0, 2000.1, 2000.05, time.time())}
        
        # We need news context (mocked or fetched)
        # For probe, we want to see what it thinks NOW.
        news_context = {"state": "normal", "is_embargo": False}
        
        # Evaluate
        timestamp_utc = datetime.now(timezone.utc)
        allowed = gate.should_allow_trade(instrument, market_data, news_context, timestamp_utc)
        
        logger.info(f"Gate Decision: {'ALLOWED' if allowed else 'BLOCKED'}")
        
        # Check audit log
        log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs/session_regime_gate_audit.jsonl"))
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    try:
                        last_log = json.loads(lines[-1])
                        logger.info("--- Latest Gate Audit Log ---")
                        logger.info(f"Timestamp: {last_log.get('timestamp')}")
                        logger.info(f"Allowed: {last_log.get('allowed')}")
                        logger.info(f"Reason: {last_log.get('reason')}")
                        logger.info(f"Session: {last_log.get('session')}")
                        logger.info(f"Regime: {last_log.get('regime')}")
                        logger.info(f"News State: {last_log.get('news_state')}")
                        logger.info(f"Roadmap Aligned: {last_log.get('roadmap_aligned')}")
                        logger.info(f"Daily Bias: {last_log.get('daily_bias')} ({last_log.get('daily_reason')})")
                        logger.info(f"Weekly Bias: {last_log.get('weekly_bias')} ({last_log.get('weekly_reason')})")
                        logger.info(f"Readiness Score: {last_log.get('readiness_score')}")
                    except json.JSONDecodeError:
                        logger.warning("Last log line is not valid JSON")
        else:
            logger.warning(f"No audit log found at {log_file}")

    except Exception as e:
        logger.error(f"Probe failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_session_gate()
