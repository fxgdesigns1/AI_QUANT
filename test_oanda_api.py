#!/usr/bin/env python3
"""Quick test to verify OANDA API is working"""
import requests
import json
from datetime import datetime, timedelta

import os
API_KEY = os.getenv('OANDA_API_KEY')
if not API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
BASE_URL = 'https://api-fxpractice.oanda.com'
headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

# Test with one account
account_id = '101-004-30719775-007'

print(f"Testing OANDA API for account {account_id}")
print("="*80)

# Test 1: Get account summary
print("\n1. Testing account summary...")
try:
    response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/summary', headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        account = data.get('account', {})
        print(f"   Balance: {account.get('balance', 'N/A')}")
        print(f"   Last Transaction ID: {account.get('lastTransactionID', 'N/A')}")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 2: Get transactions (no filter)
print("\n2. Testing transactions (no filter)...")
try:
    response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/transactions', headers=headers, params={'count': 10}, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        transactions = data.get('transactions', [])
        print(f"   Found {len(transactions)} transactions")
        if transactions:
            print(f"   Latest transaction: {transactions[0].get('type', 'N/A')} at {transactions[0].get('time', 'N/A')}")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 3: Get open trades
print("\n3. Testing open trades...")
try:
    response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/openTrades', headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        trades = data.get('trades', [])
        print(f"   Found {len(trades)} open trades")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 4: Get closed trades
print("\n4. Testing closed trades...")
try:
    response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/trades', headers=headers, params={'state': 'CLOSED', 'count': 10}, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        trades = data.get('trades', [])
        print(f"   Found {len(trades)} closed trades")
        if trades:
            print(f"   Latest closed: {trades[0].get('instrument', 'N/A')} at {trades[0].get('closeTime', 'N/A')}")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

print("\n" + "="*80)

