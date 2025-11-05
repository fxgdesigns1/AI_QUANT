#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM DIAGNOSTIC - Find Why No Trades Execute
Diagnoses: Signal generation, execution chain, strategy switching, startup issues
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
if Path('google-cloud-trading-system').exists():
    sys.path.insert(0, str(Path('google-cloud-trading-system')))

print("="*80)
print("🔍 COMPREHENSIVE SYSTEM DIAGNOSTIC")
print("="*80)
print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Results storage
DIAGNOSTIC_RESULTS = {
    'critical_issues': [],
    'warnings': [],
    'info': [],
    'recommendations': []
}

def add_issue(severity: str, message: str):
    """Add diagnostic issue"""
    if severity == 'critical':
        DIAGNOSTIC_RESULTS['critical_issues'].append(message)
        print(f"❌ CRITICAL: {message}")
    elif severity == 'warning':
        DIAGNOSTIC_RESULTS['warnings'].append(message)
        print(f"⚠️  WARNING: {message}")
    else:
        DIAGNOSTIC_RESULTS['info'].append(message)
        print(f"ℹ️  INFO: {message}")

# ============================================================================
# TEST 1: Environment & Credentials
# ============================================================================
print("[TEST 1/12] Checking Environment & Credentials")
print("-"*80)

try:
    from dotenv import load_dotenv
    
    # Try multiple env file locations
    env_locations = [
        'google-cloud-trading-system/oanda_config.env',
        'google-cloud-trading-system/.env',
        '.env',
        'oanda_config.env'
    ]
    
    env_loaded = False
    for env_path in env_locations:
        if Path(env_path).exists():
            load_dotenv(env_path)
            env_loaded = True
            print(f"✓ Loaded environment from: {env_path}")
            break
    
    if not env_loaded:
        add_issue('warning', 'No .env file found - using system environment variables')
    
    api_key = os.getenv('OANDA_API_KEY')
    primary_account = os.getenv('PRIMARY_ACCOUNT') or os.getenv('OANDA_ACCOUNT_ID')
    environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
    
    if api_key:
        print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    else:
        add_issue('critical', 'OANDA_API_KEY not found - trades cannot execute')
    
    if primary_account:
        print(f"✓ Primary Account: {primary_account}")
    else:
        add_issue('critical', 'PRIMARY_ACCOUNT/OANDA_ACCOUNT_ID not found')
    
    print(f"✓ Environment: {environment}")
    
except Exception as e:
    add_issue('critical', f'Failed to load credentials: {e}')

# ============================================================================
# TEST 2: System Files & Structure
# ============================================================================
print("\n[TEST 2/12] Checking System Files & Structure")
print("-"*80)

critical_files = {
    'main.py': 'google-cloud-trading-system/main.py',
    'accounts.yaml': 'google-cloud-trading-system/accounts.yaml',
    'scanner': 'google-cloud-trading-system/src/core/simple_timer_scanner.py',
    'order_manager': 'google-cloud-trading-system/src/core/order_manager.py',
    'dashboard_manager': 'google-cloud-trading-system/src/core/dashboard_manager.py'
}

for name, path in critical_files.items():
    if Path(path).exists():
        print(f"✓ {name}: Found")
    else:
        add_issue('critical', f'{name} missing: {path}')

# ============================================================================
# TEST 3: Accounts Configuration
# ============================================================================
print("\n[TEST 3/12] Checking Accounts Configuration")
print("-"*80)

