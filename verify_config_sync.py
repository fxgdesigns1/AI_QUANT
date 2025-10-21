#!/usr/bin/env python3
"""
Verify Config Sync Tool
Checks if running configuration matches accounts.yaml
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src'))

from core.yaml_manager import get_yaml_manager
from core.candle_based_scanner import get_candle_scanner

def verify_sync():
    """Verify if scanner config matches YAML"""
    
    print("🔍 Checking Configuration Sync...")
    print("=" * 60)
    
    # Get YAML config
    yaml_mgr = get_yaml_manager()
    yaml_config = yaml_mgr.read_config()
    yaml_accounts = yaml_mgr.get_all_accounts()
    
    print(f"\n📄 accounts.yaml Configuration:")
    print(f"  • Total accounts: {len(yaml_accounts)}")
    print(f"  • Active accounts: {len([a for a in yaml_accounts if a.get('active')])}")
    
    for account in yaml_accounts:
        if account.get('active'):
            print(f"  • {account.get('display_name', account.get('name'))}: {account.get('strategy')} ({len(account.get('instruments', []))} instruments)")
    
    # Get scanner config
    try:
        scanner = get_candle_scanner()
        
        print(f"\n🔄 Scanner Running Configuration:")
        print(f"  • Loaded strategies: {len(scanner.strategies)}")
        print(f"  • Loaded accounts: {len(scanner.accounts)}")
        
        for strategy_name, account_id in scanner.accounts.items():
            strategy = scanner.strategies.get(strategy_name)
            if strategy:
                instruments = getattr(strategy, 'instruments', [])
                print(f"  • {strategy_name}: {len(instruments)} instruments")
        
        # Compare
        print(f"\n✅ Configuration Comparison:")
        
        yaml_strategies = set()
        for acc in yaml_accounts:
            if acc.get('active'):
                yaml_strategies.add(acc.get('strategy'))
        
        scanner_strategies = set(scanner.strategies.keys())
        
        if yaml_strategies == scanner_strategies:
            print("  ✅ Strategies MATCH")
        else:
            print("  ⚠️ Strategies DIFFER")
            print(f"     YAML has: {yaml_strategies}")
            print(f"     Scanner has: {scanner_strategies}")
            print(f"     → You need to restart scanner to sync!")
        
    except Exception as e:
        print(f"\n❌ Could not access scanner: {e}")
        print("  Scanner may not be running")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    verify_sync()



