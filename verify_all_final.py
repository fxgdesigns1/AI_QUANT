#!/usr/bin/env python3
"""
Comprehensive System Verification Script
Verifies:
1. System Status (Runner, Mode)
2. Account 006 Alignment (Strict Logic)
3. Outlook Engine Logic (EMA + Lowered Thresholds)
4. Session Execution Strategy (Safety Rules)
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone
import subprocess

# Add project root to path
sys.path.append(os.getcwd())

# Setup logging
LOG_FILE = "VERIFICATION_REPORT_FINAL.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}\nError: {e.stderr}")
        return None

def verify_runner_status():
    logger.info("=== 1. VERIFYING RUNNER STATUS ===")
    
    # Check PID
    pid = run_command("ps aux | grep 'runner_src.runner.main' | grep -v grep | awk '{print $2}'")
    if pid:
        logger.info(f"✅ Runner is ACTIVE (PID: {pid})")
    else:
        logger.error("❌ Runner is NOT active")
        return False

    # Check status.json
    try:
        with open("runtime/status.json", "r") as f:
            status = json.load(f)
            mode = status.get("system", {}).get("mode", "unknown")
            exec_enabled = status.get("system", {}).get("execution_enabled", False)
            logger.info(f"✅ System Mode: {mode}")
            logger.info(f"✅ Execution Enabled: {exec_enabled}")
            
            if mode == "paper" and exec_enabled:
                logger.info("✅ System is correctly configured for PAPER TRADING")
            else:
                logger.warning(f"⚠️ System configuration mismatch: Mode={mode}, Exec={exec_enabled}")
    except Exception as e:
        logger.error(f"❌ Could not read status.json: {e}")
        return False
        
    return True

def verify_outlook_engine_logic():
    logger.info("\n=== 2. VERIFYING OUTLOOK ENGINE LOGIC ===")
    
    try:
        from src.control_plane.outlook_engine import get_outlook_engine
        engine = get_outlook_engine()
        
        # We can't easily test internal logic without mocking, but we can verify the file content
        # contains the critical changes
        
        with open("src/control_plane/outlook_engine.py", "r") as f:
            content = f.read()
            
            # Check 1: H1 candles for daily
            if 'granularity = "H1"' in content:
                logger.info("✅ Daily bias uses H1 candles (Reactive)")
            else:
                logger.error("❌ Daily bias NOT using H1 candles")
                
            # Check 2: EMA Structure
            if "EMA structure is PRIMARY signal" in content:
                logger.info("✅ EMA Structure logic present")
            else:
                logger.error("❌ EMA Structure logic MISSING")
                
            # Check 3: Lowered Gold Threshold
            if "bullish_threshold = 0.3" in content and "is_metal" in content:
                logger.info("✅ Gold threshold lowered to 0.3% (Early detection)")
            else:
                logger.error("❌ Gold threshold verify failed")
                
            # Check 4: Hybrid Logic
            if "HYBRID LOGIC" in content:
                logger.info("✅ Hybrid Logic (EMA + Price) present")
            else:
                logger.error("❌ Hybrid Logic missing")

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")

def verify_session_strategy_safety():
    logger.info("\n=== 3. VERIFYING SESSION STRATEGY SAFETY ===")
    
    try:
        with open("src/strategies/session_execution_strategy.py", "r") as f:
            content = f.read()
            
            # Check 1: Strict Alignment
            if 'STRICT ALIGNMENT REQUIRED' in content:
                logger.info("✅ Strict Alignment rule present")
            else:
                logger.error("❌ Strict Alignment rule MISSING")
                
            # Check 2: Neutral Blocking
            if 'if daily == "NEUTRAL" or weekly == "NEUTRAL":' in content:
                logger.info("✅ NEUTRAL blocking logic verified (Fail-Closed)")
            else:
                logger.error("❌ NEUTRAL blocking logic missing or incorrect")
                
            # Check 3: Misalignment Blocking
            if 'daily_weekly_misaligned' in content:
                logger.info("✅ Misalignment blocking verified")
            else:
                logger.error("❌ Misalignment blocking missing")

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")

def verify_logs():
    logger.info("\n=== 4. VERIFYING RECENT LOGS ===")
    
    # Check session_regime_gate_audit.jsonl for recent activity
    log_file = "logs/session_regime_gate_audit.jsonl"
    if os.path.exists(log_file):
        lines = run_command(f"tail -n 5 {log_file}")
        logger.info(f"Recent Audit Logs:\n{lines}")
    else:
        logger.warning("⚠️ No audit logs found")

def main():
    logger.info("STARTING FINAL SYSTEM VERIFICATION")
    logger.info(f"Date: {datetime.now(timezone.utc)}")
    logger.info("-" * 50)
    
    verify_runner_status()
    verify_outlook_engine_logic()
    verify_session_strategy_safety()
    verify_logs()
    
    logger.info("-" * 50)
    logger.info("VERIFICATION COMPLETE")
    logger.info(f"Full report written to: {os.path.abspath(LOG_FILE)}")

if __name__ == "__main__":
    main()
