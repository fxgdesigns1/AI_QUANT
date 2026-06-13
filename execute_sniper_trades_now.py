#!/usr/bin/env python3
"""Execute sniper trades based on Trump DNA roadmaps"""

import sys
sys.path.insert(0, 'google-cloud-trading-system/src')

from core.trump_dna_scanner import get_trump_dna_scanner
from datetime import datetime

# Account mapping must be explicit; do not invent lanes.
# Lane 010 is manual_only/protected and must not be targeted unless explicitly overridden.
import os
ACCOUNT_ID_PREFIX = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-").strip()
ACCOUNT_SUFFIX_ALLOWLIST = [s.strip() for s in os.getenv("ACCOUNT_SUFFIX_ALLOWLIST", "").split(",") if s.strip()]
ALLOW_LANE_010_TESTS = os.getenv("ALLOW_LANE_010_TESTS", "false").lower() == "true"

if not ACCOUNT_SUFFIX_ALLOWLIST:
    raise RuntimeError("ACCOUNT_SUFFIX_ALLOWLIST is required to run this script (e.g., '011').")
if ("010" in ACCOUNT_SUFFIX_ALLOWLIST) and (not ALLOW_LANE_010_TESTS):
    raise RuntimeError("Refusing to target protected lane 010. Set ALLOW_LANE_010_TESTS=true to override explicitly.")

ACCOUNTS = {f"lane_{suffix}": f"{ACCOUNT_ID_PREFIX}{suffix}" for suffix in ACCOUNT_SUFFIX_ALLOWLIST}

def main():
    print("=" * 80)
    print("🎯 TRUMP DNA SNIPER SCANNER - FINDING OPPORTUNITIES")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S London')}")
    print("=" * 80)
    print()
    
    # Initialize scanner
    scanner = get_trump_dna_scanner()
    
    # Scan for sniper entries
    print("🔍 Scanning all pairs for sniper entry zones...")
    print()
    
    signals = scanner.scan_for_sniper_entries()
    
    if not signals:
        print("⚠️  No sniper entries at current prices")
        print("   Waiting for price to reach entry zones...")
        print()
        print("📊 Current zones being watched:")
        
        for plan_key, plan in scanner.planner.weekly_plans.items():
            print(f"\n{plan.pair} - {plan.strategy_name}:")
            for zone in plan.entry_zones:
                emoji = "🟢" if zone['action'] == 'BUY' else "🔴"
                if 'XAU' in plan.pair:
                    print(f"   {emoji} ${zone['level']:.2f} ({zone['type']}) → {zone['action']}")
                else:
                    print(f"   {emoji} {zone['level']:.5f} ({zone['type']}) → {zone['action']}")
    
    else:
        print(f"🎯 FOUND {len(signals)} SNIPER ENTRY SIGNALS!")
        print()
        
        for idx, signal in enumerate(signals, 1):
            print(f"{idx}. {signal['pair']} - {signal['strategy']}")
            print(f"   Action: {signal['action']} @ {signal['entry_price']}")
            print(f"   Zone: {signal['zone_type']} at {signal['entry_zone']}")
            print(f"   SL: {signal['stop_loss']} | TP: {signal['take_profit']}")
            print(f"   Max Hold: {signal['max_hold_hours']} hours")
            print(f"   Reason: {signal['reason']}")
            print()
        
        # Execute trades
        print("=" * 80)
        print("📤 EXECUTING TRADES...")
        print("=" * 80)
        print()
        
        executed = 0
        failed = 0
        
        for signal in signals:
            # Get account ID
            plan_key = f"{signal['pair']}_{signal['strategy'].replace(' ', '_').replace('#', '')}"
            
            account_id = None
            # Use first allowed lane by default; do not infer lanes from strategy labels.
            account_id = f"{ACCOUNT_ID_PREFIX}{ACCOUNT_SUFFIX_ALLOWLIST[0]}"
            
            if not account_id:
                print(f"❌ No account found for {signal['strategy']}")
                failed += 1
                continue
            
            print(f"Executing: {signal['pair']} on {signal['strategy']} ({account_id[-3:]})...")
            
            success = scanner.execute_signal(signal, account_id)
            
            if success:
                print(f"   ✅ EXECUTED!")
                executed += 1
            else:
                print(f"   ❌ FAILED")
                failed += 1
            print()
        
        print("=" * 80)
        print(f"📊 EXECUTION SUMMARY")
        print("=" * 80)
        print(f"✅ Executed: {executed}/{len(signals)}")
        print(f"❌ Failed: {failed}/{len(signals)}")
        print()
    
    print("=" * 80)
    print("✅ SCAN COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()



