#!/usr/bin/env python3
"""
Debug why backtest returns no results
"""

import sys
sys.path.insert(0, '.')
import os
import yaml

# Load credentials
with open('app.yaml', 'r') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml', 'r') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']

from src.core.oanda_client import OandaClient
from src.strategies.gold_scalping import GoldScalpingStrategy
from src.core.data_feed import MarketData

# Get some historical data
client = OandaClient(
    api_key=os.environ['OANDA_API_KEY'],
    account_id=os.environ['OANDA_ACCOUNT_ID'],
    environment='practice'
)

print("Downloading 100 candles for XAU_USD...")
result = client.get_candles('XAU_USD', granularity='M5', count=100)
candles = result['candles']
print(f"✅ Got {len(candles)} candles\n")

# Create strategy
strategy = GoldScalpingStrategy()
strategy.price_history = {'XAU_USD': []}

print("Building price history and testing signals...")
signals_generated = 0

for i, candle in enumerate(candles):
    # Extract price
    close_price = float(candle['bid']['c'])
    strategy.price_history['XAU_USD'].append(close_price)
    
    # Keep history manageable
    if len(strategy.price_history['XAU_USD']) > 200:
        strategy.price_history['XAU_USD'] = strategy.price_history['XAU_USD'][-200:]
    
    # Try to generate signal after we have enough data
    if len(strategy.price_history['XAU_USD']) >= 20:
        try:
            market_data = MarketData(
                pair='XAU_USD',
                bid=float(candle['bid']['c']),
                ask=float(candle['ask']['c']),
                spread=float(candle['ask']['c']) - float(candle['bid']['c']),
                timestamp=candle['time'],
                is_live=False,
                data_source='OANDA_Historical',
                last_update_age=0
            )
            
            signals = strategy.analyze_market({'XAU_USD': market_data})
            
            if signals:
                signals_generated += len(signals)
                print(f"Bar {i}: ✅ SIGNAL! {signals[0].direction} at {signals[0].current_price}")
                print(f"  SL: {signals[0].stop_loss}, TP: {signals[0].take_profit}")
                
        except Exception as e:
            if i == 20:  # Only print error once
                print(f"Bar {i}: Error generating signal: {str(e)}")

print(f"\n{'='*70}")
print(f"Total signals generated: {signals_generated}")
print(f"{'='*70}")

if signals_generated == 0:
    print("\n❌ PROBLEM: Strategy generates NO signals!")
    print("Need to check:")
    print("1. Are quality thresholds too high?")
    print("2. Does analyze_market work correctly?")
    print("3. Are filters too strict?")

