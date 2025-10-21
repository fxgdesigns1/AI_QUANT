#!/usr/bin/env python3
"""
Deep debug of analyze_market to trace EXACTLY why no signals are generated
"""

import sys
sys.path.insert(0, '.')

import os
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

load_dotenv()

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🔍 DEEP DEBUG: analyze_market Method")
print("="*100)
print("Tracing EXACTLY why signals aren't being generated")
print("="*100)

# Load strategy
print("\n📊 Step 1: Load Strategy")
print("-"*100)

strategy = get_momentum_trading_strategy()

print(f"✅ Strategy loaded")
print(f"   Instruments: {strategy.instruments}")
print(f"   Price history bars: {sum(len(hist) for hist in strategy.price_history.values())}")
print(f"\n   Current thresholds:")
print(f"   - min_adx: {strategy.min_adx}")
print(f"   - min_momentum: {strategy.min_momentum}")
print(f"   - min_volume: {strategy.min_volume}")
print(f"   - min_quality_score: {strategy.min_quality_score}")

# Get recent data
print("\n📥 Step 2: Get Recent Market Data")
print("-"*100)

fetcher = get_historical_fetcher()
historical_data = fetcher.get_recent_data_for_strategy(['XAU_USD', 'EUR_USD', 'GBP_USD'], hours=48)

print(f"✅ Retrieved data for 3 instruments")

# Build price history
print("\n📈 Step 3: Build Price History")
print("-"*100)

