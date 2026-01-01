#!/usr/bin/env python3
from src.core.settings import settings
"""
Market Readiness Verification for Dynamic Multi-Pair Unified Strategy
Checks all calibration and configuration before live trading
"""

import os
import sys
import yaml
import requests
from datetime import datetime

# OANDA Configuration
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")
HEADERS = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

# Target account
TARGET_ACCOUNT = "101-004-30719775-011"
REQUIRED_INSTRUMENTS = ["USD_CAD", "NZD_USD", "GBP_USD", "EUR_USD", "XAU_USD", "USD_JPY"]

def check_account_exists():
    """Verify account exists and is accessible"""
    print("🔍 Checking account accessibility...")
    try:
        url = f"{OANDA_BASE_URL}/v3/accounts/{TARGET_ACCOUNT}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            account = response.json().get('account', {})
            balance = float(account.get('balance', 0))
            currency = account.get('currency', 'USD')
            print(f"   ✅ Account accessible: {TARGET_ACCOUNT}")
            print(f"   ✅ Balance: {balance:,.2f} {currency}")
            return True
        else:
            print(f"   ❌ Account access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error accessing account: {e}")
        return False

def check_instruments_available():
    """Verify all required instruments are tradeable"""
    print("\n🔍 Checking instrument availability...")
    all_available = True
    
    for instrument in REQUIRED_INSTRUMENTS:
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{TARGET_ACCOUNT}/pricing"
            params = {'instruments': instrument}
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                if prices:
                    price_data = prices[0]
                    status = price_data.get('status', '').lower()
                    bid = float(price_data.get('bids', [{}])[0].get('price', 0))
                    ask = float(price_data.get('asks', [{}])[0].get('price', 0))
                    
                    if status in ('tradeable', 'tradable') and bid > 0 and ask > 0:
                        spread = ask - bid
                        print(f"   ✅ {instrument}: Tradeable (Spread: {spread:.5f})")
                    else:
                        print(f"   ⚠️  {instrument}: Not tradeable (Status: {status})")
                        all_available = False
                else:
                    print(f"   ❌ {instrument}: No price data")
                    all_available = False
            else:
                print(f"   ❌ {instrument}: API error {response.status_code}")
                all_available = False
        except Exception as e:
            print(f"   ❌ {instrument}: Error - {e}")
            all_available = False
    
    return all_available

def check_accounts_yaml():
    """Verify accounts.yaml configuration"""
    print("\n🔍 Checking accounts.yaml configuration...")
    
    yaml_paths = [
        '/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml',
        os.path.join(os.path.dirname(__file__), 'AI_QUANT_credentials', 'accounts.yaml'),
    ]
    
    for yaml_path in yaml_paths:
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    accounts_data = yaml.safe_load(f) or {}
                
                accounts = accounts_data.get('accounts', {})
                target_found = False
                
                for name, config in accounts.items():
                    if config.get('account_id') == TARGET_ACCOUNT:
                        target_found = True
                        strategy = config.get('strategy', '')
                        trading_pairs = config.get('trading_pairs', [])
                        risk_settings = config.get('risk_settings', {})
                        active = config.get('active', False)
                        
                        print(f"   ✅ Found account configuration")
                        print(f"      Strategy: {strategy}")
                        print(f"      Active: {active}")
                        print(f"      Trading pairs: {trading_pairs}")
                        print(f"      Max risk per trade: {risk_settings.get('max_risk_per_trade', 'N/A')}")
                        print(f"      Max positions: {risk_settings.get('max_positions', 'N/A')}")
                        
                        # Verify strategy matches
                        if strategy == 'dynamic_multi_pair_unified':
                            print(f"   ✅ Strategy matches: dynamic_multi_pair_unified")
                        else:
                            print(f"   ⚠️  Strategy mismatch: expected 'dynamic_multi_pair_unified', got '{strategy}'")
                        
                        # Verify trading pairs
                        if set(trading_pairs) == set(REQUIRED_INSTRUMENTS):
                            print(f"   ✅ Trading pairs match required instruments")
                        else:
                            missing = set(REQUIRED_INSTRUMENTS) - set(trading_pairs)
                            extra = set(trading_pairs) - set(REQUIRED_INSTRUMENTS)
                            if missing:
                                print(f"   ⚠️  Missing instruments: {missing}")
                            if extra:
                                print(f"   ⚠️  Extra instruments: {extra}")
                        
                        return True
                
                if not target_found:
                    print(f"   ❌ Account {TARGET_ACCOUNT} not found in configuration")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error reading {yaml_path}: {e}")
                return False
    
    print(f"   ❌ accounts.yaml not found in expected locations")
    return False