try:
    import yaml
    accounts_path = Path('google-cloud-trading-system/accounts.yaml')
    
    if accounts_path.exists():
        with open(accounts_path, 'r') as f:
            accounts_config = yaml.safe_load(f)
        
        accounts = accounts_config.get('accounts', [])
        active_accounts = [acc for acc in accounts if acc.get('active', False)]
        
        print(f"✓ Total accounts configured: {len(accounts)}")
        print(f"✓ Active accounts: {len(active_accounts)}")
        
        if len(active_accounts) == 0:
            add_issue('critical', 'NO ACTIVE ACCOUNTS - system will not trade')
        
        # Check strategy assignments
        strategies_found = {}
        for acc in active_accounts:
            strategy = acc.get('strategy', 'N/A')
            strategies_found[strategy] = strategies_found.get(strategy, 0) + 1
            print(f"  • {acc.get('name', 'Unknown')}: {strategy} ({'active' if acc.get('active') else 'inactive'})")
        
        print(f"✓ Strategies in use: {list(strategies_found.keys())}")
        
    else:
        add_issue('critical', 'accounts.yaml not found')
        
except Exception as e:
    add_issue('critical', f'Failed to read accounts.yaml: {e}')

# ============================================================================
# TEST 4: Scanner Initialization
# ============================================================================
print("\n[TEST 4/12] Testing Scanner Initialization")
print("-"*80)

try:
    sys.path.insert(0, 'google-cloud-trading-system/src')
    from core.simple_timer_scanner import get_simple_scanner
    
    scanner = get_simple_scanner()
    if scanner:
        print("✓ Scanner initialized successfully")
        
        # Check scanner state
        if hasattr(scanner, 'is_running'):
            print(f"  • Scanner running: {scanner.is_running}")
        if hasattr(scanner, 'accounts'):
            print(f"  • Accounts configured: {len(scanner.accounts) if scanner.accounts else 0}")
        if hasattr(scanner, 'strategies'):
            print(f"  • Strategies loaded: {len(scanner.strategies) if scanner.strategies else 0}")
        
        # Check if scanner can run
        if hasattr(scanner, '_run_scan'):
            print("✓ Scanner has _run_scan method")
        else:
            add_issue('critical', 'Scanner missing _run_scan method')
            
    else:
        add_issue('critical', 'Scanner failed to initialize')
        
except Exception as e:
    add_issue('critical', f'Scanner initialization failed: {e}')
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 5: Strategy Loading & Signal Generation
# ============================================================================
print("\n[TEST 5/12] Testing Strategy Loading & Signal Generation")
print("-"*80)

try:
    from core.oanda_client import OandaClient
    
    if api_key and primary_account:
        client = OandaClient(api_key=api_key, account_id=primary_account)
        
        # Test price fetching
        prices = client.get_current_prices(['EUR_USD', 'GBP_USD'])
        if prices:
            print(f"✓ Can fetch prices: {len(prices)} instruments")
        else:
            add_issue('critical', 'Cannot fetch prices - signals cannot be generated')
        
        # Test strategy imports
        strategy_modules = [
            'momentum_trading',
            'gold_scalping',
            'breakout_strategy',
            'scalping_strategy'
        ]
        
        strategies_loaded = 0
        for strategy_name in strategy_modules:
            try:
                module = __import__(f'strategies.{strategy_name}', fromlist=[''])
                if hasattr(module, 'MomentumTradingStrategy') or hasattr(module, 'GoldScalpingStrategy') or hasattr(module, 'BreakoutStrategy'):
                    strategies_loaded += 1
                    print(f"✓ Strategy {strategy_name} can be imported")
            except Exception as e:
                add_issue('warning', f'Strategy {strategy_name} import failed: {e}')
        
        if strategies_loaded == 0:
            add_issue('critical', 'No strategies can be imported')
        
        # Test signal generation
        try:
            from strategies.momentum_trading import MomentumTradingStrategy
            strategy = MomentumTradingStrategy(api_key=api_key, account_id=primary_account)
            
            if hasattr(strategy, 'generate_signals'):
                signals = strategy.generate_signals('EUR_USD')
                print(f"✓ Strategy can generate signals: {len(signals) if signals else 0} signals")
            else:
                add_issue('critical', 'Strategy missing generate_signals method')
                
        except Exception as e:
            add_issue('warning', f'Signal generation test failed: {e}')
            
    else:
        add_issue('warning', 'Skipping strategy test - missing credentials')
        
