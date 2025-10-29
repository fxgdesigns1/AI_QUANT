#!/usr/bin/env python3
"""
Verify ALL major pairs against external APIs to find data discrepancies
"""

import sys
sys.path.insert(0, '.')

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try importing yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    print("⚠️  yfinance not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
    import yfinance as yf
    HAS_YFINANCE = True

from src.core.historical_fetcher import get_historical_fetcher

# Pairs to verify with their Yahoo Finance symbols
PAIRS_TO_CHECK = [
    {'our_symbol': 'XAU_USD', 'yahoo': 'GC=F', 'name': 'Gold (XAU/USD)', 'expected_move': 7.5},
    {'our_symbol': 'USD_JPY', 'yahoo': 'JPY=X', 'name': 'USD/JPY', 'expected_move': 1.5},
    {'our_symbol': 'GBP_USD', 'yahoo': 'GBPUSD=X', 'name': 'GBP/USD', 'expected_move': 1.5},
    {'our_symbol': 'EUR_USD', 'yahoo': 'EURUSD=X', 'name': 'EUR/USD', 'expected_move': 1.3},
    {'our_symbol': 'AUD_USD', 'yahoo': 'AUDUSD=X', 'name': 'AUD/USD', 'expected_move': 1.4},
    {'our_symbol': 'USD_CAD', 'yahoo': 'CAD=X', 'name': 'USD/CAD', 'expected_move': 0.7},
    {'our_symbol': 'NZD_USD', 'yahoo': 'NZDUSD=X', 'name': 'NZD/USD', 'expected_move': 1.3},
]

print("🔍 EXTERNAL API VERIFICATION - ALL MAJOR PAIRS")
print("="*100)
print(f"Comparing our system data vs Yahoo Finance (trusted source)")
print(f"Lookback: 5 days (~120 hours)")
print("="*100)

# Initialize our data fetcher
fetcher = get_historical_fetcher()

all_our_symbols = [p['our_symbol'] for p in PAIRS_TO_CHECK]
print(f"\n📥 Fetching our system data for {len(all_our_symbols)} pairs...")

try:
    our_data = fetcher.get_recent_data_for_strategy(all_our_symbols, hours=120)
    print(f"✅ Retrieved data from our system")
except Exception as e:
    print(f"❌ Error fetching our data: {e}")
    our_data = {}

print(f"\n📊 PAIR-BY-PAIR COMPARISON:")
print("-"*100)

discrepancies_found = []

for pair_info in PAIRS_TO_CHECK:
    print(f"\n{pair_info['name']} (Expected move: ~{pair_info['expected_move']}%)")
    print("-"*50)
    
    # Get from Yahoo Finance
    try:
        ticker = yf.Ticker(pair_info['yahoo'])
        hist = ticker.history(period='5d')
        
        if len(hist) < 2:
            print(f"  ⚠️  Yahoo Finance: Insufficient data")
            yahoo_move = None
            yahoo_start = None
            yahoo_end = None
        else:
            yahoo_start = float(hist['Close'].iloc[0])
            yahoo_end = float(hist['Close'].iloc[-1])
            yahoo_move = ((yahoo_end - yahoo_start) / yahoo_start) * 100
            
            print(f"  Yahoo Finance:")
            print(f"    Start: {yahoo_start:.4f}")
            print(f"    End:   {yahoo_end:.4f}")
            print(f"    Move:  {yahoo_move:+.2f}%")
    except Exception as e:
        print(f"  ❌ Yahoo Finance error: {e}")
        yahoo_move = None
    
    # Get from our system
    our_symbol = pair_info['our_symbol']
    if our_symbol in our_data and len(our_data[our_symbol]) > 0:
        our_candles = our_data[our_symbol]
        our_start = float(our_candles[0]['close'])
        our_end = float(our_candles[-1]['close'])
        our_move = ((our_end - our_start) / our_start) * 100
        
        print(f"  Our System (OANDA):")
        print(f"    Start: {our_start:.4f}")
        print(f"    End:   {our_end:.4f}")
        print(f"    Move:  {our_move:+.2f}%")
        print(f"    Bars:  {len(our_candles)}")
        
        # Compare if we have both
        if yahoo_move is not None:
            discrepancy = abs(yahoo_move - our_move)
            
            print(f"\n  Comparison:")
            print(f"    Discrepancy: {discrepancy:.2f}%")
            
            if discrepancy > 0.5:
                print(f"    ❌ ERROR: Significant data mismatch!")
                discrepancies_found.append({
                    'pair': pair_info['name'],
                    'yahoo': yahoo_move,
                    'ours': our_move,
                    'discrepancy': discrepancy
                })
            else:
                print(f"    ✅ Data matches (within 0.5%)")
    else:
        print(f"  ❌ Our System: No data retrieved for {our_symbol}")

print("\n" + "="*100)
print("SUMMARY:")
print("="*100)

if discrepancies_found:
    print(f"\n❌ Found {len(discrepancies_found)} pairs with data discrepancies:")
    for d in discrepancies_found:
        print(f"  • {d['pair']}: Yahoo {d['yahoo']:+.2f}% vs Ours {d['ours']:+.2f}% (diff: {d['discrepancy']:.2f}%)")
    print("\n⚠️  DATA QUALITY ISSUE CONFIRMED - Need to investigate calculation vs fetching")
else:
    print("\n✅ All pairs match external data within acceptable tolerance")
    print("   → Data fetching is correct")
    print("   → Issue is likely in strategy CALCULATION, not data source")

print("\n" + "="*100)
print("NEXT STEPS:")
print("="*100)
print("1. If data matches: Check strategy momentum/indicator calculations")
print("2. If data mismatches: Check historical_fetcher.py and OANDA API calls")
print("3. Run debug_momentum_values.py to see what strategies calculate")
print("="*100)