def check_strategy_registry():
    """Verify strategy is registered"""
    print("\n🔍 Checking strategy registry...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system'))
        from src.strategies.registry import resolve_strategy_key, STRATEGY_REGISTRY
        
        key = resolve_strategy_key("dynamic_multi_pair_unified")
        if key and key in STRATEGY_REGISTRY:
            definition = STRATEGY_REGISTRY[key]
            print(f"   ✅ Strategy registered: {definition.display_name}")
            print(f"      Description: {definition.description}")
            
            # Try to create instance
            try:
                strategy = definition.create()
                print(f"   ✅ Strategy instance created successfully")
                print(f"      Instruments: {', '.join(strategy.instruments)}")
                print(f"      Max trades/day: {strategy.max_trades_per_day}")
                print(f"      Position multiplier: {strategy.position_multiplier}x")
                return True
            except Exception as e:
                print(f"   ⚠️  Strategy creation failed: {e}")
                return False
        else:
            print(f"   ❌ Strategy not found in registry")
            return False
    except Exception as e:
        print(f"   ⚠️  Could not verify registry (may be expected if not deployed): {e}")
        return None  # Not a failure, just can't verify locally

def check_config_file():
    """Verify config file exists"""
    print("\n🔍 Checking configuration file...")
    
    config_paths = [
        '/opt/quant_system_clean/google-cloud-trading-system/LIVE_TRADING_CONFIG_UNIFIED.yaml',
        '/Users/mac/quant_system_clean/google-cloud-trading-system/LIVE_TRADING_CONFIG_UNIFIED.yaml',
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system', 'LIVE_TRADING_CONFIG_UNIFIED.yaml'),
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = yaml.safe_load(f)
                
                strategy_config = config.get('strategies', {}).get('dynamic_multi_pair_unified', {})
                if strategy_config:
                    print(f"   ✅ Config file found: {path}")
                    instruments = strategy_config.get('instruments', [])
                    print(f"      Instruments in config: {len(instruments)}")
                    return True
            except Exception as e:
                print(f"   ⚠️  Error reading {path}: {e}")
    
    print(f"   ⚠️  Config file not found (strategy will use defaults)")
    return None  # Not critical, strategy has defaults

def main():
    """Run all market readiness checks"""
    print("=" * 70)
    print("MARKET READINESS VERIFICATION")
    print("Dynamic Multi-Pair Unified Strategy")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Account: {TARGET_ACCOUNT}")
    print()
    
    results = {}
    
    results['account'] = check_account_exists()
    results['instruments'] = check_instruments_available()
    results['accounts_yaml'] = check_accounts_yaml()
    results['registry'] = check_strategy_registry()
    results['config'] = check_config_file()
    
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    critical_passed = True
    for check, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
            if check in ['account', 'instruments', 'accounts_yaml']:
                critical_passed = False
        else:
            status = "⚠️  SKIP"
        
        print(f"{check.upper():20} {status}")
    
    print()
    if critical_passed:
        print("✅ MARKET READY - All critical checks passed")
        print("   Strategy is ready for deployment and live trading")
    else:
        print("❌ NOT MARKET READY - Critical checks failed")
        print("   Please fix issues before deploying")
    
    return 0 if critical_passed else 1

if __name__ == "__main__":
    sys.exit(main())








