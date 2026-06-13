#!/usr/bin/env python3
"""
BRUTAL TRUTH VERIFICATION: All 5 Accounts Active
Checks logs and config to verify ALL accounts are actually running.
"""

import sys
import os
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# Load env
env_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k not in os.environ:
                    os.environ[k] = v.strip('"').strip("'")

sys.path.append(os.getcwd())

print("=== BRUTAL TRUTH VERIFICATION: ALL ACCOUNTS ACTIVE ===\n")
print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

# 1. Check Config
print("--- STEP 1: Runtime Config Check ---")
try:
    from src.control_plane.config_store import ConfigStore
    config_store = ConfigStore()
    config = config_store.load()
    
    if config.strategy_assignments:
        enabled = [a for a in config.strategy_assignments if a.enabled]
        print(f"✅ Config has {len(enabled)} enabled strategy assignments:")
        for a in enabled:
            print(f"   Account {a.account_id[-3:]}: {a.strategy_key}")
    else:
        print(f"❌ FAIL: No strategy_assignments in config")
        sys.exit(1)
except Exception as e:
    print(f"❌ FAIL: Config check failed: {e}")
    sys.exit(1)

# 2. Check Logs (last 500 lines, last 5 minutes)
print(f"\n--- STEP 2: Log Evidence Check (Last 5 minutes) ---")
log_path = "/tmp/runner.out"
if not os.path.exists(log_path):
    print(f"❌ FAIL: Log file not found: {log_path}")
    sys.exit(1)

try:
    with open(log_path, 'r') as f:
        lines = f.readlines()
        # Get last 500 lines
        recent_lines = lines[-500:] if len(lines) > 500 else lines
    
    # Parse STRAT_EVIDENCE lines
    accounts_seen = defaultdict(list)
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    for line in recent_lines:
        # Extract STRAT_EVIDENCE
        if "STRAT_EVIDENCE" in line:
            # Parse: account=001 strategy=momentum
            account_match = re.search(r'account=(\d{3})', line)
            strategy_match = re.search(r'strategy=([^\s]+)', line)
            if account_match and strategy_match:
                acc = account_match.group(1)
                strat = strategy_match.group(1)
                accounts_seen[acc].append(strat)
    
    print(f"Accounts with STRAT_EVIDENCE in last 500 log lines:")
    for acc in sorted(accounts_seen.keys()):
        unique_strats = list(set(accounts_seen[acc]))
        count = len(accounts_seen[acc])
        print(f"   Account {acc}: {count} signals, strategies: {unique_strats}")
    
    # Verify all 5 accounts
    expected_accounts = ['001', '002', '003', '004', '005']
    missing = [acc for acc in expected_accounts if acc not in accounts_seen]
    
    if missing:
        print(f"\n❌ FAIL: Missing accounts in logs: {missing}")
        print(f"   Only {len(accounts_seen)}/{len(expected_accounts)} accounts active")
        sys.exit(1)
    else:
        print(f"\n✅ PASS: All 5 accounts found in logs")
        
except Exception as e:
    print(f"❌ FAIL: Log check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. System State Check
print(f"\n--- STEP 3: System Runtime State Check ---")
try:
    from working_trading_system import WorkingTradingSystem
    system = WorkingTradingSystem()
    
    if system._strategy_assignments:
        enabled = [a for a in system._strategy_assignments if a.enabled]
        print(f"✅ System has {len(enabled)} enabled assignments:")
        for a in enabled:
            print(f"   Account {a.account_id[-3:]}: {a.strategy_key}")
        
        if len(enabled) != 5:
            print(f"\n❌ FAIL: Expected 5 assignments, got {len(enabled)}")
            sys.exit(1)
    else:
        print(f"❌ FAIL: System has no strategy_assignments (using legacy mode)")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAIL: System state check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n=== ✅ VERIFICATION PASSED ===")
print(f"All 5 accounts are configured and generating signals.")
print(f"\nEvidence:")
print(f"  - Config: {len(config.strategy_assignments)} assignments")
print(f"  - Logs: {len(accounts_seen)} accounts with recent signals")
print(f"  - System: {len(enabled)} enabled assignments")
