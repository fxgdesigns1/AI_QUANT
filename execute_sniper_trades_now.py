#!/usr/bin/env python3
"""Execute sniper trades based on Trump DNA roadmaps"""

import sys
sys.path.insert(0, 'google-cloud-trading-system/src')

from core.trump_dna_scanner import get_trump_dna_scanner
from datetime import datetime

# Account mapping
ACCOUNTS = {
    'XAU_USD_Gold': '101-004-30719775-009',
    'GBP_USD_Rank1': '101-004-30719775-008',
    'GBP_USD_Rank2': '101-004-30719775-007',
    'GBP_USD_Rank3': '101-004-30719775-006',
    'EUR_USD_UltraStrict': '101-004-30719775-010',
    'USD_JPY_Momentum': '101-004-30719775-011',
}

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
            if 'Gold' in signal['strategy']:
                account_id = '101-004-30719775-009'
            elif 'Rank1' in signal['strategy'] or 'Rank_1' in signal['strategy']:
                account_id = '101-004-30719775-008'
            elif 'Rank2' in signal['strategy'] or 'Rank_2' in signal['strategy']:
                account_id = '101-004-30719775-007'
            elif 'Rank3' in signal['strategy'] or 'Rank_3' in signal['strategy']:
                account_id = '101-004-30719775-006'
            elif 'Ultra' in signal['strategy']:
                account_id = '101-004-30719775-010'
            elif 'Momentum' in signal['strategy']:
                account_id = '101-004-30719775-011'
            
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



