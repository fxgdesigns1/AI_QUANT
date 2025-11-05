#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM STATUS CHECK
Uses unified credential loader - NO FALSE ALARMS
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

print("="*80)
print("🔍 SYSTEM STATUS CHECK")
print("="*80)
print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
if Path('google-cloud-trading-system').exists():
    sys.path.insert(0, str(Path('google-cloud-trading-system')))
    sys.path.insert(0, str(Path('google-cloud-trading-system/src')))

status_summary = {
    'system_running': False,
    'credentials_loaded': False,
    'scanner_available': False,
    'strategies_loaded': 0,
    'accounts_configured': 0,
    'issues': [],
    'warnings': [],
    'working': []
}

# ============================================================================
# CHECK 1: Credentials (USING UNIFIED LOADER)
# ============================================================================
print("[1/7] Checking Credentials (Unified Loader)")
print("-"*80)

try:
    from core.unified_credential_loader import get_credential_status, ensure_credentials_loaded
    
    ensure_credentials_loaded()
    cred_status = get_credential_status()
    
    if cred_status['all_credentials_present']:
        print("✅ ALL CREDENTIALS LOADED")
        print(f"   • API Key: {cred_status['api_key_preview']}")
        print(f"   • Account ID: {cred_status['account_id']}")
        print(f"   • Environment: {cred_status['environment']}")
        status_summary['credentials_loaded'] = True
        status_summary['working'].append("Credentials loaded successfully")
    else:
        print("❌ CREDENTIALS MISSING")
        if not cred_status['api_key_loaded']:
            status_summary['issues'].append("OANDA_API_KEY not found")
        if not cred_status['account_id_loaded']:
            status_summary['issues'].append("OANDA_ACCOUNT_ID not found")
except Exception as e:
    print(f"⚠️  Credential check failed: {e}")
    status_summary['warnings'].append(f"Credential check error: {e}")

# ============================================================================
# CHECK 2: System Processes
# ============================================================================
print("\n[2/7] Checking System Processes")
print("-"*80)

try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
    processes = result.stdout
    
    python_processes = [p for p in processes.split('\n') if 'python' in p.lower()]
    main_processes = [p for p in python_processes if 'main.py' in p or 'trading' in p.lower()]
    
    if main_processes:
        print(f"✅ Found {len(main_processes)} trading-related processes")
        for proc in main_processes[:3]:
            parts = proc.split()
            if len(parts) > 10:
                print(f"   • PID {parts[1]}: {parts[10][:60]}...")
        status_summary['system_running'] = True
        status_summary['working'].append("System processes running")
    else:
        print("⚠️  No trading system processes found")
        status_summary['warnings'].append("No system processes detected")
except Exception as e:
    print(f"⚠️  Could not check processes: {e}")

# ============================================================================
# CHECK 3: Scanner Status
# ============================================================================
print("\n[3/7] Checking Scanner Status")
print("-"*80)

try:
    from core.simple_timer_scanner import get_simple_scanner
    
    scanner = get_simple_scanner()
    if scanner:
        print("✅ Scanner initialized")
        status_summary['scanner_available'] = True
        status_summary['working'].append("Scanner available")
        
        if hasattr(scanner, 'strategies'):
            strategies_count = len(scanner.strategies) if scanner.strategies else 0
            print(f"   • Strategies loaded: {strategies_count}")
            status_summary['strategies_loaded'] = strategies_count
            
            if strategies_count == 0:
                status_summary['issues'].append("NO STRATEGIES LOADED")
            else:
                status_summary['working'].append(f"{strategies_count} strategies loaded")
        
        if hasattr(scanner, 'accounts'):
            accounts_count = len(scanner.accounts) if scanner.accounts else 0
            print(f"   • Accounts configured: {accounts_count}")
            status_summary['accounts_configured'] = accounts_count
            
            if accounts_count == 0:
                status_summary['issues'].append("NO ACCOUNTS CONFIGURED")
            else:
                status_summary['working'].append(f"{accounts_count} accounts configured")
        
        if hasattr(scanner, 'is_running'):
            print(f"   • Scanner running: {scanner.is_running}")
        
        if hasattr(scanner, 'scan_count'):
            print(f"   • Total scans: {scanner.scan_count}")
    else:
        print("❌ Scanner not available")
        status_summary['issues'].append("Scanner failed to initialize")
        
except ImportError as e:
    print(f"⚠️  Scanner not available (missing dependencies): {str(e)[:60]}...")
    status_summary['warnings'].append("Scanner dependencies missing")
except Exception as e:
    print(f"❌ Scanner check failed: {str(e)[:60]}...")
    status_summary['issues'].append(f"Scanner error: {str(e)[:50]}")

# ============================================================================
# CHECK 4: Accounts Configuration
# ============================================================================
print("\n[4/7] Checking Accounts Configuration")
print("-"*80)

