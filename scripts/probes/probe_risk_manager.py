#!/usr/bin/env python3
"""
Probe Step 6: Risk Constraints Probe
Ensure risk manager did not silently block trades.
"""
import sys
import os
import logging
import requests
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.adaptive_system import AdaptiveRiskManager, MarketCondition, MarketRegime
from src.core.execution_gate import ExecutionGuard

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_risk_manager")

def get_oanda_account_summary(account_id):
    api_key = os.getenv("OANDA_API_KEY")
    base_url = "https://api-fxpractice.oanda.com" # Default to practice for safety
    if os.getenv("TRADING_MODE", "").lower() == "live":
        base_url = "https://api-fxtrade.oanda.com"
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{base_url}/v3/accounts/{account_id}/summary"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("account", {})
        else:
            logger.error(f"OANDA API Error: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None

def probe_risk_manager():
    logger.info("Probing Risk Manager constraints...")
    
    try:
        # 1. Theoretical Risk (Adaptive)
        # We need to simulate a condition
        arm = AdaptiveRiskManager()
        # Assume normal/trending for baseline
        adj = arm.get_risk_adjustment(MarketCondition.NORMAL, MarketRegime.TRENDING)
        logger.info("--- Adaptive Risk Parameters (Baseline) ---")
        logger.info(f"Size Multiplier: {adj.position_size_multiplier}")
        logger.info(f"Stop Loss Multiplier: {adj.stop_loss_multiplier}")
        logger.info(f"Confidence Mod: {adj.confidence_threshold_modifier}")
        
        # 2. Execution Guard (Daily Loss)
        guard = ExecutionGuard()
        # We need to trigger the private _check_daily_pnl if possible, or just deduce from decision
        max_daily_loss = float(os.getenv("MAX_DAILY_LOSS_USD", "0"))
        logger.info(f"Max Daily Loss Config: ${max_daily_loss}")
        
        decision = guard.decision()
        if decision.reason_code == "MAX_DAILY_LOSS_TRIPPED":
             logger.error("BLOCKER: Max daily loss tripped!")
        
        # 3. Account State (Equity/Margin)
        account_id_prefix = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-")
        account_suffix = "006" # Focused on the execution account
        account_id = f"{account_id_prefix}{account_suffix}"
        
        logger.info(f"Fetching summary for Account {account_id}...")
        summary = get_oanda_account_summary(account_id)
        
        if summary:
            equity = float(summary.get("NAV", 0))
            margin_avail = float(summary.get("marginAvailable", 0))
            margin_used = float(summary.get("marginUsed", 0))
            open_trade_count = summary.get("openTradeCount", 0)
            
            logger.info(f"NAV (Equity): ${equity:.2f}")
            logger.info(f"Margin Available: ${margin_avail:.2f}")
            logger.info(f"Margin Used: ${margin_used:.2f}")
            logger.info(f"Open Trades: {open_trade_count}")
            
            if margin_avail < 100:
                logger.warning("BLOCKER: Low margin available!")
        else:
            logger.warning("Could not fetch account summary.")

    except Exception as e:
        logger.error(f"Probe failed: {e}")

if __name__ == "__main__":
    probe_risk_manager()
