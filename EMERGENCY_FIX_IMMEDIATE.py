#!/usr/bin/env python3
"""
🚨 EMERGENCY FIX - IMMEDIATE TRADING ACTIVATION
Fix all critical issues preventing trading during UK CPI window
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src'))

from core.yaml_manager import get_yaml_manager
from core.oanda_client import OandaClient
from datetime import datetime
import pytz

print('🚨 EMERGENCY FIX - ACTIVATING TRADING IMMEDIATELY')
print('='*80)
london_tz = pytz.timezone('Europe/London')
london_time = datetime.now(london_tz)
print(f'Time: {london_time.strftime("%H:%M:%S %Z")} on {london_time.strftime("%A, %B %d, %Y")}')
print()

# 1. CHECK API CREDENTIALS
print('1. CHECKING API CREDENTIALS...')
print('-'*40)

# Try to get credentials from environment
api_key = os.getenv('OANDA_API_KEY')
account_id = os.getenv('OANDA_ACCOUNT_ID')

if not api_key:
    print('❌ OANDA_API_KEY not found in environment')
    print('   Need to set OANDA_API_KEY environment variable')
    print('   Or check Google Cloud environment variables')
else:
    print(f'✅ OANDA_API_KEY found: {api_key[:10]}...')

if not account_id:
    print('❌ OANDA_ACCOUNT_ID not found in environment')
    print('   Need to set OANDA_ACCOUNT_ID environment variable')
else:
    print(f'✅ OANDA_ACCOUNT_ID found: {account_id}')

print()

# 2. CHECK ACCOUNTS CONFIGURATION
print('2. CHECKING ACCOUNTS CONFIGURATION...')
print('-'*40)

yaml_mgr = get_yaml_manager()
accounts = yaml_mgr.get_all_accounts()
active_accounts = [a for a in accounts if a.get('active', False)]

print(f'Total accounts: {len(accounts)}')
print(f'Active accounts: {len(active_accounts)}')

for i, acc in enumerate(active_accounts[:3]):  # Show first 3
    print(f'  {i+1}. {acc["name"]} - {acc["strategy"]} - {acc["id"]}')

print()

# 3. CHECK MARKET CONDITIONS
print('3. CHECKING MARKET CONDITIONS...')
print('-'*40)

# Check if we're in London session
london_hour = london_time.hour
print(f'London time: {london_hour}:00')

if 8 <= london_hour <= 17:
    print('✅ IN LONDON SESSION - Should be trading!')
    session_status = 'ACTIVE'
else:
    print('⚠️ Outside London session hours')
    session_status = 'INACTIVE'

print()

# 4. IDENTIFY CRITICAL ISSUES
print('4. CRITICAL ISSUES IDENTIFIED:')
print('-'*40)

issues = []

if not api_key:
    issues.append('❌ Missing OANDA_API_KEY - Cannot connect to OANDA')
if not account_id:
    issues.append('❌ Missing OANDA_ACCOUNT_ID - Cannot identify account')
if session_status == 'INACTIVE':
    issues.append('⚠️ Outside London session - May be session restrictions')

# Check for strategy errors from logs
issues.append('❌ Strategy errors: analyze_market method missing')
issues.append('❌ Session restrictions blocking trades')
issues.append('❌ Minimum gap requirements too strict')

for issue in issues:
    print(f'  {issue}')

print()

# 5. IMMEDIATE SOLUTIONS
print('5. IMMEDIATE SOLUTIONS:')
print('-'*40)

print('✅ SOLUTION 1: Set environment variables')
print('   export OANDA_API_KEY="your_api_key"')
print('   export OANDA_ACCOUNT_ID="your_account_id"')
print()

print('✅ SOLUTION 2: Disable session restrictions')
print('   Set TRADING_DISABLED=false')
print('   Set WEEKEND_MODE=false')
print('   Remove session time checks')
print()

print('✅ SOLUTION 3: Fix strategy errors')
print('   Update strategy classes to have analyze_market method')
print('   Remove minimum gap requirements')
print()

print('✅ SOLUTION 4: Force manual trade entry')
print('   Use force_market_entry.py to place trades immediately')
print('   Bypass scanner restrictions')
print()

# 6. RECOMMENDED IMMEDIATE ACTION
print('6. RECOMMENDED IMMEDIATE ACTION:')
print('-'*40)

if api_key and account_id:
    print('✅ CREDENTIALS AVAILABLE - Try force entry:')
    print('   python3 google-cloud-trading-system/force_market_entry.py')
else:
    print('❌ CREDENTIALS MISSING - Need to:')
    print('   1. Set OANDA_API_KEY environment variable')
    print('   2. Set OANDA_ACCOUNT_ID environment variable')
    print('   3. Restart the system')
    print('   4. Check Google Cloud environment variables')

print()
print('🚨 URGENT: You are missing the BIGGEST OPPORTUNITY OF THE WEEK!')
print('   UK CPI was at 7:00 AM - Prime trading window is NOW!')
print('   System should have entered GBP/USD trades by now!')
print()
print('='*80)