try:
    import yaml
    accounts_path = Path('google-cloud-trading-system/accounts.yaml')
    
    if accounts_path.exists():
        with open(accounts_path, 'r') as f:
            config = yaml.safe_load(f)
        
        accounts = config.get('accounts', [])
        active = [acc for acc in accounts if acc.get('active', False)]
        
        print(f"✅ accounts.yaml found")
        print(f"   • Total accounts: {len(accounts)}")
        print(f"   • Active accounts: {len(active)}")
        
        if len(active) == 0:
            status_summary['issues'].append("NO ACTIVE ACCOUNTS in accounts.yaml")
        else:
            status_summary['working'].append(f"{len(active)} active accounts in config")
            print("\n   Active Accounts:")
            for acc in active[:5]:
                name = acc.get('name', acc.get('display_name', 'Unknown'))
                strategy = acc.get('strategy', 'N/A')
                acc_id = acc.get('id', 'N/A')[-3:] if acc.get('id') else 'N/A'
                print(f"     • {name} ({acc_id}): {strategy}")
    else:
        print("⚠️  accounts.yaml not found (template exists)")
        status_summary['warnings'].append("accounts.yaml not found")
        
except Exception as e:
    print(f"⚠️  Could not check accounts: {str(e)[:60]}...")

# ============================================================================
# CHECK 5: Critical Files
# ============================================================================
print("\n[5/7] Checking Critical Files")
print("-"*80)

critical_files = {
    'main.py': 'google-cloud-trading-system/main.py',
    'scanner': 'google-cloud-trading-system/src/core/simple_timer_scanner.py',
    'order_manager': 'google-cloud-trading-system/src/core/order_manager.py',
    'credential_loader': 'google-cloud-trading-system/src/core/unified_credential_loader.py',
}

all_files_present = True
for name, path in critical_files.items():
    if Path(path).exists():
        print(f"✅ {name}: Found")
    else:
        print(f"❌ {name}: MISSING")
        all_files_present = False
        status_summary['issues'].append(f"{name} file missing")

if all_files_present:
    status_summary['working'].append("All critical files present")

# ============================================================================
# CHECK 6: Network Connectivity
# ============================================================================
print("\n[6/7] Checking Network Connectivity")
print("-"*80)

try:
    import socket
    socket.setdefaulttimeout(3)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("api-fxpractice.oanda.com", 443))
        sock.close()
        print("✅ OANDA API (practice): Reachable")
        status_summary['working'].append("Network connectivity OK")
    except Exception as e:
        print(f"⚠️  OANDA API: Not reachable - {str(e)[:40]}...")
        status_summary['warnings'].append("Cannot reach OANDA API")
        
except Exception as e:
    print(f"⚠️  Network check failed: {str(e)[:40]}...")

# ============================================================================
# CHECK 7: Recent Activity
# ============================================================================
print("\n[7/7] Checking Recent Activity")
print("-"*80)

log_files = [
    'logs/real_system_manual_fix.log',
    'logs/real_system_final.log',
    'google-cloud-trading-system/working_server.log'
]

signals_found = 0
trades_found = 0

for log_path in log_files:
    log_file = Path(log_path)
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-500:]
            
            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in ['signal generated', 'opportunity found']):
                    signals_found += 1
                if any(word in line_lower for word in ['trade executed', 'entered:', 'order placed']):
                    trades_found += 1
            
            print(f"✓ Analyzed {Path(log_path).name}")
        except Exception:
            pass

print(f"   • Recent signals: {signals_found}")
print(f"   • Recent trades: {trades_found}")

if signals_found > 0:
    status_summary['working'].append(f"{signals_found} recent signals found")
if trades_found > 0:
    status_summary['working'].append(f"{trades_found} recent trades found")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("📊 SYSTEM STATUS SUMMARY")
print("="*80)

# Overall status
if status_summary['credentials_loaded'] and status_summary['scanner_available']:
    if status_summary['strategies_loaded'] > 0:
        overall = "✅ OPERATIONAL"
    else:
        overall = "⚠️  CONFIGURED BUT NO STRATEGIES"
elif status_summary['credentials_loaded']:
    overall = "⚠️  CREDENTIALS OK BUT SCANNER NOT AVAILABLE"
elif len(status_summary['issues']) > 0:
    overall = "❌ ISSUES DETECTED"
else:
    overall = "⚠️  UNKNOWN STATE"

print(f"\n🎯 Overall Status: {overall}")

if status_summary['system_running']:
    print("✅ System: RUNNING")
else:
    print("⚠️  System: NOT RUNNING")

if status_summary['credentials_loaded']:
    print("✅ Credentials: LOADED")
else:
    print("❌ Credentials: MISSING")

if status_summary['scanner_available']:
    print(f"✅ Scanner: AVAILABLE ({status_summary['strategies_loaded']} strategies, {status_summary['accounts_configured']} accounts)")
else:
    print("❌ Scanner: NOT AVAILABLE")

if status_summary['working']:
    print(f"\n✅ Working ({len(status_summary['working'])}):")
    for item in status_summary['working'][:5]:
        print(f"   • {item}")

if status_summary['issues']:
    print(f"\n❌ Issues ({len(status_summary['issues'])}):")
    for issue in status_summary['issues']:
        print(f"   • {issue}")

if status_summary['warnings']:
    print(f"\n⚠️  Warnings ({len(status_summary['warnings'])}):")
    for warning in status_summary['warnings'][:5]:
        print(f"   • {warning}")

print("\n" + "="*80)
