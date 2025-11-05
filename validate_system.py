#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM VALIDATION
Validates all systems are running and configured correctly
"""
import os
import sys
import time
import requests
import subprocess
from datetime import datetime

# Set environment
os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
os.environ['OANDA_ACCOUNT_ID'] = "101-004-30719775-008"
os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"

def check_process_running(name_pattern):
    """Check if a process is running"""
    try:
        result = subprocess.run(['pgrep', '-f', name_pattern], 
                              capture_output=True, text=True)
        return len(result.stdout.strip()) > 0
    except:
        return False

def test_telegram():
    """Test Telegram connection"""
    try:
        token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, "✅ Telegram bot is active"
        else:
            return False, f"❌ Telegram API error: {response.status_code}"
    except Exception as e:
        return False, f"❌ Telegram test failed: {e}"

def test_oanda():
    """Test OANDA API connection"""
    try:
        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            account = response.json()['account']
            return True, f"✅ OANDA connected - Balance: ${float(account['balance']):.2f}"
        else:
            return False, f"❌ OANDA API error: {response.status_code}"
    except Exception as e:
        return False, f"❌ OANDA test failed: {e}"

def test_dashboard():
    """Test dashboard is accessible"""
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        if response.status_code == 200:
            return True, "✅ Dashboard is running"
        else:
            return False, f"⚠️ Dashboard returned: {response.status_code}"
    except:
        return False, "⚠️ Dashboard not accessible (may not be started)"

def send_validation_report():
    """Send validation report to Telegram"""
    try:
        token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        report = f"""🤖 SYSTEM VALIDATION REPORT
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 SYSTEM STATUS:
"""
        
        # Check processes
        systems = {
            'Automated Trading': 'automated_trading_system.py',
            'AI Trading': 'ai_trading_system.py',
            'Dashboard': 'advanced_dashboard.py'
        }
        
        for name, pattern in systems.items():
            if check_process_running(pattern):
                report += f"✅ {name}: RUNNING\n"
            else:
                report += f"❌ {name}: NOT RUNNING\n"
        
        report += "\n🔗 CONNECTIONS:\n"
        
        # Test Telegram
        tel_ok, tel_msg = test_telegram()
        report += f"{tel_msg}\n"
        
        # Test OANDA
        oanda_ok, oanda_msg = test_oanda()
        report += f"{oanda_msg}\n"
        
        # Test Dashboard
        dash_ok, dash_msg = test_dashboard()
        report += f"{dash_msg}\n"
        
        # Send report
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': report}
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Validation report sent to Telegram")
        else:
            print(f"⚠️ Failed to send report: {response.status_code}")
        
        return report
        
    except Exception as e:
        print(f"❌ Failed to send validation report: {e}")
        return ""

def main():
    print("🔍 VALIDATING TRADING SYSTEM")
    print("=" * 50)
    
    # Check processes
    print("\n📊 Checking Processes:")
    systems = {
        'Automated Trading': 'automated_trading_system.py',
        'AI Trading': 'ai_trading_system.py',
        'Dashboard': 'advanced_dashboard.py'
    }
    
    all_running = True
    for name, pattern in systems.items():
        running = check_process_running(pattern)
        status = "✅ RUNNING" if running else "❌ NOT RUNNING"
        print(f"  {status}: {name}")
        if not running:
            all_running = False
    
    # Test connections
    print("\n🔗 Testing Connections:")
    
    tel_ok, tel_msg = test_telegram()
    print(f"  {tel_msg}")
    
    oanda_ok, oanda_msg = test_oanda()
    print(f"  {oanda_msg}")
    
    dash_ok, dash_msg = test_dashboard()
    print(f"  {dash_msg}")
    
    # Summary
    print("\n" + "=" * 50)
    if all_running and tel_ok and oanda_ok:
        print("✅ SYSTEM VALIDATION: PASSED")
    else:
        print("⚠️ SYSTEM VALIDATION: ISSUES FOUND")
    
    # Send report
    print("\n📱 Sending validation report to Telegram...")
    report = send_validation_report()
    
    print("\n" + "=" * 50)
    print("Validation complete!")

if __name__ == "__main__":
    main()