for instrument in ['XAU_USD', 'EUR_USD', 'GBP_USD']:
    if instrument in historical_data:
        for candle in historical_data[instrument]:
            if instrument not in strategy.price_history:
                strategy.price_history[instrument] = []
            strategy.price_history[instrument].append({
                'time': candle['time'],
                'close': float(candle['close']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'volume': float(candle['volume'])
            })

for instrument in ['XAU_USD', 'EUR_USD', 'GBP_USD']:
    bars = len(strategy.price_history.get(instrument, []))
    print(f"   {instrument}: {bars} bars")

# Test on last 10 candles to see detailed rejection reasons
print("\n🎯 Step 4: Test Signal Generation (Last 10 Candles)")
print("="*100)

test_instruments = ['XAU_USD', 'EUR_USD']  # Test both Gold and EUR_USD

for instrument in test_instruments:
    if instrument not in historical_data:
        continue
    
    print(f"\n{'='*100}")
    print(f"Testing: {instrument}")
    print(f"{'='*100}\n")
    
    # Get last 10 candles
    candles = historical_data[instrument][-10:]
    
    for idx, candle in enumerate(candles):
        print(f"\n{'─'*100}")
        print(f"Candle {idx+1}/10 - {candle['time']}")
        print(f"{'─'*100}")
        
        close_price = float(candle['close'])
        
        print(f"Price: {close_price:.2f}")
        
        # Create market data
        market_data = MarketData(
            pair=instrument,
            bid=close_price,
            ask=close_price + 0.0001,
            timestamp=candle['time'],
            is_live=False,
            data_source='OANDA_Historical',
            spread=0.0001,
            last_update_age=0
        )
        
        # Create market data dict for analyze_market
        market_data_dict = {instrument: market_data}
        
        # MANUALLY TRACE THROUGH analyze_market LOGIC
        print(f"\n🔍 Tracing analyze_market logic:")
        
        # Check 1: Instrument in tracked list?
        if instrument not in strategy.instruments:
            print(f"   ❌ BLOCKED: Instrument not in strategy.instruments")
            continue
        print(f"   ✅ Instrument in tracked list")
        
        # Check 2: Enough price history?
        if instrument not in strategy.price_history:
            print(f"   ❌ BLOCKED: No price history for {instrument}")
            continue
        
        price_hist = strategy.price_history[instrument]
        print(f"   ✅ Price history exists: {len(price_hist)} bars")
        
        if len(price_hist) < 30:
            print(f"   ❌ BLOCKED: Not enough bars (need 30, have {len(price_hist)})")
            continue
        print(f"   ✅ Enough bars for analysis")
        
        # Check 3: Calculate momentum
        try:
            momentum_period = strategy.momentum_period
            if len(price_hist) < momentum_period:
                print(f"   ❌ BLOCKED: Not enough bars for momentum ({len(price_hist)} < {momentum_period})")
                continue
            
            recent_prices = [p['close'] for p in price_hist[-momentum_period:]]
            momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            print(f"\n   📊 Momentum Calculation:")
            print(f"      Period: {momentum_period} bars")
            print(f"      Start price: {recent_prices[0]:.2f}")
            print(f"      End price: {recent_prices[-1]:.2f}")
            print(f"      Momentum: {momentum*100:.4f}%")
            print(f"      Min required: {strategy.min_momentum*100:.4f}%")
            
            if abs(momentum) < strategy.min_momentum:
                print(f"   ❌ BLOCKED: Momentum too low ({abs(momentum)*100:.4f}% < {strategy.min_momentum*100:.4f}%)")
                continue
            print(f"   ✅ Momentum passes threshold")
            
        except Exception as e:
            print(f"   ❌ ERROR calculating momentum: {e}")
            continue
        
        # Check 4: Calculate ADX
        try:
            adx_period = strategy.adx_period
            if len(price_hist) < adx_period + 1:
                print(f"   ❌ BLOCKED: Not enough bars for ADX ({len(price_hist)} < {adx_period + 1})")
                continue
            
            highs = np.array([p['high'] for p in price_hist[-adx_period-1:]])
            lows = np.array([p['low'] for p in price_hist[-adx_period-1:]])
            closes = np.array([p['close'] for p in price_hist[-adx_period-1:]])
            
            # Calculate TR
            high_low = highs[1:] - lows[1:]
            high_close = np.abs(highs[1:] - closes[:-1])
            low_close = np.abs(lows[1:] - closes[:-1])
            tr = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = np.mean(tr) if len(tr) > 0 else 0
            
            # Calculate +DM and -DM
            high_diff = highs[1:] - highs[:-1]
            low_diff = lows[:-1] - lows[1:]
            
            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
            
            plus_di = 100 * (np.mean(plus_dm) / atr) if atr > 0 else 0
            minus_di = 100 * (np.mean(minus_dm) / atr) if atr > 0 else 0
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
            adx = dx  # Simplified
            
            print(f"\n   📊 ADX Calculation:")
            print(f"      ATR: {atr:.6f}")
            print(f"      +DI: {plus_di:.2f}")
            print(f"      -DI: {minus_di:.2f}")
            print(f"      ADX: {adx:.2f}")
            print(f"      Min required: {strategy.min_adx:.2f}")
            
            if adx < strategy.min_adx:
                print(f"   ❌ BLOCKED: ADX too low ({adx:.2f} < {strategy.min_adx:.2f})")
                continue
            print(f"   ✅ ADX passes threshold")
            
        except Exception as e:
            print(f"   ❌ ERROR calculating ADX: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Check 5: Calculate Volume
        try:
            volume_period = strategy.volume_period
            if len(price_hist) < volume_period:
                print(f"   ❌ BLOCKED: Not enough bars for volume ({len(price_hist)} < {volume_period})")
                continue
            
            recent_volumes = [p['volume'] for p in price_hist[-volume_period:]]
            avg_volume = np.mean(recent_volumes) if recent_volumes else 0
            current_volume = price_hist[-1]['volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            print(f"\n   📊 Volume Analysis:")
            print(f"      Current: {current_volume:.0f}")
            print(f"      Average: {avg_volume:.0f}")
            print(f"      Ratio: {volume_ratio:.2f}")
            print(f"      Min required: {strategy.min_volume:.2f}")
            
            if volume_ratio < strategy.min_volume:
                print(f"   ❌ BLOCKED: Volume too low ({volume_ratio:.2f} < {strategy.min_volume:.2f})")
                continue
            print(f"   ✅ Volume passes threshold")
            
        except Exception as e:
            print(f"   ❌ ERROR calculating volume: {e}")
            continue
        
        # Check 6: Quality Score
        try:
            # Simplified quality score calculation
            adx_score = min(adx / 30.0, 1.0) * 40  # 0-40 points
            momentum_score = min(abs(momentum) / 0.01, 1.0) * 40  # 0-40 points
            volume_score = min(volume_ratio / 2.0, 1.0) * 20  # 0-20 points
            quality_score = adx_score + momentum_score + volume_score
            
            print(f"\n   📊 Quality Score:")
            print(f"      ADX component: {adx_score:.1f}/40")
            print(f"      Momentum component: {momentum_score:.1f}/40")
            print(f"      Volume component: {volume_score:.1f}/20")
            print(f"      Total: {quality_score:.1f}/100")
            print(f"      Min required: {strategy.min_quality_score:.1f}")
            
            if quality_score < strategy.min_quality_score:
                print(f"   ❌ BLOCKED: Quality score too low ({quality_score:.1f} < {strategy.min_quality_score:.1f})")
                continue
            print(f"   ✅ Quality score passes threshold")
            
        except Exception as e:
            print(f"   ❌ ERROR calculating quality score: {e}")
            continue
        
        # Check 7: Confirmations (hidden filter!)
        try:
            confirmations = 0
            if adx >= strategy.min_adx:
                confirmations += 1
            if abs(momentum) >= strategy.min_momentum:
                confirmations += 1
            if volume_ratio >= strategy.min_volume:
                confirmations += 1
            if atr > 0:
                confirmations += 1
            
            print(f"\n   📊 Confirmations Check:")
            print(f"      ADX confirmation: {'✅' if adx >= strategy.min_adx else '❌'}")
            print(f"      Momentum confirmation: {'✅' if abs(momentum) >= strategy.min_momentum else '❌'}")
            print(f"      Volume confirmation: {'✅' if volume_ratio >= strategy.min_volume else '❌'}")
            print(f"      ATR confirmation: {'✅' if atr > 0 else '❌'}")
            print(f"      Total: {confirmations}")
            print(f"      Min required: {strategy.min_confirmations}")
            
            if confirmations < strategy.min_confirmations:
                print(f"   ❌ BLOCKED: Not enough confirmations ({confirmations} < {strategy.min_confirmations})")
                continue
            print(f"   ✅ Confirmations pass threshold")
            
        except Exception as e:
            print(f"   ❌ ERROR checking confirmations: {e}")
            continue
        
        # If we get here, signal SHOULD be generated!
        print(f"\n   ✅✅✅ ALL CHECKS PASSED - SIGNAL SHOULD BE GENERATED! ✅✅✅")
        
        # Now actually call analyze_market to see if it generates
        try:
            signals = strategy.analyze_market(market_data_dict)
            if signals:
                print(f"   ✅ analyze_market RETURNED SIGNAL: {signals[0]}")
            else:
                print(f"   ❌ analyze_market returned NO SIGNAL despite passing all checks!")
                print(f"   ⚠️  THERE IS A BUG IN analyze_market!")
        except Exception as e:
            print(f"   ❌ ERROR calling analyze_market: {e}")
            import traceback
            traceback.print_exc()

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
print("""
If you see:
- ❌ BLOCKED messages: Those filters are rejecting signals
- ✅ ALL CHECKS PASSED but no signal: There's a bug in analyze_market method
- Errors: There's a calculation issue in the indicators

Next steps:
1. Lower the threshold that's blocking most signals
2. Fix any bugs in analyze_market if checks pass but no signal
3. Re-test with lowered thresholds
""")

