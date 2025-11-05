#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM VALIDATION
Validates all trading systems are running and working correctly
"""
import os
import sys
import time
import requests
import subprocess
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_process(process_name):
    """Check if a process is running"""
    try:
        result = subprocess.run(['pgrep', '-f', process_name], 
                              capture_output=True, text=True)
        return len(result.stdout.strip()) > 0
    except:
        return False

def check_trade_execution():
    """Check if trades are being executed"""
    log_files = [
        '/workspace/logs/ai_trading.log',
        '/workspace/logs/automated_trading.log',
        '/workspace/logs/comprehensive_trading.log'
    ]
    
    trades_found = []
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if 'TRADE EXECUTED' in content:
                        trades_found.append(log_file)
            except:
                pass
    
    return len(trades_found) > 0

def check_telegram_connection():
    """Check Telegram bot connection"""
    token = os.getenv('TELEGRAM_TOKEN', '')
    if not token:
        return False, "Token not set"
    
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, "Connected"
        else:
            return False, f"API Error: {response.status_code}"
    except Exception as e:
        return False, f"Connection failed: {e}"

def check_api_connection():
    """Check OANDA API connection"""
    api_key = os.getenv('OANDA_API_KEY', '')
    account_id = os.getenv('OANDA_ACCOUNT_ID', '')
    
    if not api_key or not account_id:
        return False, "Credentials not set"
    
    try:
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Connected"
        else:
            return False, f"API Error: {response.status_code}"
    except Exception as e:
        return False, f"Connection failed: {e}"

def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}COMPREHENSIVE TRADING SYSTEM VALIDATION{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Check processes
    print(f"{YELLOW}📦 PROCESS STATUS:{RESET}")
    processes = {
        'AI Trading System': 'ai_trading_system.py',
        'Automated Trading System': 'automated_trading_system.py',
        'Comprehensive Trading System': 'comprehensive_trading_system'
    }
    
    for name, pattern in processes.items():
        is_running = check_process(pattern)
        status = f"{GREEN}✅ RUNNING{RESET}" if is_running else f"{RED}❌ NOT RUNNING{RESET}"
        print(f"  {name}: {status}")
        results[f'process_{name}'] = is_running
    
    print()
    
    # Check API connections
    print(f"{YELLOW}🔌 API CONNECTIONS:{RESET}")
    
    oanda_ok, oanda_msg = check_api_connection()
    status = f"{GREEN}✅ {oanda_msg}{RESET}" if oanda_ok else f"{RED}❌ {oanda_msg}{RESET}"
    print(f"  OANDA API: {status}")
    results['oanda_api'] = oanda_ok
    
    telegram_ok, telegram_msg = check_telegram_connection()
    status = f"{GREEN}✅ {telegram_msg}{RESET}" if telegram_ok else f"{YELLOW}⚠️ {telegram_msg}{RESET}"
    print(f"  Telegram Bot: {status}")
    results['telegram'] = telegram_ok
    
    print()
    
    # Check trade execution
    print(f"{YELLOW}🎯 TRADE EXECUTION:{RESET}")
    trades_executing = check_trade_execution()
    status = f"{GREEN}✅ TRADES EXECUTING{RESET}" if trades_executing else f"{YELLOW}⚠️ NO TRADES YET{RESET}"
    print(f"  Status: {status}")
    results['trades'] = trades_executing
    
    print()
    
    # Check logs
    print(f"{YELLOW}📋 LOG FILES:{RESET}")
    log_files = [
        ('AI Trading', '/workspace/logs/ai_trading.log'),
        ('Automated Trading', '/workspace/logs/automated_trading.log'),
        ('Comprehensive Trading', '/workspace/logs/comprehensive_trading.log')
    ]
    
    for name, log_path in log_files:
        exists = os.path.exists(log_path)
        size = os.path.getsize(log_path) if exists else 0
        status = f"{GREEN}✅ {size} bytes{RESET}" if exists else f"{RED}❌ NOT FOUND{RESET}"
        print(f"  {name}: {status}")
    
    print()
    
    # Summary
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}SUMMARY:{RESET}")
    
    all_critical = (
        results.get('process_AI Trading System', False) and
        results.get('process_Automated Trading System', False) and
        results.get('oanda_api', False)
    )
    
    if all_critical:
        print(f"{GREEN}✅ ALL CRITICAL SYSTEMS OPERATIONAL{RESET}")
        print(f"{GREEN}✅ Trading systems are running and connected{RESET}")
        if results.get('trades', False):
            print(f"{GREEN}✅ Trades are being executed{RESET}")
    else:
        print(f"{RED}❌ SOME CRITICAL SYSTEMS NOT OPERATIONAL{RESET}")
        if not results.get('process_AI Trading System', False):
            print(f"{RED}  • AI Trading System not running{RESET}")
        if not results.get('process_Automated Trading System', False):
            print(f"{RED}  • Automated Trading System not running{RESET}")
        if not results.get('oanda_api', False):
            print(f"{RED}  • OANDA API not connected{RESET}")
    
    if not results.get('telegram', False):
        print(f"{YELLOW}⚠️ Telegram bot connection issue (non-critical){RESET}")
    
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    return all_critical

if __name__ == "__main__":
    main()