except Exception as e:
    add_issue('critical', f'Strategy loading failed: {e}')
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 6: Order Manager & Execution Chain
# ============================================================================
print("\n[TEST 6/12] Testing Order Manager & Execution Chain")
print("-"*80)

try:
    from core.order_manager import OrderManager
    from core.dynamic_account_manager import get_account_manager
    
    account_manager = get_account_manager()
    if account_manager:
        print("✓ Account manager initialized")
        
        active_accounts = account_manager.get_active_accounts()
        print(f"✓ Active accounts from manager: {len(active_accounts)}")
        
        if len(active_accounts) == 0:
            add_issue('critical', 'Account manager reports 0 active accounts')
        
        # Check order manager
        if hasattr(account_manager, 'order_manager'):
            order_mgr = account_manager.order_manager
            print("✓ Order manager available")
            
            if hasattr(order_mgr, 'execute_trade'):
                print("✓ execute_trade method exists")
            else:
                add_issue('critical', 'Order manager missing execute_trade method')
        else:
            add_issue('critical', 'Account manager missing order_manager')
            
    else:
        add_issue('critical', 'Account manager failed to initialize')
        
except Exception as e:
    add_issue('critical', f'Order manager test failed: {e}')
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 7: Dashboard Manager & Signal Execution
# ============================================================================
print("\n[TEST 7/12] Testing Dashboard Manager & Signal Execution")
print("-"*80)

try:
    from core.dashboard_manager import get_dashboard_manager
    
    dashboard_mgr = get_dashboard_manager()
    if dashboard_mgr:
        print("✓ Dashboard manager initialized")
        
        # Check initialization status
        if hasattr(dashboard_mgr, '_initialized'):
            print(f"  • Initialized: {dashboard_mgr._initialized}")
            if not dashboard_mgr._initialized:
                add_issue('warning', 'Dashboard manager not fully initialized')
        
        # Check execute method
        if hasattr(dashboard_mgr, 'execute_trading_signals'):
            print("✓ execute_trading_signals method exists")
        else:
            add_issue('critical', 'Dashboard manager missing execute_trading_signals method')
        
        # Check scanner reference
        if hasattr(dashboard_mgr, 'scanner'):
            print("✓ Dashboard manager has scanner reference")
            if dashboard_mgr.scanner is None:
                add_issue('critical', 'Dashboard manager scanner is None')
        else:
            add_issue('warning', 'Dashboard manager missing scanner reference')
            
    else:
        add_issue('critical', 'Dashboard manager failed to initialize')
        
except Exception as e:
    add_issue('critical', f'Dashboard manager test failed: {e}')
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 8: Trading Enablement & Flags
# ============================================================================
print("\n[TEST 8/12] Checking Trading Enablement & Flags")
print("-"*80)

trading_flags = {
    'MOCK_TRADING': os.getenv('MOCK_TRADING', 'False'),
    'DEVELOPMENT_MODE': os.getenv('DEVELOPMENT_MODE', 'False'),
    'FORCED_TRADING_MODE': os.getenv('FORCED_TRADING_MODE', 'disabled'),
    'TRADING_ENABLED': os.getenv('TRADING_ENABLED', 'true'),
}

for flag, value in trading_flags.items():
    print(f"  • {flag}: {value}")
    
    if flag == 'MOCK_TRADING' and value.lower() == 'true':
        add_issue('warning', 'MOCK_TRADING enabled - no real trades will execute')
    if flag == 'DEVELOPMENT_MODE' and value.lower() == 'true':
        add_issue('warning', 'DEVELOPMENT_MODE enabled - may limit trading')
    if flag == 'FORCED_TRADING_MODE' and value.lower() != 'enabled':
        add_issue('info', 'FORCED_TRADING_MODE disabled - system uses normal criteria')

