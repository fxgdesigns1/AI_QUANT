#!/usr/bin/env python3
"""
LIFECYCLE PROBE
---------------
Probes the full trade lifecycle for all configured accounts/strategies.
Verifies:
1. Configuration Loading
2. Dependency Resolution (Outlook, Regime)
3. Gatekeeper Logic (Simulated)
4. Strategy Readiness

Does NOT execute trades. Read-only probe.
"""

import sys
import os
import logging
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

# Add workspace root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("lifecycle_probe")

def probe_lifecycle():
    print(f"=== 🕵️ LIFECYCLE PROBE STARTED at {datetime.now(timezone.utc).isoformat()} ===")
    
    # 1. Initialize System
    print("\n--- PHASE 1: System Initialization ---")
    try:
        from working_trading_system import WorkingTradingSystem
        # We assume env is set up or defaults will apply. 
        # Ideally we'd source .env if needed, but WorkingTradingSystem handles some of that.
        
        # Patch execution to prevent accidents, just in case
        WorkingTradingSystem.scan_and_execute = MagicMock(side_effect=RuntimeError("SAFETY: Exec called in probe!"))
        
        system = WorkingTradingSystem()
        print("✅ WorkingTradingSystem initialized")
        
    except Exception as e:
        print(f"❌ CRITICAL: Failed to init system: {e}")
        return

    # 2. Get Assignments
    print("\n--- PHASE 2: Configuration & Assignments ---")
    assignments = []
    if system._strategy_assignments:
        assignments = [a for a in system._strategy_assignments if a.enabled]
        print(f"Found {len(assignments)} enabled assignments:")
        for a in assignments:
            print(f"  • Account {a.account_id[-3:]}: {a.strategy_key}")
    else:
        print("⚠️ No strategy assignments found (legacy mode or config error)")
        # Fallback to scanning accounts if available
        for acc in system.account_ids_for_scanning:
            assignments.append(MagicMock(account_id=acc, strategy_key=system._active_strategy_key))
            print(f"  • Account {acc[-3:]}: {system._active_strategy_key} (Legacy)")

    # 3. Probe Each Account
    print("\n--- PHASE 3: Gate & Strategy Probe ---")
    
    results = {}
    
    for assignment in assignments:
        acc_id = assignment.account_id
        strat_key = assignment.strategy_key
        short_id = acc_id[-3:]
        print(f"\n🔎 Probing Account {short_id} ({strat_key})...")
        
        status = {"account": short_id, "strategy": strat_key, "blockers": [], "warnings": []}
        
        # A. Strategy Resolution
        strategy = system._get_strategy_by_key(strat_key)
        if not strategy:
            print(f"  ❌ FAIL: Strategy class not found for key '{strat_key}'")
            status["blockers"].append("Strategy class missing")
            results[acc_id] = status
            continue
        
        print(f"  ✅ Strategy Class: {strategy.__class__.__name__}")
        
        # B. Dependency Check (for 006 / SessionExecution)
        if strat_key == "session_execution" or hasattr(strategy, "outlook_engine"):
            if getattr(strategy, "outlook_engine", None):
                print("  ✅ Dependency: OutlookEngine loaded")
            else:
                print("  ❌ FAIL: OutlookEngine MISSING")
                status["blockers"].append("OutlookEngine missing")
                
            if getattr(strategy, "regime_detector", None):
                print("  ✅ Dependency: RegimeDetector loaded")
            else:
                print("  ❌ FAIL: RegimeDetector MISSING")
                status["blockers"].append("RegimeDetector missing")
        
        # C. Gatekeeper Check (SessionRegimeAligned)
        # We simulate a "perfect" signal to see if the gate allows it
        # We need to mock market data and news
        
        if system.session_regime_gate:
            print("  🛡️ Testing Gatekeeper (SessionRegimeAligned)...")
            
            # Mock Data
            mock_price = MagicMock()
            mock_price.mid = 2000.0 if "gold" in strat_key else 1.1000
            mock_price.ask = mock_price.mid + 0.0001
            mock_price.bid = mock_price.mid - 0.0001
            
            # Use 'gold' or 'eur_usd' based on strategy key
            instrument = "XAU_USD" if "gold" in strat_key or "xau" in strat_key else "EUR_USD"
            mock_market_data = {instrument: mock_price}
            
            # Test 1: Normal conditions
            mock_news_normal = {"state": "normal", "is_embargo": False}
            
            # Test 2: Embargo Active
            mock_news_embargo = {"state": "embargo", "is_embargo": True, "embargo_triggers": ["TEST_TRIGGER"]}
            
            try:
                # We need to pass a timestamp that IS in session to test logic
                # London session is 6-12 UTC. Let's pick 09:00 UTC.
                mock_time = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
                
                # --- TEST A: EMBARGO ACTIVE ---
                print("  🧪 Test A: Embargo Logic...")
                allowed_embargo = system.session_regime_gate.should_allow_trade(
                    symbol=instrument,
                    market_data=mock_market_data,
                    news_context=mock_news_embargo,
                    timestamp_utc=mock_time
                )
                if not allowed_embargo:
                    print("  ✅ Embargo Test: PASSED (Trade Blocked)")
                else:
                    print("  ❌ Embargo Test: FAILED (Trade Allowed during Embargo!)")
                    status["blockers"].append("Embargo logic failed - Trade allowed during embargo")

                # --- TEST B: NORMAL ---
                print("  🧪 Test B: Normal Logic...")
                # Check gate
                allowed = system.session_regime_gate.should_allow_trade(
                    symbol=instrument,
                    market_data=mock_market_data,
                    news_context=mock_news_normal,
                    timestamp_utc=mock_time
                )
                
                # --- LONDON READINESS REPORT ---
                readiness_path = "logs/LONDON_SESSION_READINESS.md"
                with open(readiness_path, "w") as rf:
                    rf.write(f"# London Session Readiness Probe\n")
                    rf.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n")
                    rf.write(f"## Simulation Details\n")
                    rf.write(f"- Simulated Time: {mock_time.isoformat()}\n")
                    rf.write(f"- Instrument: {instrument}\n")
                    rf.write(f"- News State: Normal\n\n")
                    rf.write(f"## Gate Decision\n")
                    rf.write(f"- Allowed: **{allowed}**\n")
                    rf.write(f"- Reason: Check audit log (mocked run)\n")
                    
                    if allowed:
                         rf.write("\n✅ **READY FOR LONDON EXECUTION**\n")
                    else:
                         rf.write("\n⚠️ **NOT READY** - Trade blocked by gate logic.\n")
                         rf.write("Possible reasons:\n")
                         rf.write("- Roadmap misaligned (Daily/Weekly bias mismatch)\n")
                         rf.write("- Regime UNKNOWN (requires candles)\n")
                         rf.write("- Policy score too low\n")
                
                print(f"  📄 London readiness report written to {readiness_path}")

                if allowed:
                    print("  ✅ Gate Test: ALLOWED (Simulated London Session)")
                else:
                    print("  ⚠️ Gate Test: BLOCKED (Check Audit Log for Reason)")
                    # This might be expected if regime is not TRENDING or Roadmap not aligned
                    # We accept this as "Working Correctly" but note it
                    status["warnings"].append("Gate blocked trade in simulation (likely regime/roadmap alignment)")

                    
            except Exception as e:
                print(f"  ❌ Gate Test Error: {e}")
                status["blockers"].append(f"Gate error: {e}")
        else:
            print("  ℹ️ No Gatekeeper active (Legacy/Simple Mode)")

        # D. Execution Readiness
        if not system.execution_enabled:
             print("  ⚠️ Execution: DISABLED globally")
             status["blockers"].append("Global Execution Disabled")
        else:
             print("  ✅ Execution: ENABLED globally")

        results[acc_id] = status

    # 4. Generate Report
    print("\n--- PHASE 4: Report Generation ---")
    report_path = "logs/PROBE_REPORT.md"
    with open(report_path, "w") as f:
        f.write(f"# System Probe Report - {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("## Executive Summary\n")
        
        blockers_total = sum(len(r["blockers"]) for r in results.values())
        if blockers_total == 0:
            f.write("✅ **SYSTEM HEALTHY**. No blocking errors detected.\n")
        else:
            f.write(f"❌ **SYSTEM ISSUES DETECTED**. Found {blockers_total} blocking issues.\n")
            
        f.write("\n## Account Details\n")
        for acc_id, res in results.items():
            icon = "✅" if not res["blockers"] else "❌"
            f.write(f"### {icon} Account {res['account']} ({res['strategy']})\n")
            if res["blockers"]:
                for b in res["blockers"]:
                    f.write(f"- 🛑 **BLOCKER**: {b}\n")
            if res["warnings"]:
                for w in res["warnings"]:
                    f.write(f"- ⚠️ WARNING: {w}\n")
            if not res["blockers"] and not res["warnings"]:
                f.write("- Status: Fully Operational\n")
            f.write("\n")
            
    print(f"📄 Report written to {report_path}")
    print(open(report_path).read())

if __name__ == "__main__":
    probe_lifecycle()
