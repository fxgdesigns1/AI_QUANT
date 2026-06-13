#!/usr/bin/env python3
"""
Verification script for Strategy Trigger Probe

Verifies probe output and provides analysis of strategy evaluation patterns.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Probe log paths
PROBE_LOG_PATH = "/opt/ai-quant/logs/strategy_trigger_probe.jsonl"
LOCAL_LOG_PATH = "logs/strategy_trigger_probe.jsonl"


def get_probe_log_path() -> Optional[str]:
    """Determine which log path exists"""
    if os.path.exists(PROBE_LOG_PATH):
        return PROBE_LOG_PATH
    elif os.path.exists(LOCAL_LOG_PATH):
        return LOCAL_LOG_PATH
    else:
        return None


def load_probe_records(log_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load records from JSONL log file"""
    records = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                    if limit and len(records) >= limit:
                        break
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line: {e}")
                    continue
    except FileNotFoundError:
        print(f"Log file not found: {log_path}")
    except Exception as e:
        print(f"Error reading log file: {e}")
    
    return records


def analyze_evaluation_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze strategy evaluation records"""
    analysis = {
        "total_evaluations": 0,
        "signals_generated": 0,
        "signals_blocked": 0,
        "strategies_evaluated": set(),
        "instruments_evaluated": set(),
        "blocking_conditions": Counter(),
        "exit_reasons": Counter(),
        "near_misses": [],
        "regime_distribution": Counter(),
        "bias_distribution": Counter(),
    }
    
    for record in records:
        if record.get("type") != "strategy_evaluation":
            continue
        
        analysis["total_evaluations"] += 1
        analysis["strategies_evaluated"].add(record.get("strategy_id", "UNKNOWN"))
        analysis["instruments_evaluated"].add(record.get("instrument", "UNKNOWN"))
        
        if record.get("returned_signal"):
            analysis["signals_generated"] += 1
        else:
            analysis["signals_blocked"] += 1
        
        exit_reason = record.get("exit_reason")
        if exit_reason:
            analysis["exit_reasons"][exit_reason] += 1
        
        blocking = record.get("first_blocking_condition")
        if blocking:
            condition_name = blocking.get("condition_name", "UNKNOWN")
            analysis["blocking_conditions"][condition_name] += 1
        
        near_miss = record.get("near_miss")
        if near_miss:
            analysis["near_misses"].append({
                "strategy_id": record.get("strategy_id"),
                "instrument": record.get("instrument"),
                "miss_type": near_miss.get("miss_type"),
                "delta_pct": near_miss.get("delta_pct"),
            })
        
        regime = record.get("regime_resolved")
        if regime:
            analysis["regime_distribution"][regime] += 1
        
        daily_bias = record.get("daily_bias")
        if daily_bias:
            analysis["bias_distribution"][daily_bias] += 1
    
    analysis["strategies_evaluated"] = sorted(list(analysis["strategies_evaluated"]))
    analysis["instruments_evaluated"] = sorted(list(analysis["instruments_evaluated"]))
    
    return analysis


def analyze_trade_selection_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze trade selection records"""
    analysis = {
        "total_selections": 0,
        "total_input_signals": 0,
        "total_output_signals": 0,
        "total_rejected": 0,
        "rejection_reasons": Counter(),
    }
    
    for record in records:
        if record.get("type") != "trade_selection":
            continue
        
        analysis["total_selections"] += 1
        input_count = record.get("input_signals_count", 0)
        output_count = record.get("output_signals_count", 0)
        analysis["total_input_signals"] += input_count
        analysis["total_output_signals"] += output_count
        analysis["total_rejected"] += (input_count - output_count)
        
        reasons = record.get("selection_reasons", [])
        for reason in reasons:
            analysis["rejection_reasons"][reason] += 1
    
    return analysis


