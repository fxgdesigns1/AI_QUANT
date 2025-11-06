#!/usr/bin/env python3
"""
COMPREHENSIVE DIAGNOSTIC - Find ALL blocking conditions preventing trades
This script will identify every single reason why trades aren't executing
"""

import sys
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

# OANDA Configuration
OANDA_API_KEY = "REMOVED_SECRET"
OANDA_ACCOUNT_ID = "101-004-30719775-008"
OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

print("="*80)
print("🔍 COMPREHENSIVE TRADING BLOCKER DIAGNOSTIC")
print("="*80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

headers = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

blockers_found = []
warnings_found = []

# Test 1: API Connectivity
print("[TEST 1] API Connectivity")
print("-"*80)
try:
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        account_info = response.json()['account']
        print(f"✅ API Connected - Balance: ${float(account_info['balance']):.2f}")
        print(f"   Account Status: {account_info.get('state', 'UNKNOWN')}")
        if account_info.get('state') != 'TRADE_OPEN':
            blockers_found.append(f"❌ Account state is {account_info.get('state')} - trading may be disabled")
    else:
        blockers_found.append(f"❌ API Connection Failed: {response.status_code}")
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    blockers_found.append(f"❌ API Connection Error: {e}")
    print(f"❌ Error: {e}")

print()

# Test 2: Price Data Availability
print("[TEST 2] Price Data Availability")
print("-"*80)
try:
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing"
    params = {'instruments': 'EUR_USD,GBP_USD,USD_JPY,XAU_USD,AUD_USD'}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        prices = {}
        for price_data in data.get('prices', []):
            inst = price_data.get('instrument')
            if inst:
                bids = price_data.get('bids', [])
                asks = price_data.get('asks', [])
                if bids and asks:
                    bid = float(bids[0].get('price', 0))
                    ask = float(asks[0].get('price', 0))
                    if bid > 0 and ask > 0:
                        prices[inst] = {
                            'bid': bid,
                            'ask': ask,
                            'mid': (bid + ask) / 2,
                            'spread': ask - bid,
                            'status': price_data.get('status', 'UNKNOWN')
                        }
        
        print(f"✅ Prices Available: {len(prices)}/{len(params['instruments'].split(','))}")
        for inst, data in prices.items():
            status = data.get('status', 'UNKNOWN')
            spread = data['spread']
            if status != 'tradeable':
                warnings_found.append(f"⚠️ {inst} status: {status} (may block trading)")
            print(f"   {inst}: {data['mid']:.5f} (spread: {spread:.5f}, status: {status})")
        
        if len(prices) == 0:
            blockers_found.append("❌ NO PRICE DATA AVAILABLE - Cannot generate signals")
    else:
        blockers_found.append(f"❌ Price API Failed: {response.status_code}")
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    blockers_found.append(f"❌ Price Data Error: {e}")
    print(f"❌ Error: {e}")

print()

# Test 3: Check Trading System Status
print("[TEST 3] Trading System Status")
print("-"*80)

# Check if ai_trading_system.py exists and analyze it
try:
    with open('ai_trading_system.py', 'r') as f:
        content = f.read()
        
    # Check trading_enabled flag
    if 'self.trading_enabled = True' in content:
        print("✅ trading_enabled initialized to True")
    else:
        warnings_found.append("⚠️ trading_enabled may not be initialized correctly")
    
    # Check for blocking conditions
    blocking_conditions = [
        ('News halt active', 'is_news_halt_active()'),
        ('Trading disabled', 'not self.trading_enabled'),
        ('Daily trade limit', 'daily_trade_count >= max_daily_trades'),
        ('Max concurrent trades', 'total_live >= max_concurrent_trades'),
        ('Per-symbol cap', 'sym_live >= current_symbol_cap'),
        ('Position size too small', 'units == 0'),
        ('Minimum R threshold', 'tp_dist < (min_r * sl_dist)'),
        ('Minimum absolute profit', 'expected_abs < min_abs'),
    ]
    
    print("🔍 Blocking conditions found in code:")
    for name, condition in blocking_conditions:
        if condition in content or name.lower() in content.lower():
            print(f"   ⚠️ {name}: {condition}")
            warnings_found.append(f"⚠️ {name} check exists")
    
    # Check signal generation requirements
    signal_requirements = [
        ('confirm_above >= 2', 'Requires 3 consecutive candles above upper band'),
        ('slope_up', 'Requires upward price trend'),
        ('m15_ema alignment', 'Requires M15 EMA alignment for BUY'),
        ('London session', 'XAU requires London session (8-17 UTC)'),
        ('Spread limits', 'Instrument-specific spread thresholds'),
        ('ATR > 0', 'Requires valid ATR calculation'),
        ('EMA > 0', 'Requires valid EMA calculation'),
    ]
    
    print("\n🔍 Signal generation requirements:")
    for req, desc in signal_requirements:
        print(f"   • {req}: {desc}")
        warnings_found.append(f"⚠️ Signal requires: {req}")
        
except Exception as e:
    print(f"⚠️ Could not analyze trading system: {e}")

print()

# Test 4: Check Current Market Conditions
print("[TEST 4] Current Market Conditions")
print("-"*80)

try:
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing"
    params = {'instruments': 'EUR_USD,GBP_USD,USD_JPY,XAU_USD,AUD_USD'}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        now = datetime.utcnow()
        hour = now.hour
        
        print(f"Current UTC Time: {now.strftime('%H:%M:%S')} (Hour: {hour})")
        
        # Check London session
        in_london = 8 <= hour <= 17
        print(f"London Session (8-17 UTC): {'✅ ACTIVE' if in_london else '❌ INACTIVE'}")
        if not in_london:
            warnings_found.append(f"⚠️ Outside London session - XAU trades blocked")
        
        # Check London/NY overlap
        in_overlap = 13 <= hour <= 17
        print(f"London/NY Overlap (13-17 UTC): {'✅ ACTIVE' if in_overlap else '❌ INACTIVE'}")
        
        # Check weekend
        weekday = now.weekday()
        is_weekend = weekday >= 5
        print(f"Weekend: {'❌ YES' if is_weekend else '✅ NO'}")
        if is_weekend:
            blockers_found.append("❌ WEEKEND - Markets closed, no trades possible")
        
        # Check spreads
        print("\n📊 Spread Analysis:")
        for price_data in data.get('prices', []):
            inst = price_data.get('instrument')
            if not inst:
                continue
            bids = price_data.get('bids', [])
            asks = price_data.get('asks', [])
            if not bids or not asks:
                continue
            
            bid = float(bids[0].get('price', 0))
            ask = float(asks[0].get('price', 0))
            spread = ask - bid
            
            # Check against limits
            limits = {
                'EUR_USD': 0.00025,
                'GBP_USD': 0.00030,
                'AUD_USD': 0.00030,
                'USD_JPY': 0.025,
                'XAU_USD': 1.00
            }
            
            limit = limits.get(inst, 0.00030)
            status = "✅ OK" if spread <= limit else "❌ TOO WIDE"
            if spread > limit:
                blockers_found.append(f"❌ {inst} spread {spread:.5f} > limit {limit:.5f}")
            
            print(f"   {inst}: {spread:.5f} (limit: {limit:.5f}) {status}")
            
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 5: Check Active Positions and Limits
print("[TEST 5] Active Positions and Limits")
print("-"*80)

try:
    # Get positions
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/positions"
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        positions = response.json().get('positions', [])
        active_positions = []
        for pos in positions:
            long_units = float(pos.get('long', {}).get('units', 0))
            short_units = float(pos.get('short', {}).get('units', 0))
            if long_units != 0 or short_units != 0:
                active_positions.append({
                    'instrument': pos['instrument'],
                    'long': long_units,
                    'short': short_units
                })
        
        print(f"Active Positions: {len(active_positions)}")
        for pos in active_positions:
            print(f"   {pos['instrument']}: LONG {pos['long']}, SHORT {pos['short']}")
        
        if len(active_positions) >= 5:
            blockers_found.append(f"❌ Max concurrent trades reached: {len(active_positions)}/5")
        
    # Get pending orders
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pendingOrders"
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        orders = response.json().get('orders', [])
        entry_orders = [o for o in orders if o.get('type') in ('LIMIT', 'STOP', 'MARKET_IF_TOUCHED')]
        print(f"Pending Entry Orders: {len(entry_orders)}")
        
        total_live = len(active_positions) + len(entry_orders)
        if total_live >= 5:
            blockers_found.append(f"❌ Total live (positions + pending) >= 5: {total_live}")
        
except Exception as e:
    print(f"⚠️ Error checking positions: {e}")

print()

# Test 6: Signal Generation Simulation
print("[TEST 6] Signal Generation Simulation")
print("-"*80)

try:
    # Fetch candles for EUR_USD
    url = f"{OANDA_BASE_URL}/v3/instruments/EUR_USD/candles"
    params = {
        'granularity': 'M5',
        'count': 200,
        'price': 'M'
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code == 200:
        candles = response.json().get('candles', [])
        mids = []
        for c in candles:
            try:
                mid = float(c['mid']['c'])
                mids.append(mid)
            except:
                continue
        
        if len(mids) >= 50:
            print(f"✅ Candle data available: {len(mids)} candles")
            
            # Calculate EMA(50)
            period = 50
            k = 2 / (period + 1)
            ema = mids[0]
            for v in mids[1:period]:
                ema = v * k + ema * (1 - k)
            
            # Calculate ATR
            trs = [abs(mids[i] - mids[i-1]) for i in range(1, len(mids))]
            atr = sum(trs[:14]) / 14 if len(trs) >= 14 else 0
            
            current_price = mids[-1]
            upper = ema + 1.25 * atr
            lower = ema - 1.25 * atr
            
            print(f"   Current Price: {current_price:.5f}")
            print(f"   EMA(50): {ema:.5f}")
            print(f"   ATR(14): {atr:.5f}")
            print(f"   Upper Band: {upper:.5f}")
            print(f"   Lower Band: {lower:.5f}")
            
            # Check signal conditions
            last3 = mids[-3:]
            confirm_above = sum(1 for v in last3 if v > upper)
            confirm_below = sum(1 for v in last3 if v < lower)
            slope_up = len(mids) >= 4 and (mids[-1] > mids[-2] >= mids[-3])
            
            print(f"\n   Signal Conditions:")
            print(f"   • Price above upper: {current_price > upper}")
            print(f"   • confirm_above >= 2: {confirm_above >= 2} (actual: {confirm_above})")
            print(f"   • slope_up: {slope_up}")
            
            if not (current_price > upper and confirm_above >= 2 and slope_up):
                blockers_found.append("❌ Signal conditions NOT MET - No BUY signal generated")
                print(f"   ❌ BUY Signal: BLOCKED (conditions not met)")
            else:
                print(f"   ✅ BUY Signal: WOULD BE GENERATED")
            
            if not (current_price < lower and confirm_below >= 2):
                print(f"   ❌ SELL Signal: BLOCKED (conditions not met)")
            else:
                print(f"   ✅ SELL Signal: WOULD BE GENERATED")
        else:
            blockers_found.append("❌ Insufficient candle data for signal generation")
            print(f"❌ Only {len(mids)} candles available (need >= 50)")
            
except Exception as e:
    print(f"❌ Error: {e}")

print()

# SUMMARY
print("="*80)
print("📊 DIAGNOSTIC SUMMARY")
print("="*80)

print(f"\n🚨 CRITICAL BLOCKERS ({len(blockers_found)}):")
if blockers_found:
    for i, blocker in enumerate(blockers_found, 1):
        print(f"   {i}. {blocker}")
else:
    print("   ✅ None found")

print(f"\n⚠️ WARNINGS ({len(warnings_found)}):")
if warnings_found:
    for i, warning in enumerate(warnings_found[:10], 1):  # Limit to 10
        print(f"   {i}. {warning}")
else:
    print("   ✅ None found")

print("\n" + "="*80)
print("💡 RECOMMENDED FIXES")
print("="*80)

if blockers_found:
    print("\n1. IMMEDIATE FIXES NEEDED:")
    for blocker in blockers_found:
        if "WEEKEND" in blocker:
            print("   → Wait for market open (Monday 00:00 UTC)")
        elif "spread" in blocker.lower():
            print("   → Wait for tighter spreads or adjust spread limits")
        elif "Signal conditions" in blocker:
            print("   → Relax signal generation requirements:")
            print("     - Reduce confirm_above requirement from 2 to 1")
            print("     - Remove slope_up requirement")
            print("     - Remove m15_ema alignment requirement")
        elif "max concurrent" in blocker.lower():
            print("   → Increase max_concurrent_trades limit or close positions")
        elif "position size" in blocker.lower():
            print("   → Reduce minimum position size requirements")
else:
    print("\n✅ No critical blockers found!")
    print("   → System should be able to trade")
    print("   → Check if signals are being generated but not executed")

print("\n2. STRATEGY RELAXATION OPTIONS:")
print("   → Reduce confirm_above from 2 to 1")
print("   → Remove slope_up requirement")
print("   → Remove m15_ema alignment")
print("   → Increase spread limits")
print("   → Reduce minimum R threshold")
print("   → Reduce minimum absolute profit")

print("\n3. MONITORING COMMANDS:")
print("   → Check logs: tail -f logs/*.log | grep -i 'signal\\|trade\\|block'")
print("   → Check system status: python3 ai_trading_system.py (manual run)")
print("   → Force signal test: Run this script regularly")

print("\n" + "="*80)
print("✅ DIAGNOSTIC COMPLETE")
print("="*80)
