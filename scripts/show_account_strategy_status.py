#!/usr/bin/env python3
"""
Show Current Account/Strategy Status
Displays what's actually running vs what's configured
"""

import sys
import os
sys.path.append(os.getcwd())

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

try:
    from working_trading_system import WorkingTradingSystem
    from src.control_plane.config_store import ConfigStore
    
    print("=== CURRENT SYSTEM STATUS ===\n")
    
    # Check Runtime Config
    config_store = ConfigStore()
    config = config_store.load()
    
    print("📋 Runtime Configuration:")
    print(f"   Active Strategy Key (Legacy): {config.active_strategy_key}")
    if config.strategy_assignments:
        print(f"   Strategy Assignments: {len(config.strategy_assignments)} configured")
        for a in config.strategy_assignments:
            status = "✅ ENABLED" if a.enabled else "❌ DISABLED"
            print(f"      Account {a.account_id[-3:]}: {a.strategy_key} ({status})")
    else:
        print(f"   Strategy Assignments: None (using legacy mode - only first account)")
    
    print(f"\n   Default Instruments: {', '.join(config.default_instruments)}")
    print(f"   Scan Interval: {config.scan_interval_seconds}s")
    print(f"   Max Daily Trades: {config.risk.max_daily_trades_per_account}")
    
    # Check System State
    system = WorkingTradingSystem()
    
    print(f"\n🔍 System Runtime State:")
    print(f"   Accounts Loaded: {len(system.account_ids_for_scanning)}")
    print(f"   Accounts: {[acc[-3:] for acc in system.account_ids_for_scanning]}")
    print(f"   Execution Enabled: {'✅ Yes' if system.execution_enabled else '❌ No'}")
    print(f"   Order Managers: {len(system.order_managers)}")
    
    print(f"\n📊 Expected Behavior:")
    if config.strategy_assignments:
        enabled = [a for a in config.strategy_assignments if a.enabled]
        print(f"   {len(enabled)} accounts should be actively trading:")
        for a in enabled:
            print(f"      Account {a.account_id[-3:]}: {a.strategy_key} on default instruments")
    else:
        if system.account_ids_for_scanning:
            first = system.account_ids_for_scanning[0]
            print(f"   LEGACY MODE: Only account {first[-3:]} runs {config.active_strategy_key}")
            print(f"   Other accounts ({len(system.account_ids_for_scanning)-1}) are NOT active")
    
    print(f"\n⚠️  Trade Execution Status:")
    if not system.execution_enabled:
        print(f"   ❌ Execution is DISABLED - signals only, no trades")
    else:
        print(f"   ✅ Execution is ENABLED - trades will execute if signals pass safety gates")
        print(f"   Safety Gates: Price sanity, daily limits, throttle limits, cooldowns")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
