#!/usr/bin/env python3
"""
Force immediate market scan and signal generation
"""
import os
import sys
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.oanda_client import OandaClient
from src.core.simple_timer_scanner import SimpleTimerScanner

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    print("="*80)
    print("🔍 FORCING IMMEDIATE MARKET SCAN - ALL STRATEGIES")
    print("="*80)
    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S London')}")
    print()
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('oanda_config.env')
    
    # Get all account IDs
    accounts = [
        ("101-004-30719775-002", "All-Weather 70% WR"),
        ("101-004-30719775-003", "Momentum V2"),
        ("101-004-30719775-004", "Ultra Strict V2"),
        ("101-004-30719775-005", "75% WR Champion"),
        ("101-004-30719775-006", "Strategy #3"),
        ("101-004-30719775-007", "Strategy #2"),
        ("101-004-30719775-008", "Strategy #1"),
        ("101-004-30719775-009", "Gold Scalping"),
        ("101-004-30719775-010", "Ultra Strict Fx"),
        ("101-004-30719775-011", "Momentum Multi-Pair"),
    ]
    
    total_signals = 0
    
    for account_id, name in accounts:
        try:
            print(f"\n{'='*80}")
            print(f"📊 Scanning: {name} ({account_id[-3:]})")
            print(f"{'='*80}")
            
            # Initialize scanner for this account
            oanda = OandaClient(account_id=account_id)
            scanner = SimpleTimerScanner(oanda_client=oanda)
            
            # Run scan
            signals = scanner.scan_for_quality_signals()
            
            if signals:
                print(f"\n✅ {len(signals)} SIGNALS FOUND!")
                for i, signal in enumerate(signals, 1):
                    print(f"\n🎯 SIGNAL #{i}:")
                    print(f"   Instrument: {signal.get('instrument')}")
                    print(f"   Direction: {signal.get('direction')}")
                    print(f"   Entry: {signal.get('entry_price'):.5f}")
                    print(f"   SL: {signal.get('stop_loss'):.5f}")
                    print(f"   TP: {signal.get('take_profit'):.5f}")
                    print(f"   Quality: {signal.get('quality_score', 0):.1f}/100")
                    print(f"   Strategy: {signal.get('strategy_name', 'Unknown')}")
                
                total_signals += len(signals)
            else:
                print(f"   ⚠️  No signals found (criteria not met)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"📈 SCAN COMPLETE")
    print(f"{'='*80}")
    print(f"Total signals found: {total_signals}")
    print(f"Accounts scanned: {len(accounts)}")
    
    if total_signals == 0:
        print("\n⚠️  NO SIGNALS - Market conditions don't meet strategy criteria")
        print("   Possible reasons:")
        print("   • Quality score threshold too high (70+)")
        print("   • Time gap requirements (15min minimum)")
        print("   • No strong trends detected")
        print("   • Risk limits already hit")
        print()
        print("💡 TIP: Wait for next scheduled scan or adjust criteria")
    
    return total_signals

if __name__ == "__main__":
    total = main()
    sys.exit(0 if total > 0 else 1)

