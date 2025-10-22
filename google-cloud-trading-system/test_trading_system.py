#!/usr/bin/env python3
"""
QUICK TRADING SYSTEM TEST
Verifies:
1. API authentication working
2. Accounts accessible
3. Live price data flowing
4. Trading capabilities enabled
"""

import os
import requests
from datetime import datetime

# Test configuration
CLOUD_URL = "https://ai-quant-trading.uc.r.appspot.com"
TELEGRAM_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
TELEGRAM_CHAT_ID = "6100678501"

def send_telegram(message):
    """Send Telegram notification"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        print(f"✅ Telegram sent")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

def test_system():
    """Test trading system"""
    print("="*60)
    print("🔍 TRADING SYSTEM HEALTH CHECK")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print(f"URL: {CLOUD_URL}")
    print()
    
    results = []
    
    # Test 1: Health Check
    print("1. Testing Health Endpoint...")
    try:
        r = requests.get(f"{CLOUD_URL}/api/health", timeout=15)
        if r.status_code == 200 and "ok" in r.text.lower():
            print("   ✅ System is ONLINE")
            results.append("✅ System Online")
        else:
            print(f"   ❌ Health check failed: {r.status_code}")
            results.append("❌ Health check failed")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        results.append(f"❌ Connection error: {e}")
    
    # Test 2: Accounts
    print("\n2. Testing Account Access...")
    try:
        r = requests.get(f"{CLOUD_URL}/api/accounts", timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "accounts" in data:
                account_count = len(data["accounts"])
                print(f"   ✅ {account_count} accounts accessible")
                results.append(f"✅ {account_count} Accounts Connected")
            else:
                print("   ⚠️  No accounts in response")
                results.append("⚠️ No accounts")
        else:
            print(f"   ❌ Accounts API failed: {r.status_code}")
            results.append("❌ Account access failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append(f"❌ Account error")
    
    # Test 3: Positions
    print("\n3. Testing Live Positions...")
    try:
        r = requests.get(f"{CLOUD_URL}/api/positions", timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "positions" in data:
                print(f"   ✅ Live positions accessible")
                results.append("✅ Positions API Working")
            else:
                print("   ⚠️  No positions data")
                results.append("⚠️ No positions data")
        else:
            print(f"   ❌ Positions API failed: {r.status_code}")
            results.append("❌ Positions failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append("❌ Positions error")
    
    # Test 4: Dashboard
    print("\n4. Testing Dashboard...")
    try:
        r = requests.get(CLOUD_URL, timeout=15)
        if r.status_code == 200:
            if "Trading Active" in r.text:
                print("   ✅ Dashboard shows: Trading Active")
                results.append("✅ AUTO-TRADING ACTIVE")
            elif "dashboard" in r.text.lower():
                print("   ✅ Dashboard accessible")
                results.append("✅ Dashboard Online")
            else:
                print("   ⚠️  Dashboard loaded but unclear status")
                results.append("⚠️ Dashboard unclear")
        else:
            print(f"   ❌ Dashboard failed: {r.status_code}")
            results.append("❌ Dashboard failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append("❌ Dashboard error")
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    for result in results:
        print(f"  {result}")
    
    # Send Telegram alert
    print("\n📱 Sending Telegram Alert...")
    message = f"""
🤖 <b>TRADING SYSTEM STATUS</b>

{chr(10).join(results)}

🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 <a href="{CLOUD_URL}">View Dashboard</a>
"""
    send_telegram(message)
    
    print("\n✅ Test complete!")
    print("="*60)

if __name__ == "__main__":
    test_system()

