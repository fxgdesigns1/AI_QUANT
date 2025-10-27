#!/usr/bin/env python3
"""
Find WHY strategies are not generating signals
Test each strategy with current market data
"""
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "google-cloud-trading-system"))

print("="*80)
print("🔍 TESTING WHY STRATEGIES DON'T GENERATE SIGNALS")
print("="*80)

# Load environment
from dotenv import load_dotenv
load_dotenv('google-cloud-trading-system/oanda_config.env')

from src.core.oanda_client import get_oanda_client
from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.strategies.gold_scalping import get_gold_scalping_strategy

print("\n[1/5] Initialize OANDA Client")
print("-"*80)
try:
    oanda = get_oanda_client()
    print("✓ OANDA client initialized")
except Exception as e:
    print(f"✗ FAILURE: {e}")
    sys.exit(1)

print("\n[2/5] Get Current Market Prices")
print("-"*80)
try:
    test_pairs = ['EUR_USD', 'XAU_USD', 'GBP_USD']
    prices = oanda.get_current_prices(test_pairs)
    
    if prices:
        print(f"✓ Got prices for {len(prices)} pairs:")
        for pair, price in prices.items():
            mid = (price.bid + price.ask) / 2
            print(f"   {pair}: {mid:.5f}")
    else:
        print("✗ FAILURE: No prices returned")
        print("   → THIS IS THE PROBLEM - no data = no signals")
        sys.exit(1)
except Exception as e:
    print(f"✗ FAILURE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[3/5] Test Strategy #1 - Momentum Trading")
print("-"*80)
try:
    strategy = get_momentum_trading_strategy()
    print(f"✓ Strategy loaded: {strategy.__class__.__name__}")
    print(f"   Instruments: {strategy.instruments if hasattr(strategy, 'instruments') else 'N/A'}")
    
    # Check if it has the analyze_market method
    if hasattr(strategy, 'analyze_market'):
        print("✓ has analyze_market method")
        
        # Prepare market data in the format it expects
        market_data = {pair: prices[pair] for pair in test_pairs if pair in prices}
        
        print(f"\n   Testing with {len(market_data)} instruments...")
        result = strategy.analyze_market(market_data)
        
        if result:
            print(f"✓ SIGNAL GENERATED: {result}")
            print("\n   ✅ THIS STRATEGY CAN GENERATE SIGNALS!")
        else:
            print("⚠️  No signal (market conditions may not meet criteria)")
            
            # Check why
            print("\n   Checking why no signal:")
            
            # Check price history
            if hasattr(strategy, 'price_history'):
                for inst, hist in strategy.price_history.items():
                    print(f"      {inst}: {len(hist)} price points")
                    if len(hist) < 50:
                        print(f"         ⚠️ Need 50+ points for indicators (has {len(hist)})")
            else:
                print("      ⚠️  No price_history attribute")
                print("         → Strategy cannot calculate indicators without history")
                
            # Check if strategy requires backfill
            if hasattr(strategy, 'min_history_length'):
                print(f"      Min history required: {strategy.min_history_length}")
                
    else:
        print("✗ FAILURE: No analyze_market method")
        print("   Available methods:")
        for method in dir(strategy):
            if not method.startswith('_') and callable(getattr(strategy, method)):
                print(f"      - {method}")
                
except Exception as e:
    print(f"✗ FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("\n[4/5] Test Strategy #2 - Gold Scalping")
print("-"*80)
try:
    strategy = get_gold_scalping_strategy()
    print(f"✓ Strategy loaded: {strategy.__class__.__name__}")
    print(f"   Instruments: {strategy.instruments if hasattr(strategy, 'instruments') else 'N/A'}")
    
    if hasattr(strategy, 'analyze_market'):
        print("✓ has analyze_market method")
        
        # Test with gold only
        if 'XAU_USD' in prices:
            market_data = {'XAU_USD': prices['XAU_USD']}
            
            print(f"\n   Testing with XAU/USD...")
            result = strategy.analyze_market(market_data)
            
            if result:
                print(f"✓ SIGNAL GENERATED: {result}")
                print("\n   ✅ THIS STRATEGY CAN GENERATE SIGNALS!")
            else:
                print("⚠️  No signal (market conditions may not meet criteria)")
                
                # Check why
                print("\n   Checking why no signal:")
                if hasattr(strategy, 'price_history'):
                    hist_len = len(strategy.price_history.get('XAU_USD', []))
                    print(f"      XAU_USD: {hist_len} price points")
                    if hist_len < 50:
                        print(f"         ⚠️ Need 50+ points (has {hist_len})")
                else:
                    print("      ⚠️  No price_history")
        else:
            print("⚠️  XAU_USD price not available")
                
    else:
        print("✗ FAILURE: No analyze_market method")
        
except Exception as e:
    print(f"✗ FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("\n[5/5] Test Historical Data Backfill")
print("-"*80)
try:
    print("Fetching historical candles for EUR/USD...")
    candles = oanda.get_candles('EUR_USD', count=60, granularity='M5')
    
    if candles and 'candles' in candles:
        candle_list = candles['candles']
        print(f"✓ Got {len(candle_list)} candles")
        
        if len(candle_list) >= 50:
            print("✓ Enough history for indicators")
        else:
            print(f"⚠️  Only {len(candle_list)} candles (need 50+)")
            
        # Show sample
        if candle_list:
            latest = candle_list[-1]
            print(f"   Latest candle: {latest['mid']['c']}")
    else:
        print("✗ FAILURE: No candles returned")
        print("   → Cannot build price history")
        
except Exception as e:
    print(f"✗ FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("🔍 DIAGNOSIS")
print("="*80)

print("\nMost likely problems:")
print("\n1. ❌ INSUFFICIENT PRICE HISTORY")
print("   - Strategies need 50+ price points to calculate indicators")
print("   - Scanner may not be backfilling properly on start")
print("   - Solution: Run backfill before first scan")

print("\n2. ❌ MARKET CONDITIONS DON'T MEET CRITERIA")
print("   - Strategies may be TOO STRICT")
print("   - No clear trends right now")
print("   - Solution: Wait for London/NY overlap (1-5 PM)")

print("\n3. ❌ SCANNER NOT ACTUALLY RUNNING")
print("   - main.py must be running for APScheduler to work")
print("   - Check: ps aux | grep main.py")
print("   - Solution: cd google-cloud-trading-system && python3 main.py")

print("\n" + "="*80)
print("💡 IMMEDIATE FIX")
print("="*80)

print("\n1. Start the main system:")
print("   cd google-cloud-trading-system")
print("   python3 main.py")

print("\n2. Monitor logs for signals:")
print("   tail -f logs/trading_system.log | grep -E 'SIGNAL|signals'")

print("\n3. If still no signals, check during peak hours:")
print("   - Best time: 1:00-5:00 PM London (London/NY overlap)")
print("   - Current time:", datetime.now().strftime('%H:%M %Z'))

print("\n4. Force a test trade:")
print("   cd google-cloud-trading-system")
print("   python3 tmp_place_gold_demo.py")

print("\n" + "="*80)


