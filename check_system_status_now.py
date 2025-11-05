#!/usr/bin/env python3
"""
REAL-TIME SYSTEM STATUS CHECK
Quick diagnostic of current system state
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json

print("="*80)
print("🔍 REAL-TIME SYSTEM STATUS CHECK")
print("="*80)
print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
if Path('google-cloud-trading-system').exists():
    sys.path.insert(0, str(Path('google-cloud-trading-system')))

status = {
    'system_running': False,
    'scanner_available': False,
    'strategies_loaded': 0,
    'accounts_active': 0,
    'issues': [],
    'warnings': [],
    'info': []
}

# ============================================================================
# CHECK 1: System Processes
# ============================================================================
print("[1/8] Checking System Processes")
print("-"*80)

try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
    processes = result.stdout
    
    python_processes = [p for p in processes.split('\n') if 'python' in p.lower()]
    main_processes = [p for p in python_processes if 'main.py' in p or 'trading' in p.lower()]
    
    if main_processes:
        print(f"✓ Found {len(main_processes)} trading-related Python processes:")
        for proc in main_processes[:3]:  # Show first 3
            parts = proc.split()
            if len(parts) > 10:
                print(f"  • PID {parts[1]}: {parts[10][:50]}...")
        status['system_running'] = True
    else:
        print("⚠️  No trading system processes found")
        status['warnings'].append("No trading system processes running")
        
except Exception as e:
    print(f"⚠️  Could not check processes: {e}")

# ============================================================================
# CHECK 2: Scanner Status
# ============================================================================
print("\n[2/8] Checking Scanner Status")
print("-"*80)

try:
    sys.path.insert(0, 'google-cloud-trading-system/src')
    from core.simple_timer_scanner import get_simple_scanner
    
    scanner = get_simple_scanner()
    if scanner:
        print("✓ Scanner initialized")
        status['scanner_available'] = True
        
        if hasattr(scanner, 'strategies'):
            strategies_count = len(scanner.strategies) if scanner.strategies else 0
            print(f"  • Strategies loaded: {strategies_count}")
            status['strategies_loaded'] = strategies_count
            
            if strategies_count == 0:
                status['critical'].append("NO STRATEGIES LOADED - system cannot trade")
        
        if hasattr(scanner, 'accounts'):
            accounts_count = len(scanner.accounts) if scanner.accounts else 0
            print(f"  • Accounts configured: {accounts_count}")
            status['accounts_active'] = accounts_count
            
            if accounts_count == 0:
                status['issues'].append("NO ACCOUNTS CONFIGURED")
        
        if hasattr(scanner, 'is_running'):
            print(f"  • Scanner running: {scanner.is_running}")
        
        if hasattr(scanner, 'scan_count'):
            print(f"  • Scan count: {scanner.scan_count}")
    else:
        print("❌ Scanner not available")
        status['issues'].append("Scanner failed to initialize")
        
except ImportError as e:
    print(f"⚠️  Could not import scanner (may need dependencies): {e}")
except Exception as e:
    print(f"❌ Scanner check failed: {e}")
    status['issues'].append(f"Scanner check failed: {e}")

# ============================================================================
# CHECK 3: Accounts Configuration
# ============================================================================
print("\n[3/8] Checking Accounts Configuration")
print("-"*80)

try:
    import yaml
    accounts_path = Path('google-cloud-trading-system/accounts.yaml')
    
    if accounts_path.exists():
        with open(accounts_path, 'r') as f:
            config = yaml.safe_load(f)
        
        accounts = config.get('accounts', [])
        active = [acc for acc in accounts if acc.get('active', False)]
        
        print(f"✓ accounts.yaml found")
        print(f"  • Total accounts: {len(accounts)}")
        print(f"  • Active accounts: {len(active)}")
        
        if len(active) == 0:
            status['issues'].append("NO ACTIVE ACCOUNTS in accounts.yaml")
        else:
            print("\n  Active Accounts:")
            for acc in active[:5]:  # Show first 5
                name = acc.get('name', acc.get('display_name', 'Unknown'))
                strategy = acc.get('strategy', 'N/A')
                acc_id = acc.get('id', 'N/A')[-3:] if acc.get('id') else 'N/A'
                print(f"    • {name} ({acc_id}): {strategy}")
    else:
        print("❌ accounts.yaml not found")
        status['issues'].append("accounts.yaml missing")
        
except Exception as e:
    print(f"⚠️  Could not check accounts: {e}")

# ============================================================================
# CHECK 4: Environment Variables
# ============================================================================
print("\n[4/8] Checking Environment Variables")
print("-"*80)

env_vars = {
    'OANDA_API_KEY': os.getenv('OANDA_API_KEY'),
    'OANDA_ACCOUNT_ID': os.getenv('OANDA_ACCOUNT_ID') or os.getenv('PRIMARY_ACCOUNT'),
    'PRIMARY_ACCOUNT': os.getenv('PRIMARY_ACCOUNT'),
    'OANDA_ENVIRONMENT': os.getenv('OANDA_ENVIRONMENT', 'practice'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
}

for key, value in env_vars.items():
    if key == 'PRIMARY_ACCOUNT':
        continue  # Skip, already checked in OANDA_ACCOUNT_ID
    if value:
        if key == 'OANDA_API_KEY':
            print(f"✓ {key}: {value[:10]}...{value[-4:] if len(value) > 14 else '***'}")
        elif key in ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
            print(f"✓ {key}: ***SET***")
        else:
            print(f"✓ {key}: {value}")
    else:
        print(f"⚠️  {key}: NOT SET")
        if key == 'OANDA_API_KEY':
            status['issues'].append("OANDA_API_KEY not set")
        elif key == 'OANDA_ACCOUNT_ID':
            status['warnings'].append("OANDA_ACCOUNT_ID not set")

# ============================================================================
# CHECK 5: Service Files
# ============================================================================
print("\n[5/8] Checking Service Files")
print("-"*80)

service_files = [
    'automated_trading.service',
    'ai_trading.service',
    'google-cloud-trading-system/adaptive-trading-system.service'
]

for service_file in service_files:
    if Path(service_file).exists():
        print(f"✓ {Path(service_file).name}: Found")
    else:
        print(f"⚠️  {Path(service_file).name}: Not found")

# Check if systemd services are active
try:
    result = subprocess.run(['systemctl', 'is-active', 'automated_trading.service'], 
                           capture_output=True, text=True, timeout=3)
    if result.returncode == 0:
        print(f"  • automated_trading.service: {result.stdout.strip()}")
except Exception:
    pass  # systemctl may not be available

# ============================================================================
# CHECK 6: Recent Logs
# ============================================================================
print("\n[6/8] Checking Recent Log Activity")
print("-"*80)

log_files = [
    'logs/real_system_manual_fix.log',
    'logs/real_system_final.log',
    'google-cloud-trading-system/working_server.log'
]

signals_found = 0
trades_found = 0
errors_found = 0
last_scan_time = None

for log_path in log_files:
    log_file = Path(log_path)
    if log_file.exists():
        try:
            # Read last 500 lines
            with open(log_file, 'r') as f:
                lines = f.readlines()[-500:]
            
            for line in lines:
                line_lower = line.lower()
                
                if any(word in line_lower for word in ['signal generated', 'opportunity found', 'entry signal']):
                    signals_found += 1
                    if 'scan' in line_lower:
                        # Try to extract timestamp
                        if not last_scan_time:
                            last_scan_time = line[:50]
                
                if any(word in line_lower for word in ['trade executed', 'entered:', 'order placed']):
                    trades_found += 1
                
                if 'error' in line_lower or 'failed' in line_lower:
                    if 'price verification' not in line_lower:  # Skip spam
                        errors_found += 1
            
            print(f"✓ Analyzed {Path(log_path).name}: {len(lines)} lines")
            
        except Exception as e:
            print(f"⚠️  Could not read {log_path}: {e}")

print(f"\n  • Signals found: {signals_found}")
print(f"  • Trades found: {trades_found}")
print(f"  • Errors found: {errors_found}")

if last_scan_time:
    print(f"  • Last scan: {last_scan_time[:80]}")

if signals_found > 0 and trades_found == 0:
    status['issues'].append("Signals generated but NO trades executed")
elif signals_found == 0:
    status['warnings'].append("NO signals found in recent logs")

# ============================================================================
# CHECK 7: File Structure
# ============================================================================
print("\n[7/8] Checking Critical Files")
print("-"*80)

critical_files = {
    'main.py': 'google-cloud-trading-system/main.py',
    'scanner': 'google-cloud-trading-system/src/core/simple_timer_scanner.py',
    'order_manager': 'google-cloud-trading-system/src/core/order_manager.py',
    'dashboard': 'google-cloud-trading-system/src/dashboard/advanced_dashboard.py',
}

for name, path in critical_files.items():
    if Path(path).exists():
        print(f"✓ {name}: Found")
    else:
        print(f"❌ {name}: MISSING - {path}")
        status['issues'].append(f"{name} file missing")

# ============================================================================
# CHECK 8: Network Connectivity
# ============================================================================
print("\n[8/8] Checking Network Connectivity")
print("-"*80)

try:
    import socket
    socket.setdefaulttimeout(3)
    
    # Test OANDA API
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("api-fxpractice.oanda.com", 443))
        sock.close()
        print("✓ OANDA API (practice): Reachable")
    except Exception as e:
        print(f"⚠️  OANDA API (practice): Not reachable - {e}")
        status['warnings'].append("Cannot reach OANDA API")
        
except Exception as e:
    print(f"⚠️  Network check failed: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("📊 SYSTEM STATUS SUMMARY")
print("="*80)

if status['system_running']:
    print("✅ System: RUNNING")
else:
    print("⚠️  System: NOT RUNNING (or cannot detect)")

if status['scanner_available']:
    print(f"✅ Scanner: AVAILABLE ({status['strategies_loaded']} strategies, {status['accounts_active']} accounts)")
else:
    print("❌ Scanner: NOT AVAILABLE")

if status['issues']:
    print(f"\n❌ CRITICAL ISSUES ({len(status['issues'])}):")
    for issue in status['issues']:
        print(f"   • {issue}")

if status['warnings']:
    print(f"\n⚠️  WARNINGS ({len(status['warnings'])}):")
    for warning in status['warnings'][:5]:  # Show first 5
        print(f"   • {warning}")

print(f"\n📈 Recent Activity:")
print(f"   • Signals: {signals_found}")
print(f"   • Trades: {trades_found}")
print(f"   • Errors: {errors_found}")

# Overall status
if status['issues']:
    overall = "❌ NEEDS ATTENTION"
elif status['warnings']:
    overall = "⚠️  WARNINGS"
elif status['scanner_available'] and status['strategies_loaded'] > 0:
    overall = "✅ OPERATIONAL"
else:
    overall = "⚠️  UNKNOWN STATE"

print(f"\n🎯 Overall Status: {overall}")
print("="*80)

# Save status to file
status_file = Path('system_status_check.json')
with open(status_file, 'w') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'overall_status': overall,
        **status
    }, f, indent=2, default=str)

print(f"\n💾 Status saved to: {status_file}")
