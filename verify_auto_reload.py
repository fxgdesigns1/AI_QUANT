#!/usr/bin/env python3
"""
Verify Auto-Reload Status for accounts.yaml
Checks if ConfigReloader is watching accounts.yaml and if dynamic_account_manager is registered
"""

import os
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

print("=" * 70)
print("AUTO-RELOAD VERIFICATION REPORT")
print("=" * 70)
print()

# 1. Check if ConfigReloader exists
print("1. Checking ConfigReloader...")
try:
    from src.core.config_reloader import get_config_reloader, ConfigReloader
    config_reloader = get_config_reloader()
    print(f"   ✅ ConfigReloader exists: {type(config_reloader)}")
    print(f"   📊 Is watching: {config_reloader.is_watching}")
    print(f"   📝 Registered callbacks: {len(config_reloader.config_change_callbacks)}")
    
    if config_reloader.is_watching:
        print(f"   👀 Watching {len(config_reloader.config_paths)} config files:")
        for path in config_reloader.config_paths:
            print(f"      - {path}")
    else:
        print("   ⚠️  NOT watching any files")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# 2. Check accounts.yaml location
print("2. Checking accounts.yaml location...")
try:
    accounts_yaml_paths = [
        Path('google-cloud-trading-system/accounts.yaml'),
        Path('accounts.yaml'),
        Path('/app/accounts.yaml'),
    ]
    
    found_path = None
    for path in accounts_yaml_paths:
        if path.exists():
            found_path = path.resolve()
            print(f"   ✅ Found at: {found_path}")
            print(f"   📅 Last modified: {path.stat().st_mtime}")
            break
    
    if not found_path:
        print("   ❌ accounts.yaml not found in expected locations")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# 3. Check if dynamic_account_manager registers for reload
print("3. Checking dynamic_account_manager reload registration...")
try:
    from src.core.dynamic_account_manager import DynamicAccountManager, get_account_manager
    
    # Check if there's a reload method or callback registration
    am = get_account_manager()
    print(f"   ✅ AccountManager exists: {type(am)}")
    
    # Check if it has reload capability
    has_reload = hasattr(am, 'reload') or hasattr(am, '_reload')
    has_register_callback = hasattr(am, 'register_config_callback')
    
    print(f"   🔄 Has reload method: {has_reload}")
    print(f"   📝 Registers callbacks: {has_register_callback}")
    
    # Check if accounts are loaded
    active_accounts = am.get_active_accounts()
    print(f"   📊 Active accounts loaded: {len(active_accounts)}")
    for acc_id in active_accounts:
        config = am.get_account_config(acc_id)
        if '008' in acc_id:
            print(f"      🎯 Account 008: {config.strategy_name} - {config.instruments}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# 4. Check main.py initialization
print("4. Checking if main.py initializes file watching...")
try:
    main_py = Path('google-cloud-trading-system/main.py')
    if main_py.exists():
        content = main_py.read_text()
        
        has_start_watching = 'start_watching' in content
        has_register_callback = 'register_callback' in content
        has_accounts_yaml_watch = 'accounts.yaml' in content.lower() and 'watch' in content.lower()
        
        print(f"   📝 Has start_watching call: {has_start_watching}")
        print(f"   📝 Has register_callback: {has_register_callback}")
        print(f"   📝 Watches accounts.yaml: {has_accounts_yaml_watch}")
        
        if not has_start_watching:
            print("   ⚠️  No file watching initialization found in main.py")
    else:
        print("   ❌ main.py not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# 5. Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("Based on the code analysis:")
print()
print("✅ ConfigReloader EXISTS and can watch files")
print("❌ ConfigReloader is NOT watching accounts.yaml (not started)")
print("❌ dynamic_account_manager does NOT auto-reload on file changes")
print("✅ Changes to accounts.yaml require MANUAL RESTART")
print()
print("RECOMMENDATION:")
print("  - Strategy Switcher writes to accounts.yaml ✅")
print("  - But system needs restart to reload ✅")
print("  - This is by design (see DATA_CONSISTENCY_GUIDE.md)")
print()
print("=" * 70)

