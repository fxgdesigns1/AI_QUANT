#!/usr/bin/env python3
"""
Diagnostic and Fix Script for Trading System Issues
This script will:
1. Check if cron jobs are deployed
2. Test Telegram notifications
3. Check if scheduled scans are running
4. Provide detailed logs and fix recommendations
"""

import os
import sys
import json
import requests
from datetime import datetime

print("=" * 80)
print("🔍 TRADING SYSTEM DIAGNOSTIC TOOL")
print("=" * 80)
print()

# 1. Check Telegram Configuration
print("1️⃣ CHECKING TELEGRAM CONFIGURATION...")
print("-" * 80)
telegram_token = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
telegram_chat_id = "6100678501"

if telegram_token and telegram_chat_id:
    print(f"✅ Telegram Token: {telegram_token[:10]}...")
    print(f"✅ Telegram Chat ID: {telegram_chat_id}")
    
    # Test Telegram connection
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": f"🔧 <b>DIAGNOSTIC TEST</b>\n\n✅ Telegram notifications are working!\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n#DiagnosticTest",
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Telegram test message sent successfully!")
            print(f"   Response: {response.json().get('ok', False)}")
        else:
            print(f"❌ Telegram test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")
else:
    print("❌ Telegram credentials missing!")

print()

# 2. Check if cron jobs are deployed
print("2️⃣ CHECKING CRON JOBS...")
print("-" * 80)
try:
    result = os.popen("gcloud app describe 2>/dev/null | grep 'cron'").read()
    if result:
        print("✅ Cron configuration found")
    else:
        print("⚠️  Cron configuration not found in app description")
    
    # Check if cron.yaml exists
    if os.path.exists("cron.yaml"):
        print("✅ cron.yaml file exists")
        with open("cron.yaml", "r") as f:
            content = f.read()
            if "full_scan" in content:
                print("✅ full_scan jobs configured")
                # Count jobs
                job_count = content.count("url: /tasks/full_scan")
                print(f"   Found {job_count} scheduled scan jobs")
            else:
                print("❌ No scan jobs found in cron.yaml")
    else:
        print("❌ cron.yaml file not found!")
except Exception as e:
    print(f"❌ Error checking cron jobs: {e}")

print()

# 3. Check current system status
print("3️⃣ CHECKING SYSTEM STATUS...")
print("-" * 80)
try:
    response = requests.get("https://ai-quant-trading.uc.r.appspot.com/api/status", timeout=10)
    if response.status_code == 200:
        print("✅ System is online")
        data = response.json()
        
        # Check accounts
        if 'account_statuses' in data:
            print(f"✅ Active accounts: {len(data['account_statuses'])}")
            for acc_id, acc_data in data['account_statuses'].items():
                acc_name = acc_id[-3:]
                open_trades = acc_data.get('open_trades', 0)
                open_pos = acc_data.get('open_positions', 0)
                unrealized_pl = acc_data.get('unrealized_pl', 0)
                print(f"   • Account {acc_name}: {open_trades} trades, {open_pos} positions, P&L: ${unrealized_pl:.2f}")
        else:
            print("⚠️  No account data in status")
    else:
        print(f"❌ System status check failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error checking system status: {e}")

print()

# 4. Test scan endpoint
print("4️⃣ TESTING SCAN ENDPOINT...")
print("-" * 80)
try:
    print("   Triggering manual scan...")
    response = requests.post("https://ai-quant-trading.uc.r.appspot.com/tasks/full_scan", 
                            headers={"Content-Type": "application/json"},
                            timeout=60)
    
    if response.status_code == 200:
        print("✅ Scan endpoint is working")
        try:
            result = response.json()
            total_trades = result.get('total_trades', 0)
            scan_type = result.get('scan_type', 'unknown')
            print(f"   • Scan type: {scan_type}")
            print(f"   • Trades executed: {total_trades}")
        except:
            print("   Response received but not JSON")
    elif response.status_code == 302:
        print("⚠️  Scan endpoint requires authentication (302 redirect)")
        print("   This is expected for cron jobs (they have auth)")
    else:
        print(f"❌ Scan endpoint failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error testing scan endpoint: {e}")

print()

# 5. Recommendations
print("5️⃣ RECOMMENDATIONS & FIXES")
print("-" * 80)
print()

print("📋 ISSUE SUMMARY:")
print("   1. Cron jobs may not be deployed (need to deploy cron.yaml)")
print("   2. Telegram notifications need to be tested with actual trades")
print("   3. System needs manual trigger to verify it's working")
print()

print("🔧 FIXES TO APPLY:")
print()
print("   FIX 1: Deploy cron jobs")
print("   Command: gcloud app deploy cron.yaml")
print()
print("   FIX 2: Verify cron jobs are running")
print("   Command: gcloud app logs read --service=default --limit=50 | grep 'full_scan'")
print()
print("   FIX 3: Test Telegram manually (already done above)")
print()
print("   FIX 4: Add 'no trades found' Telegram notification")
print("   (This will ensure you get notified even when no trades are found)")
print()

print("=" * 80)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 80)
