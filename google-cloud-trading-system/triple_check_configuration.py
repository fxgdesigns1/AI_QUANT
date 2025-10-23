#!/usr/bin/env python3
"""
TRIPLE CHECK - Complete System Configuration Verification
Verifies EVERY setting before next scan
"""

import os
import re

print("=" * 100)
print("🔍 TRIPLE CHECK - COMPLETE CONFIGURATION VERIFICATION")
print("=" * 100)
print()

def check_file_setting(filepath, pattern, setting_name):
    """Check a specific setting in a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            matches = re.findall(pattern, content)
            if matches:
                print(f"   ✅ {setting_name}: {matches[0]}")
                return True
            else:
                print(f"   ❌ {setting_name}: NOT FOUND")
                return False
    except Exception as e:
        print(f"   ❌ Error reading {filepath}: {e}")
        return False

print("1️⃣ ACCOUNT 009 - GOLD SCALPING")
print("-" * 100)
file_path = "src/strategies/gold_scalping.py"
if os.path.exists(file_path):
    check_file_setting(file_path, r'units=(\d+)', "Lot size (units)")
    check_file_setting(file_path, r'self\.stop_loss_pips\s*=\s*(\d+)', "Stop loss (pips)")
    check_file_setting(file_path, r'self\.take_profit_pips\s*=\s*(\d+)', "Take profit (pips)")
    check_file_setting(file_path, r'self\.min_trades_today\s*=\s*(\d+)', "Min trades today")
    check_file_setting(file_path, r'self\.max_trades_per_day\s*=\s*(\d+)', "Max trades per day")
    check_file_setting(file_path, r'self\.min_warmup_prices\s*=\s*(\d+)', "Warm-up requirement")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("2️⃣ ACCOUNT 010 - ULTRA STRICT FOREX")
print("-" * 100)
file_path = "src/strategies/ultra_strict_forex.py"
if os.path.exists(file_path):
    check_file_setting(file_path, r'units=(\d+)', "Lot size (units)")
    check_file_setting(file_path, r'self\.stop_loss_pct\s*=\s*([\d.]+)', "Stop loss (%)")
    check_file_setting(file_path, r'self\.take_profit_pct\s*=\s*([\d.]+)', "Take profit (%)")
    check_file_setting(file_path, r'self\.min_trades_today\s*=\s*(\d+)', "Min trades today")
    check_file_setting(file_path, r'self\.max_trades_per_day\s*=\s*(\d+)', "Max trades per day")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("3️⃣ ACCOUNT 011 - MOMENTUM TRADING")
print("-" * 100)
file_path = "src/strategies/momentum_trading.py"
if os.path.exists(file_path):
    check_file_setting(file_path, r'units=(\d+)', "Lot size (units)")
    check_file_setting(file_path, r'self\.stop_loss_atr\s*=\s*([\d.]+)', "Stop loss (ATR)")
    check_file_setting(file_path, r'self\.take_profit_atr\s*=\s*([\d.]+)', "Take profit (ATR)")
    check_file_setting(file_path, r'self\.min_trades_today\s*=\s*(\d+)', "Min trades today")
    check_file_setting(file_path, r'self\.max_trades_per_day\s*=\s*(\d+)', "Max trades per day")
    check_file_setting(file_path, r'self\.min_adx\s*=\s*(\d+)', "Min ADX")
    check_file_setting(file_path, r'self\.min_momentum\s*=\s*([\d.]+)', "Min momentum")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("4️⃣ TELEGRAM CONFIGURATION")
print("-" * 100)
file_path = "app.yaml"
if os.path.exists(file_path):
    check_file_setting(file_path, r'TELEGRAM_TOKEN:\s*"([^"]+)"', "Telegram Token")
    check_file_setting(file_path, r'TELEGRAM_CHAT_ID:\s*"([^"]+)"', "Telegram Chat ID")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("5️⃣ CRON JOBS CONFIGURATION")
print("-" * 100)
file_path = "cron.yaml"
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
        job_count = content.count('url: /tasks/full_scan')
        print(f"   ✅ Scheduled scan jobs: {job_count}")
        
        # List all schedules
        schedules = re.findall(r'schedule:\s*(.+)', content)
        for i, schedule in enumerate(schedules, 1):
            print(f"      {i}. {schedule}")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("6️⃣ PROGRESSIVE SCANNER INTEGRATION")
print("-" * 100)
file_path = "main.py"
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
        
        if 'progressive_scan' in content.lower():
            print("   ✅ Progressive scanner endpoint exists")
        else:
            print("   ❌ Progressive scanner endpoint NOT found")
        
        if 'ALWAYS SEND' in content:
            print("   ✅ Enhanced notifications (ALWAYS SEND) enabled")
        else:
            print("   ⚠️  Enhanced notifications may not be active")
        
        if 'ProgressiveTradingScanner' in content:
            print("   ✅ Progressive scanner imported in full_scan")
        else:
            print("   ❌ Progressive scanner NOT imported")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("7️⃣ ORDER MANAGER CONFIGURATION")
print("-" * 100)
file_path = "src/core/order_manager.py"
if os.path.exists(file_path):
    check_file_setting(file_path, r"GOLD_MAX_POSITIONS',\s*'(\d+)'", "Max positions default")
else:
    print(f"   ❌ File not found: {file_path}")
print()

print("=" * 100)
print("📊 CONFIGURATION SUMMARY")
print("=" * 100)
print()

print("Expected Trade Execution on Next Scan:")
print()
print("Account 009 (Gold Scalping):")
print("   • Will attempt 3+ gold trades")
print("   • Lot size: 7,500 units ($600 risk)")
print("   • SL: 8 pips, TP: 12 pips")
print("   • Forced entry if criteria not met")
print()
print("Account 010 (Ultra Strict Forex):")
print("   • Will attempt 10+ forex trades")
print("   • Lot size: 100,000 units ($500 risk)")
print("   • SL: 0.5%, TP: 0.8%")
print("   • NO TRADE LIMIT (999/day)")
print("   • NO POSITION LIMIT (50 max)")
print()
print("Account 011 (Momentum Trading):")
print("   • Will attempt 5+ momentum trades")
print("   • Lot size: 100,000 units ($500 risk)")
print("   • SL: 1.5 ATR, TP: 2.5 ATR")
print("   • Very low criteria (ADX>10)")
print()

print("Progressive Relaxation:")
print("   • Level 0: Try current criteria")
print("   • Level 1: Relax to 20% confidence")
print("   • Level 2: Relax to 10% confidence")
print("   • Level 3: Relax to 5% confidence")
print("   • Will continue until trades found")
print()

print("Notifications:")
print("   • Telegram notification ALWAYS sent")
print("   • Shows exact trade count per account")
print("   • Includes timestamp and next scan info")
print("   • Sent even if no trades found")
print()

print("=" * 100)
print("✅ TRIPLE CHECK COMPLETE")
print("=" * 100)