# ============================================================================
# TEST 9: Systemd Service Status
# ============================================================================
print("\n[TEST 9/12] Checking Systemd Service Status")
print("-"*80)

service_files = [
    'automated_trading.service',
    'ai_trading.service',
    'google-cloud-trading-system/adaptive-trading-system.service'
]

for service_file in service_files:
    if Path(service_file).exists():
        print(f"✓ Service file found: {service_file}")
        
        # Check service content
        try:
            with open(service_file, 'r') as f:
                content = f.read()
                
            if 'ExecStart' in content:
                exec_start = [line for line in content.split('\n') if 'ExecStart' in line]
                if exec_start:
                    print(f"  • ExecStart: {exec_start[0].strip()}")
                    
                    # Check if file exists
                    script_path = exec_start[0].split('=')[-1].strip() if '=' in exec_start[0] else ''
                    if script_path and not Path(script_path).exists():
                        add_issue('critical', f'Service script not found: {script_path}')
        except Exception as e:
            add_issue('warning', f'Could not read service file {service_file}: {e}')
    else:
        add_issue('info', f'Service file not found: {service_file} (may not be deployed)')

# ============================================================================
# TEST 10: Strategy Switching Logic
# ============================================================================
print("\n[TEST 10/12] Checking Strategy Switching Logic")
print("-"*80)

try:
    # Check graceful_restart module
    graceful_restart_path = Path('google-cloud-trading-system/src/core/graceful_restart.py')
    if graceful_restart_path.exists():
        print("✓ graceful_restart.py found")
        
        with open(graceful_restart_path, 'r') as f:
            content = f.read()
            
        if 'switch_strategy' in content:
            print("✓ switch_strategy function found")
        else:
            add_issue('warning', 'switch_strategy function not found in graceful_restart')
            
        if 'reload_config' in content:
            print("✓ reload_config function found")
        else:
            add_issue('warning', 'reload_config function not found')
    else:
        add_issue('warning', 'graceful_restart.py not found')
        
    # Check if accounts.yaml is writable (for strategy switching)
    accounts_path = Path('google-cloud-trading-system/accounts.yaml')
    if accounts_path.exists():
        if os.access(accounts_path, os.W_OK):
            print("✓ accounts.yaml is writable (strategy switching possible)")
        else:
            add_issue('warning', 'accounts.yaml not writable - strategy switching may fail')
            
except Exception as e:
    add_issue('warning', f'Strategy switching check failed: {e}')

# ============================================================================
# TEST 11: Startup Performance & Initialization
# ============================================================================
print("\n[TEST 11/12] Checking Startup Performance Issues")
print("-"*80)

# Check for blocking imports
blocking_imports = [
    'google-cloud-trading-system/main.py',
    'automated_trading_system.py',
    'ai_trading_system.py'
]

for file_path in blocking_imports:
    if Path(file_path).exists():
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for heavy imports at module level
            heavy_patterns = [
                'import requests',
                'from flask import',
                'import yaml',
                'import pandas',
                'import numpy'
            ]
            
            heavy_imports_found = []
            for pattern in heavy_patterns:
                if pattern in content:
                    # Check if it's at module level (not in function)
                    lines = content.split('\n')
                    for i, line in enumerate(lines[:50]):  # Check first 50 lines
                        if pattern in line and not line.strip().startswith('#'):
                            heavy_imports_found.append(pattern)
                            break
            
            if heavy_imports_found:
                print(f"  • {Path(file_path).name}: Heavy imports detected (may slow startup)")
                
            # Check for database connections at startup
            if 'sqlite' in content.lower() or 'database' in content.lower():
                db_patterns = ['connect', 'create_engine', 'Session']
                if any(pattern in content for pattern in db_patterns):
                    add_issue('info', f'{Path(file_path).name}: Database connections at startup (may slow boot)')
                    
        except Exception as e:
            add_issue('warning', f'Could not analyze {file_path}: {e}')