def print_analysis(analysis: Dict[str, Any], selection_analysis: Dict[str, Any]):
    """Print formatted analysis"""
    print("=" * 80)
    print("STRATEGY TRIGGER PROBE ANALYSIS")
    print("=" * 80)
    print()
    
    # Evaluation Summary
    print("EVALUATION SUMMARY")
    print("-" * 80)
    print(f"Total Evaluations: {analysis['total_evaluations']}")
    print(f"Signals Generated: {analysis['signals_generated']}")
    print(f"Signals Blocked: {analysis['signals_blocked']}")
    if analysis['total_evaluations'] > 0:
        success_rate = (analysis['signals_generated'] / analysis['total_evaluations']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    print()
    
    # Strategies and Instruments
    print("STRATEGIES EVALUATED")
    print("-" * 80)
    for strategy in analysis['strategies_evaluated']:
        print(f"  - {strategy}")
    print()
    
    print("INSTRUMENTS EVALUATED")
    print("-" * 80)
    for instrument in analysis['instruments_evaluated']:
        print(f"  - {instrument}")
    print()
    
    # Exit Reasons
    print("EXIT REASONS")
    print("-" * 80)
    for reason, count in analysis['exit_reasons'].most_common(10):
        print(f"  {reason}: {count}")
    print()
    
    # Blocking Conditions
    print("BLOCKING CONDITIONS (First Failure)")
    print("-" * 80)
    if analysis['blocking_conditions']:
        for condition, count in analysis['blocking_conditions'].most_common(10):
            print(f"  {condition}: {count}")
    else:
        print("  (No blocking conditions recorded)")
    print()
    
    # Near Misses
    print("NEAR MISSES")
    print("-" * 80)
    if analysis['near_misses']:
        print(f"Total Near Misses: {len(analysis['near_misses'])}")
        for miss in analysis['near_misses'][:10]:
            print(f"  {miss['strategy_id']} / {miss['instrument']}: {miss['miss_type']} (delta: {miss['delta_pct']:.1f}%)")
    else:
        print("  (No near misses detected)")
    print()
    
    # Regime Distribution
    print("REGIME DISTRIBUTION")
    print("-" * 80)
    for regime, count in analysis['regime_distribution'].most_common():
        print(f"  {regime}: {count}")
    print()
    
    # Bias Distribution
    print("BIAS DISTRIBUTION (Daily)")
    print("-" * 80)
    for bias, count in analysis['bias_distribution'].most_common():
        print(f"  {bias}: {count}")
    print()
    
    # Trade Selection Summary
    print("TRADE SELECTION SUMMARY")
    print("-" * 80)
    print(f"Total Selection Cycles: {selection_analysis['total_selections']}")
    print(f"Total Input Signals: {selection_analysis['total_input_signals']}")
    print(f"Total Output Signals: {selection_analysis['total_output_signals']}")
    print(f"Total Rejected: {selection_analysis['total_rejected']}")
    if selection_analysis['total_input_signals'] > 0:
        rejection_rate = (selection_analysis['total_rejected'] / selection_analysis['total_input_signals']) * 100
        print(f"Rejection Rate: {rejection_rate:.1f}%")
    print()
    
    if selection_analysis['rejection_reasons']:
        print("REJECTION REASONS")
        print("-" * 80)
        for reason, count in selection_analysis['rejection_reasons'].most_common():
            print(f"  {reason}: {count}")
    print()


def verify_success_criteria(analysis: Dict[str, Any]) -> Dict[str, bool]:
    """Verify probe success criteria"""
    criteria = {
        "strategies_evaluated_gt_0": len(analysis['strategies_evaluated']) > 0,
        "first_block_reason_present": len(analysis['blocking_conditions']) > 0 or analysis['signals_generated'] > 0,
        "near_miss_records_optional": True,  # Optional, always pass
    }
    return criteria


def main():
    """Main verification function"""
    log_path = get_probe_log_path()
    
    if not log_path:
        print("ERROR: Probe log file not found")
        print(f"  Checked: {PROBE_LOG_PATH}")
        print(f"  Checked: {LOCAL_LOG_PATH}")
        print()
        print("The probe may not have run yet, or logging is disabled.")
        return 1
    
    print(f"Loading probe records from: {log_path}")
    print()
    
    # Load recent records (last 50 by default, or all if specified)
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Warning: Invalid limit '{sys.argv[1]}', loading all records")
    
    records = load_probe_records(log_path, limit=limit)
    
    if not records:
        print("No probe records found in log file.")
        print("The probe may not have run yet, or no strategy evaluations occurred.")
        return 1
    
    print(f"Loaded {len(records)} records")
    print()
    
    # Analyze records
    analysis = analyze_evaluation_records(records)
    selection_analysis = analyze_trade_selection_records(records)
    
    # Print analysis
    print_analysis(analysis, selection_analysis)
    
    # Verify success criteria
    print("SUCCESS CRITERIA VERIFICATION")
    print("-" * 80)
    criteria = verify_success_criteria(analysis)
    all_passed = True
    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {criterion}: {status}")
        if not passed:
            all_passed = False
    print()
    
    if all_passed:
        print("✅ All success criteria met")
        return 0
    else:
        print("❌ Some success criteria not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
