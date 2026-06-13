#!/usr/bin/env python3
"""
Investigate Account 004 Dormancy
Parse runner logs to determine why account 004 has zero closed trades since 14:00 UTC.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.settings import settings
from src.control_plane.strategy_registry import get_strategy_registry
from src.control_plane.config_store import ConfigStore

def parse_journalctl_logs(hours: int = 48) -> List[str]:
    """Parse runner logs from journalctl"""
    try:
        # Get logs from last N hours
        since = f"{hours} hours ago"
        cmd = ["journalctl", "-u", "ai-quant-runner", "--since", since, "--no-pager"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"⚠️ journalctl returned {result.returncode}: {result.stderr}")
            return []
        
        return result.stdout.splitlines()
    except subprocess.TimeoutExpired:
        print("⚠️ journalctl timed out")
        return []
    except Exception as e:
        print(f"⚠️ Error running journalctl: {e}")
        return []

def filter_account_004_lines(lines: List[str]) -> List[str]:
    """Filter lines containing account=004 or account 004"""
    filtered = []
    for line in lines:
        if "account=004" in line.lower() or "account 004" in line.lower() or "004" in line:
            # Check if it's actually about account 004 (not just contains "004" in other context)
            if any(marker in line.lower() for marker in ["account=004", "account 004", "101-004-30719775-004"]):
                filtered.append(line)
    return filtered

def classify_block_reason(line: str) -> str:
    """Classify why a trade was blocked"""
    line_lower = line.lower()
    
    if "strategy_blocked" in line_lower or "strategy not assigned" in line_lower:
        return "strategy_blocked"
    elif "missing_instruments" in line_lower or "instrument not configured" in line_lower:
        return "missing_instruments"
    elif "regime_gate" in line_lower or "regime blocked" in line_lower or "market regime" in line_lower:
        return "regime_gate_block"
    elif "no signals" in line_lower or "no opportunities" in line_lower:
        return "no_signals"
    elif "execution_blocked" in line_lower or "execution gate" in line_lower or "blocked" in line_lower:
        return "execution_blocked"
    elif "price sanity" in line_lower or "stop loss too far" in line_lower:
        return "price_sanity_block"
    elif "daily limit" in line_lower or "trade cap" in line_lower:
        return "daily_limit_reached"
    elif "risk limit" in line_lower:
        return "risk_limit"
    else:
        return "unknown"

def check_strategy_registry_for_004() -> Dict[str, Any]:
    """Check strategy registry for account 004 instruments"""
    config_store = ConfigStore()
    config = config_store.load()
    
    account_004_id = f"{settings.account_id_prefix}004"
    
    # Find strategy assignments for account 004
    assignments = config.strategy_assignments or []
    account_004_assignments = [a for a in assignments if a.account_id == account_004_id]
    
    registry = get_strategy_registry()
    
    result = {
        "account_id": account_004_id,
        "strategy_assignments": [],
        "instruments": [],
        "enabled": False
    }
    
    for assignment in account_004_assignments:
        strategy_info = registry.get(assignment.strategy_key)
        if strategy_info:
            result["strategy_assignments"].append({
                "strategy_key": assignment.strategy_key,
                "strategy_name": strategy_info.name,
                "enabled": assignment.enabled,
                "instruments": strategy_info.instruments
            })
            result["instruments"].extend(strategy_info.instruments)
            if assignment.enabled:
                result["enabled"] = True
    
    result["instruments"] = list(set(result["instruments"]))  # Dedupe
    
    return result

def check_account_allowlist() -> Dict[str, Any]:
    """Check if account 004 is in ACCOUNT_SUFFIX_ALLOWLIST"""
    suffixes = settings.account_suffix_allowlist
    return {
        "account_suffix_allowlist": suffixes,
        "004_in_allowlist": "004" in suffixes if suffixes else False
    }

def analyze_logs(lines: List[str]) -> Dict[str, Any]:
    """Analyze filtered log lines"""
    block_reasons = defaultdict(int)
    signal_attempts = 0
    execution_attempts = 0
    successful_trades = 0
    last_activity = None
    
    for line in lines:
        line_lower = line.lower()
        
        # Track last activity timestamp
        try:
            # Try to extract timestamp from log line (format varies)
            if "account=004" in line_lower or "account 004" in line_lower:
                # Extract ISO timestamp if present
                for part in line.split():
                    if "t" in part.lower() and ("z" in part.lower() or "+" in part):
                        try:
                            ts_str = part.replace("T", " ").replace("Z", "").replace("+00:00", "")
                            # Try parsing
                            last_activity = part
                            break
                        except:
                            pass
        except:
            pass
        
        # Count signal generation attempts
        if "signal" in line_lower and ("004" in line or "account=004" in line_lower):
            signal_attempts += 1
        
        # Count execution attempts
        if ("executing" in line_lower or "placing order" in line_lower) and "004" in line:
            execution_attempts += 1
        
        # Count successful trades
        if ("trade executed" in line_lower or "order filled" in line_lower) and "004" in line:
            successful_trades += 1
        
        # Classify block reasons
        if "blocked" in line_lower or "skip" in line_lower or "reject" in line_lower:
            reason = classify_block_reason(line)
            block_reasons[reason] += 1
    
    return {
        "block_reasons": dict(block_reasons),
        "signal_attempts": signal_attempts,
        "execution_attempts": execution_attempts,
        "successful_trades": successful_trades,
        "last_activity": last_activity,
        "total_relevant_lines": len(lines)
    }

def main():
    print("=" * 60)
    print("ACCOUNT 004 DORMANCY INVESTIGATION")
    print("=" * 60)
    print()
    
    # Step 1: Parse runner logs
    print("Step 1: Parsing runner logs (last 48 hours)...")
    all_lines = parse_journalctl_logs(hours=48)
    print(f"   Total log lines: {len(all_lines)}")
    
    # Step 2: Filter for account 004
    print("\nStep 2: Filtering for account 004...")
    account_004_lines = filter_account_004_lines(all_lines)
    print(f"   Account 004 relevant lines: {len(account_004_lines)}")
    
    # Step 3: Analyze logs
    print("\nStep 3: Analyzing log patterns...")
    log_analysis = analyze_logs(account_004_lines)
    
    # Step 4: Check strategy registry
    print("\nStep 4: Checking strategy registry...")
    strategy_info = check_strategy_registry_for_004()
    
    # Step 5: Check allowlist
    print("\nStep 5: Checking ACCOUNT_SUFFIX_ALLOWLIST...")
    allowlist_info = check_account_allowlist()
    
    # Compile findings
    findings = {
        "investigation_timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": f"{settings.account_id_prefix}004",
        "log_analysis": log_analysis,
        "strategy_configuration": strategy_info,
        "allowlist_status": allowlist_info,
        "summary": {
            "total_log_lines_analyzed": len(account_004_lines),
            "signal_attempts": log_analysis["signal_attempts"],
            "execution_attempts": log_analysis["execution_attempts"],
            "successful_trades": log_analysis["successful_trades"],
            "primary_block_reason": max(log_analysis["block_reasons"].items(), key=lambda x: x[1])[0] if log_analysis["block_reasons"] else "no_blocks_found",
            "strategy_enabled": strategy_info["enabled"],
            "in_allowlist": allowlist_info["004_in_allowlist"]
        }
    }
    
    # Determine root cause
    root_cause = "unknown"
    if not allowlist_info["004_in_allowlist"]:
        root_cause = "not_in_allowlist"
    elif not strategy_info["enabled"]:
        root_cause = "no_strategy_assigned_or_disabled"
    elif log_analysis["signal_attempts"] == 0:
        root_cause = "no_signals_generated"
    elif log_analysis["execution_attempts"] == 0:
        root_cause = "signals_generated_but_not_executed"
    elif log_analysis["block_reasons"]:
        root_cause = list(log_analysis["block_reasons"].keys())[0]
    
    findings["root_cause"] = root_cause
    
    # Write report
    output_file = "logs/account_004_dormancy_report.json"
    os.makedirs("logs", exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(findings, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("FINDINGS SUMMARY")
    print("=" * 60)
    print(f"Account ID: {findings['account_id']}")
    print(f"Root Cause: {root_cause}")
    print(f"In Allowlist: {allowlist_info['004_in_allowlist']}")
    print(f"Strategy Enabled: {strategy_info['enabled']}")
    print(f"Signal Attempts: {log_analysis['signal_attempts']}")
    print(f"Execution Attempts: {log_analysis['execution_attempts']}")
    print(f"Successful Trades: {log_analysis['successful_trades']}")
    if log_analysis["block_reasons"]:
        print("\nBlock Reasons:")
        for reason, count in sorted(log_analysis["block_reasons"].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {reason}: {count}")
    
    print(f"\n✅ Report written to: {output_file}")
    
    return findings

if __name__ == "__main__":
    main()
