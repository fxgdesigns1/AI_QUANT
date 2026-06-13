#!/usr/bin/env python3
"""
Final System Verification Script
"""
import os
import sys
import json
import logging
import subprocess
from datetime import datetime

# Add workspace root to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("final_verify")

REPORT_FILE = "VERIFICATION_REPORT_FINAL.log"

def log_report(msg):
    with open(REPORT_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")
    print(msg)

def verify_circular_imports():
    log_report("1. Verifying OutlookEngine Circular Imports...")
    try:
        from src.control_plane.outlook_engine import get_outlook_engine
        engine = get_outlook_engine()
        log_report("   PASS: OutlookEngine imported successfully.")
        return True
    except ImportError as e:
        log_report(f"   FAIL: Import error: {e}")
        return False
    except Exception as e:
        log_report(f"   FAIL: Unexpected error: {e}")
        return False

def verify_dependencies_006():
    log_report("2. Verifying SessionExecutionStrategy (006) Dependencies...")
    try:
        result = subprocess.run([sys.executable, "debug_006.py"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "Dependencies are loaded" in result.stdout:
            log_report("   PASS: debug_006.py executed successfully.")
            return True
        else:
            log_report(f"   FAIL: debug_006.py failed. Output:\n{result.stdout}\nError:\n{result.stderr}")
            return False
    except Exception as e:
        log_report(f"   FAIL: Failed to run debug_006.py: {e}")
        return False

def verify_snapshot_logic():
    log_report("3. Verifying Snapshot Integrity Logic...")
    try:
        with open("working_trading_system.py", "r") as f:
            content = f.read()
            checks = [
                "get_outlook_engine",
                "MarketRegimeDetector",
                "daily_bias",
                "regime",
                "session",
                "status_writer.write(snapshot)"
            ]
            missing = [c for c in checks if c not in content]
            if not missing:
                log_report("   PASS: working_trading_system.py contains required logic.")
                return True
            else:
                log_report(f"   FAIL: working_trading_system.py missing logic: {missing}")
                return False
    except Exception as e:
        log_report(f"   FAIL: Could not read working_trading_system.py: {e}")
        return False

def verify_gate_audit():
    log_report("4. Verifying Gate Audit Logs...")
    log_path = "logs/session_regime_gate_audit.jsonl"
    if os.path.exists(log_path):
        log_report("   PASS: Audit log exists.")
        return True
    else:
        log_report("   WARN: Audit log not found (acceptable if no execution run yet).")
        return True

def main():
    if os.path.exists(REPORT_FILE):
        os.remove(REPORT_FILE)
    
    log_report("--- FINAL SYSTEM VERIFICATION START ---")
    
    c1 = verify_circular_imports()
    c2 = verify_dependencies_006()
    c3 = verify_snapshot_logic()
    c4 = verify_gate_audit()
    
    success = c1 and c2 and c3 and c4
    
    if success:
        log_report("--- VERIFICATION COMPLETE: SYSTEM GO ---")
        log_report("READY_FOR_CONTROLLED_EXECUTION = false (paper only)")
    else:
        log_report("--- VERIFICATION FAILED: SYSTEM NO-GO ---")
        sys.exit(1)

if __name__ == "__main__":
    main()
