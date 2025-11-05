#!/usr/bin/env python3
"""
Comprehensive System Validation
Validates all systems are running and executing trades
"""
import os
import sys
import time
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

# Set environment
TELEGRAM_TOKEN = "7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
TELEGRAM_CHAT_ID = "6100678501"
OANDA_API_KEY = "REMOVED_SECRET"
OANDA_ACCOUNT_ID = "101-004-30719775-008"

def check_processes() -> Dict[str, bool]:
    """Check if all processes are running"""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    stdout = result.stdout
    
    return {
        'AI Trading System': 'ai_trading_system.py' in stdout,
        'Automated Trading System': 'automated_trading_system.py' in stdout,
        'Dashboard': 'advanced_dashboard.py' in stdout,
    }

def check_dashboard() -> Tuple[bool, str]:
    """Check if dashboard is responding"""
    try:
        response = requests.get('http://localhost:8080/ready', timeout=5)
        if response.status_code == 200:
            return True, "Dashboard responding"
        else:
            return False, f"Dashboard returned {response.status_code}"
    except Exception as e:
        return False, f"Dashboard not responding: {str(e)}"

def check_telegram() -> Tuple[bool, str]:
    """Check Telegram connection"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        response = requests.get(url, timeout=5)
        if response.status_code == 200 and response.json().get('ok'):
            return True, "Telegram connected"
        else:
            return False, "Telegram authentication failed"
    except Exception as e:
        return False, f"Telegram error: {str(e)}"

def check_oanda() -> Tuple[bool, str]:
    """Check OANDA connection"""
    try:
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{OANDA_ACCOUNT_ID}"
        headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            account = response.json()['account']
            balance = account.get('balance', 'N/A')
            return True, f"OANDA connected - Balance: ${balance}"
        else:
            return False, f"OANDA error: {response.status_code}"
    except Exception as e:
        return False, f"OANDA error: {str(e)}"

def check_trades() -> Tuple[bool, str]:
    """Check if trades are being executed"""
    try:
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{OANDA_ACCOUNT_ID}/openTrades"
        headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            trades = response.json().get('trades', [])
            return True, f"{len(trades)} open trades"
        else:
            return False, f"Could not check trades: {response.status_code}"
    except Exception as e:
        return False, f"Trade check error: {str(e)}"

def check_logs() -> Dict[str, str]:
    """Check recent log activity"""
    logs = {}
    
    log_files = {
        'AI Trading': '/tmp/ai_trading.log',
        'Automated Trading': '/tmp/automated_trading.log',
        'Dashboard': '/tmp/dashboard.log',
    }
    
    for name, log_file in log_files.items():
        try:
            if os.path.exists(log_file):
                result = subprocess.run(
                    ['tail', '-1', log_file],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    last_line = result.stdout.strip()
                    if last_line:
                        logs[name] = last_line[:100]  # First 100 chars
                    else:
                        logs[name] = "Empty log"
                else:
                    logs[name] = "Could not read"
            else:
                logs[name] = "Log file not found"
        except Exception as e:
            logs[name] = f"Error: {str(e)[:50]}"
    
    return logs

def send_validation_report(results: Dict):
    """Send validation report to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        # Format results
        report_lines = ["🔍 SYSTEM VALIDATION REPORT\n"]
        
        # Processes
        report_lines.append("📊 Processes:")
        for name, status in results['processes'].items():
            icon = "✅" if status else "❌"
            report_lines.append(f"  {icon} {name}")
        
        # Services
        report_lines.append("\n🔌 Services:")
        for name, (status, msg) in results['services'].items():
            icon = "✅" if status else "❌"
            report_lines.append(f"  {icon} {name}: {msg}")
        
        # Trades
        report_lines.append("\n💰 Trading:")
        trade_status, trade_msg = results['trades']
        icon = "✅" if trade_status else "⚠️"
        report_lines.append(f"  {icon} {trade_msg}")
        
        report_lines.append(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        message = "\n".join(report_lines)
        
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        requests.post(url, json=payload, timeout=10)
        print("✅ Validation report sent to Telegram")
    except Exception as e:
        print(f"⚠️ Failed to send report: {e}")

def main():
    """Run comprehensive validation"""
    print("="*80)
    print("COMPREHENSIVE SYSTEM VALIDATION")
    print("="*80)
    print()
    
    results = {
        'processes': {},
        'services': {},
        'trades': (False, ""),
        'logs': {}
    }
    
    # Check processes
    print("📊 Checking processes...")
    results['processes'] = check_processes()
    for name, status in results['processes'].items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    
    print()
    
    # Check services
    print("🔌 Checking services...")
    results['services']['Dashboard'] = check_dashboard()
    results['services']['Telegram'] = check_telegram()
    results['services']['OANDA'] = check_oanda()
    
    for name, (status, msg) in results['services'].items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {msg}")
    
    print()
    
    # Check trades
    print("💰 Checking trades...")
    results['trades'] = check_trades()
    status, msg = results['trades']
    icon = "✅" if status else "⚠️"
    print(f"  {icon} {msg}")
    
    print()
    
    # Check logs
    print("📝 Recent log activity...")
    results['logs'] = check_logs()
    for name, log_line in results['logs'].items():
        print(f"  {name}: {log_line[:80]}")
    
    print()
    print("="*80)
    
    # Send report
    send_validation_report(results)
    
    # Summary
    all_processes_ok = all(results['processes'].values())
    all_services_ok = all(status for _, (status, _) in results['services'].items())
    
    if all_processes_ok and all_services_ok:
        print("✅ ALL SYSTEMS OPERATIONAL!")
        return True
    else:
        print("⚠️ SOME SYSTEMS NEED ATTENTION")
        return False

if __name__ == "__main__":
    main()
