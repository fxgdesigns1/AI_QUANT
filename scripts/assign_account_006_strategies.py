#!/usr/bin/env python3
"""
Assign Strategies to Account 006
Enables momentum and gold_scalping strategies for OANDA account 006.

This script assigns BOTH strategies to account 006.
The system will scan with both strategies, allowing account 006 to trade
with either momentum or gold_scalping signals.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.control_plane.config_store import ConfigStore
from src.control_plane.schema import StrategyAssignment, RuntimeConfig

# Configuration
ACCOUNT_PREFIX = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-")
ACCOUNT_006_SUFFIX = "006"
ACCOUNT_006_ID = f"{ACCOUNT_PREFIX}{ACCOUNT_006_SUFFIX}"

# Strategies to assign to account 006
STRATEGIES_FOR_006 = ["momentum", "gold_scalping"]

def main():
    print("=" * 60)
    print("ASSIGNING STRATEGIES TO ACCOUNT 006")
    print("=" * 60)
    print(f"Account ID: {ACCOUNT_006_ID}")
    print(f"Strategies: {', '.join(STRATEGIES_FOR_006)}")
    print()
    
    # Load current config
    config_store = ConfigStore()
    current_config = config_store.load()
    
    # Get existing assignments (if any)
    existing_assignments = current_config.strategy_assignments or []
    
    # Filter out any existing assignments for account 006
    # (We'll replace them with new multi-strategy assignments)
    filtered_assignments = [
        a for a in existing_assignments 
        if a.account_id != ACCOUNT_006_ID
    ]
    
    # Add new assignments for account 006 (one per strategy)
    for strategy_key in STRATEGIES_FOR_006:
        new_assignment = StrategyAssignment(
            account_id=ACCOUNT_006_ID,
            strategy_key=strategy_key,
            enabled=True
        )
        filtered_assignments.append(new_assignment)
    
    # Update config
    print(f"Current assignments: {len(existing_assignments)}")
    print(f"After update: {len(filtered_assignments)}")
    print()
    
    # Show all assignments
    print("Strategy Assignments:")
    for assignment in filtered_assignments:
        account_suffix = assignment.account_id[-3:] if len(assignment.account_id) >= 3 else assignment.account_id
        status = "✅ ENABLED" if assignment.enabled else "❌ DISABLED"
        print(f"  Account {account_suffix}: {assignment.strategy_key} ({status})")
    print()
    
    # Validate before saving
    current_config.strategy_assignments = filtered_assignments
    errors = current_config.validate()
    
    if errors:
        print("❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # Save config
    try:
        updated_config = config_store.save()
        print("✅ Config saved successfully!")
        print()
        print("Hot-reload: Runner will detect config change on next scan cycle")
        print("No restart required - changes take effect within 30 seconds")
        print()
        print("To verify:")
        print("  grep 'Strategy assignments:' /opt/ai-quant/logs/runner.log | tail -n 5")
        print("  grep 'Account 006' /opt/ai-quant/logs/runner.log | tail -n 10")
        return 0
    except Exception as e:
        print(f"❌ ERROR saving config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