# ============================================================================
# TEST 12: Log Analysis - Recent Signals & Executions
# ============================================================================
print("\n[TEST 12/12] Analyzing Recent Logs")
print("-"*80)

log_files = [
    'logs/real_system_manual_fix.log',
    'logs/real_system_final.log',
    'google-cloud-trading-system/working_server.log'
]

signals_found = 0
executions_found = 0
errors_found = []

for log_path in log_files:
    log_file = Path(log_path)
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-1000:]  # Last 1000 lines
                
            for line in lines:
                line_lower = line.lower()
                
                if any(word in line_lower for word in ['signal generated', 'opportunity found', 'entry signal']):
                    signals_found += 1
                    
                if any(word in line_lower for word in ['trade executed', 'order placed', 'executing trade']):
                    executions_found += 1
                    
                if 'error' in line_lower or 'failed' in line_lower:
                    if 'price' not in line_lower and 'verification' not in line_lower:  # Skip spam
                        errors_found.append(line.strip()[:150])
                        
            print(f"✓ Analyzed {log_path}: {len(lines)} lines")
            
        except Exception as e:
            add_issue('info', f'Could not read {log_path}: {e}')

print(f"  • Signals found in logs: {signals_found}")
print(f"  • Executions found in logs: {executions_found}")

if signals_found > 0 and executions_found == 0:
    add_issue('critical', 'SIGNALS GENERATED BUT NO EXECUTIONS - execution chain broken')
elif signals_found == 0:
    add_issue('critical', 'NO SIGNALS GENERATED - strategy logic may be too strict or broken')
elif executions_found > 0:
    print("✓ Recent executions found in logs")

if errors_found:
    print(f"  • Recent errors: {len(errors_found)}")
    for error in errors_found[:5]:  # Show first 5
        print(f"    - {error}")

# ============================================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================================
print("\n" + "="*80)
print("📊 DIAGNOSTIC SUMMARY")
print("="*80)

print(f"\n❌ Critical Issues: {len(DIAGNOSTIC_RESULTS['critical_issues'])}")
for issue in DIAGNOSTIC_RESULTS['critical_issues']:
    print(f"   • {issue}")

print(f"\n⚠️  Warnings: {len(DIAGNOSTIC_RESULTS['warnings'])}")
for issue in DIAGNOSTIC_RESULTS['warnings'][:5]:  # Show first 5
    print(f"   • {issue}")

# Generate recommendations
if len(DIAGNOSTIC_RESULTS['critical_issues']) > 0:
    print("\n💡 CRITICAL FIXES NEEDED:")
    print("   1. Fix all critical issues above")
    print("   2. Verify credentials are loaded correctly")
    print("   3. Ensure at least one account is active")
    print("   4. Check scanner initialization in main.py")
    print("   5. Verify order manager is connected to execution chain")

if signals_found > 0 and executions_found == 0:
    DIAGNOSTIC_RESULTS['recommendations'].append(
        "SIGNALS → EXECUTION GAP: Check execute_trading_signals() in dashboard_manager.py"
    )
    DIAGNOSTIC_RESULTS['recommendations'].append(
        "Verify signals are passed to order_manager.execute_trade()"
    )

if signals_found == 0:
    DIAGNOSTIC_RESULTS['recommendations'].append(
        "NO SIGNALS: Check strategy criteria - may be too strict"
    )
    DIAGNOSTIC_RESULTS['recommendations'].append(
        "Verify market conditions meet strategy requirements"
    )
    DIAGNOSTIC_RESULTS['recommendations'].append(
        "Check if trading_enabled flag is True"
    )

print("\n💡 Recommendations:")
for rec in DIAGNOSTIC_RESULTS['recommendations']:
    print(f"   • {rec}")

# Save results
results_file = Path('diagnostic_results.json')
with open(results_file, 'w') as f:
    json.dump(DIAGNOSTIC_RESULTS, f, indent=2, default=str)

print(f"\n✅ Diagnostic complete - results saved to {results_file}")
print("="*80)
