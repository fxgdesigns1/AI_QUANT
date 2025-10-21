#!/usr/bin/env python3
"""
SCANNER CONFIGURATION VERIFIER
Ensures scanner strategies match accounts.yaml EXACTLY
Run this BEFORE every deployment to catch mismatches
"""

import sys
import yaml
from pathlib import Path

def verify_scanner_matches_config():
    """Verify scanner code matches accounts.yaml configuration"""
    
    print("=" * 70)
    print("SCANNER CONFIGURATION VERIFICATION")
    print("=" * 70)
    
    errors = []
    warnings = []
    
    # 1. Load accounts.yaml
    try:
        with open('accounts.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"❌ Failed to load accounts.yaml: {e}")
        return errors, warnings
    
    accounts = config.get('accounts', [])
    strategies_registry = config.get('strategies', {})
    
    print(f"\n📋 Found {len(accounts)} accounts in accounts.yaml")
    print(f"📋 Found {len(strategies_registry)} strategies in registry")
    
    # 2. Read scanner file
    scanner_file = Path('src/core/candle_based_scanner.py')
    try:
        scanner_code = scanner_file.read_text()
    except Exception as e:
        errors.append(f"❌ Failed to read scanner file: {e}")
        return errors, warnings
    
    # 3. Check each account's strategy is imported
    print("\n" + "=" * 70)
    print("CHECKING STRATEGY IMPORTS")
    print("=" * 70)
    
    required_imports = set()
    for account in accounts:
        if not account.get('active', False):
            continue
        
        strategy_id = account.get('strategy')
        account_id = account.get('id')
        
        if not strategy_id:
            warnings.append(f"⚠️  Account {account_id} has no strategy defined")
            continue
        
        strategy_info = strategies_registry.get(strategy_id)
        if not strategy_info:
            errors.append(f"❌ Account {account_id} uses strategy '{strategy_id}' but it's not in registry!")
            continue
        
        module = strategy_info.get('module')
        function = strategy_info.get('function')
        
        if not module or not function:
            errors.append(f"❌ Strategy '{strategy_id}' missing module or function in registry")
            continue
        
        required_imports.add((module, function, strategy_id))
    
    # 4. Check imports exist in scanner
    for module, function, strategy_id in required_imports:
        import_line = f"from {module} import {function}"
        
        # Check both single import and multi-import on same line
        if import_line in scanner_code or (f"from {module} import" in scanner_code and function in scanner_code):
            print(f"✅ {strategy_id}: {function} imported from {module}")
        else:
            errors.append(f"❌ MISSING IMPORT: {import_line} (for strategy '{strategy_id}')")
    
    # 5. Check for OLD/UNUSED imports that shouldn't be there
    print("\n" + "=" * 70)
    print("CHECKING FOR OLD/UNUSED IMPORTS")
    print("=" * 70)
    
    old_strategies = [
        'aud_usd_5m_high_return',
        'eur_usd_5m_safe',
        'multi_strategy_portfolio',
        'gold_trump_week_strategy',
        'xau_usd_5m_gold_high_return',
    ]
    
    for old_strategy in old_strategies:
        if f"from src.strategies.{old_strategy}" in scanner_code:
            errors.append(f"❌ OLD IMPORT FOUND: {old_strategy} (should be removed!)")
        else:
            print(f"✅ No old import: {old_strategy}")
    
    # 6. Check account mapping in scanner
    print("\n" + "=" * 70)
    print("CHECKING ACCOUNT MAPPINGS")
    print("=" * 70)
    
    for account in accounts:
        if not account.get('active', False):
            continue
        
        account_id = account.get('id')
        strategy_id = account.get('strategy')
        
        # Look for account ID in scanner code
        if account_id in scanner_code:
            print(f"✅ Account {account_id[-3:]} ({strategy_id}) found in scanner")
        else:
            warnings.append(f"⚠️  Account {account_id} not found in scanner code")
    
    # 7. Print summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if errors:
        print(f"\n❌ ERRORS FOUND: {len(errors)}")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("\n✅ ALL CHECKS PASSED - Scanner matches accounts.yaml!")
    elif not errors:
        print("\n✅ No errors, only warnings - Deployment OK")
    else:
        print("\n❌ DEPLOYMENT BLOCKED - Fix errors first!")
    
    print("=" * 70)
    
    return errors, warnings


if __name__ == "__main__":
    errors, warnings = verify_scanner_matches_config()
    
    # Exit with error code if problems found
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)

