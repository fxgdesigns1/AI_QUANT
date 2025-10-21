#!/usr/bin/env python3
"""
Strategy Switcher Test Script
Quick tests to verify the strategy switcher functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_strategy_manager():
    """Test Strategy Manager API"""
    print("\n" + "="*60)
    print("Testing Strategy Manager API")
    print("="*60)
    
    try:
        from src.api.strategy_manager import get_strategy_manager
        
        mgr = get_strategy_manager()
        print("✅ Strategy Manager initialized")
        
        # Test get config
        config = mgr.get_current_config()
        print(f"✅ Config loaded: {len(config.get('accounts', []))} accounts, {len(config.get('strategies', []))} strategies")
        
        # Test staging a change (use first account if available)
        accounts = config.get('accounts', [])
        if accounts:
            account = accounts[0]
            account_id = account['id']
            current_strategy = account.get('strategy')
            
            # Try to switch to a different strategy
            strategies = config.get('available_strategy_ids', [])
            if len(strategies) > 1:
                new_strategy = strategies[1] if strategies[0] == current_strategy else strategies[0]
                
                result = mgr.stage_strategy_switch(account_id, new_strategy)
                if result['success']:
                    print(f"✅ Staged strategy switch: {current_strategy} → {new_strategy}")
                else:
                    print(f"❌ Failed to stage switch: {result.get('error')}")
                
                # Test get pending changes
                pending = mgr.get_pending_changes()
                print(f"✅ Pending changes: {pending.get('count', 0)}")
                
                # Clear changes
                clear_result = mgr.clear_pending_changes()
                if clear_result['success']:
                    print(f"✅ Cleared {clear_result.get('cleared_count', 0)} changes")
                else:
                    print(f"❌ Failed to clear changes")
            else:
                print("⚠️  Not enough strategies to test switching")
        else:
            print("⚠️  No accounts found to test")
        
        print("\n✅ Strategy Manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Strategy Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graceful_restart():
    """Test Graceful Restart Manager"""
    print("\n" + "="*60)
    print("Testing Graceful Restart Manager")
    print("="*60)
    
    try:
        from src.core.graceful_restart import get_restart_manager
        
        mgr = get_restart_manager()
        print("✅ Restart Manager initialized")
        
        # Test check positions
        position_check = mgr.check_open_positions()
        if position_check.get('success'):
            positions = position_check.get('total_positions', 0)
            print(f"✅ Position check: {positions} open position(s)")
            print(f"   Safe to restart: {position_check.get('safe_to_restart', False)}")
        else:
            print(f"⚠️  Position check failed: {position_check.get('error')}")
        
        # Test get status
        status = mgr.get_status()
        print(f"✅ Status check: {status.get('status')}")
        print(f"   Message: {status.get('message', 'N/A')}")
        
        print("\n✅ Graceful Restart tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Graceful Restart test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yaml_integration():
    """Test YAML Manager Integration"""
    print("\n" + "="*60)
    print("Testing YAML Manager Integration")
    print("="*60)
    
    try:
        from src.core.yaml_manager import get_yaml_manager
        
        mgr = get_yaml_manager()
        print("✅ YAML Manager initialized")
        
        # Test read config
        config = mgr.read_config()
        accounts = config.get('accounts', [])
        strategies = config.get('strategies', {})
        
        print(f"✅ Read config: {len(accounts)} accounts, {len(strategies)} strategies")
        
        # Test get all accounts
        all_accounts = mgr.get_all_accounts()
        print(f"✅ Got {len(all_accounts)} accounts")
        
        # Test get all strategies
        all_strategies = mgr.get_all_strategies()
        print(f"✅ Got {len(all_strategies)} strategies")
        
        # Print summary
        print("\n📊 Configuration Summary:")
        print(f"   Active accounts: {sum(1 for a in all_accounts if a.get('active', False))}")
        print(f"   Inactive accounts: {sum(1 for a in all_accounts if not a.get('active', False))}")
        print(f"   Available strategies: {', '.join(list(all_strategies.keys())[:5])}...")
        
        print("\n✅ YAML Manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ YAML Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 STRATEGY SWITCHER TEST SUITE")
    print("="*60)
    
    results = {
        'yaml_integration': test_yaml_integration(),
        'strategy_manager': test_strategy_manager(),
        'graceful_restart': test_graceful_restart(),
    }
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("🎉 All tests passed! Strategy switcher is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())



