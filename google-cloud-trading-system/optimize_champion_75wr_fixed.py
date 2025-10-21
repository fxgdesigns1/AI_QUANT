#!/usr/bin/env python3
"""
Optimize 75% WR Champion - FIXED for its unique analyze_market signature
"""

import os
import sys
import json
from datetime import datetime
import yaml

sys.path.insert(0, '.')

# Load credentials
with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']

from src.core.oanda_client import OandaClient
from src.strategies.champion_75wr import UltraSelective75WRChampion
from src.core.data_feed import MarketData

print("\n" + "="*70)
print("75% WR CHAMPION - MANUAL OPTIMIZATION")
print("="*70 + "\n")

client = OandaClient(os.environ['OANDA_API_KEY'], os.environ['OANDA_ACCOUNT_ID'], 'practice')

# Download data for all instruments
instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
all_data = {}

print("Downloading 5 days of data...")
for inst in instruments:
    result = client.get_candles(inst, granularity='M5', count=1440)  # 5 days
    all_data[inst] = result['candles']
    print(f"  {inst}: {len(all_data[inst])} candles")

# Test best parameter combination
strategy = UltraSelective75WRChampion()
strategy.price_history = {inst: [] for inst in instruments}

signals_count = 0
trades = []

print("\nRunning backtest...")

# Build price history first
for inst in instruments:
    for candle in all_data[inst][:100]:
        close = float(candle['bid']['c'])
        strategy.price_history[inst].append(close)

# Now test each instrument
for inst in instruments:
    print(f"\nTesting {inst}...")
    inst_signals = 0
    
    for i, candle in enumerate(all_data[inst][100:], 100):
        close = float(candle['bid']['c'])
        strategy.price_history[inst].append(close)
        
        if len(strategy.price_history[inst]) > 200:
            strategy.price_history[inst] = strategy.price_history[inst][-200:]
        
        md = MarketData(inst, float(candle['bid']['c']), float(candle['ask']['c']),
                       float(candle['ask']['c'])-float(candle['bid']['c']), candle['time'],
                       False, 'OANDA', 0)
        
        try:
            # Call with BOTH arguments
            signal = strategy.analyze_market({inst: md}, inst)
            if signal:
                inst_signals += 1
                signals_count += 1
                if inst_signals == 1:
                    print(f"  ✅ First signal at bar {i}")
        except Exception as e:
            if i == 100:
                print(f"  Error: {str(e)}")
    
    print(f"  Total signals: {inst_signals}")

print(f"\n{'='*70}")
print(f"TOTAL SIGNALS: {signals_count}")
print(f"{'='*70}")




