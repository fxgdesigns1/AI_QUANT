#!/usr/bin/env python3
from src.core.settings import settings
"""
Test current market conditions against strategy thresholds
Get real data and see if strategies SHOULD generate signals
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime

import os
OANDA_API_KEY = settings.oanda_api_key
ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "101-004-30719775-009")
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable is required")

headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}

print("="*70)
print("TESTING CURRENT MARKET CONDITIONS")
print("="*70)
print(f"\nTime: {datetime.now().strftime('%H:%M:%S London')}\n")

# Test EUR_USD (most traded)
inst = "EUR_USD"
url = f"https://api-fxpractice.oanda.com/v3/accounts/{ACCOUNT_ID}/instruments/{inst}/candles"
params = {"granularity": "M5", "count": 60}

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        candles = data.get('candles', [])
        
        print(f"{inst} - {len(candles)} candles retrieved")
        
        # Convert to DataFrame
        df_data = []
        for candle in candles:
            df_data.append({
                'close': float(candle['mid']['c']),
                'high': float(candle['mid']['h']),
                'low': float(candle['mid']['l']),
                'volume': int(candle.get('volume', 1000))
            })
        
        df = pd.DataFrame(df_data)
        
        # Calculate indicators
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
        current = df['close'].iloc[-1]
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # Calculate ATR
        df['hl'] = df['high'] - df['low']
        atr = df['hl'].rolling(14).mean().iloc[-1]
        
        # Calculate volatility
        returns = df['close'].pct_change()
        volatility = returns.std()
        
        # Calculate recent movement
        change_1h = ((df['close'].iloc[-1] - df['close'].iloc[-12]) / df['close'].iloc[-12]) * 100 if len(df) >= 12 else 0
        
        print(f"\nMARKET ANALYSIS:")
        print(f"  Current Price: {current:.5f}")
        print(f"  EMA 20: {ema_20:.5f}")
        print(f"  EMA 50: {ema_50:.5f}")
        print(f"  RSI: {rsi_val:.1f}")
        print(f"  ATR: {atr:.5f}")
        print(f"  Volatility: {volatility:.6f}")
        print(f"  1H Change: {change_1h:+.3f}%")
        
        # Check against thresholds
        print(f"\nSTRATEGY THRESHOLD CHECK:")
        
        # Trend
        if ema_20 > ema_50:
            print(f"  ✅ Trend: BULLISH (EMA 20 > 50)")
            trend_score = 0.3
        else:
            print(f"  ❌ Trend: BEARISH/FLAT (EMA 20 < 50)")
            trend_score = 0.1
        
        # RSI
        if 40 <= rsi_val <= 60:
            print(f"  ✅ RSI: In range (40-60)")
            rsi_score = 0.2
        else:
            print(f"  ⚠️  RSI: {rsi_val:.1f} (outside 40-60)")
            rsi_score = 0.05
        
        # Volatility
        if volatility > 0.00003:
            print(f"  ✅ Volatility: {volatility:.6f} (> 0.00003)")
            vol_score = 0.2
        else:
            print(f"  ❌ Volatility: {volatility:.6f} (TOO LOW!)")
            vol_score = 0
        
        # Movement
        if abs(change_1h) > 0.1:
            print(f"  ✅ Movement: {change_1h:+.3f}% (> 0.1%)")
            move_score = 0.2
        else:
            print(f"  ❌ Movement: {change_1h:+.3f}% (TOO SMALL!)")
            move_score = 0
        
        # Total signal strength
        total_strength = trend_score + rsi_score + vol_score + move_score
        print(f"\n  TOTAL SIGNAL STRENGTH: {total_strength:.2f} / 1.00")
        
        if total_strength >= 0.70:
            print(f"  ✅ MEETS 70% THRESHOLD - SHOULD TRADE!")
        else:
            print(f"  ❌ BELOW 70% THRESHOLD - Correctly skipping")
            print(f"  Market too quiet/choppy for quality trades")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)


