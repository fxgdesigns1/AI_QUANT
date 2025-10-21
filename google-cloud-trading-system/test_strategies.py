#!/usr/bin/env python3
"""
Test Strategies
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('oanda_config.env')

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.multi_account_data_feed import get_multi_account_data_feed
from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
from src.strategies.gold_scalping import get_gold_scalping_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy

def test_strategies():
    """Test strategy signal generation"""
    print("🔍 Testing Strategies...")
    print("=" * 50)
    
    try:
        # Get data feed
        data_feed = get_multi_account_data_feed()
        data_feed.start()
        
        # Wait for data
        import time
        time.sleep(3)
        
        # Get strategies
        ultra_strict = get_ultra_strict_forex_strategy()
        gold_scalping = get_gold_scalping_strategy()
        momentum_trading = get_momentum_trading_strategy()
        
        # Test Ultra Strict Forex
        print("\n🎯 Testing Ultra Strict Forex Strategy...")
        primary_market_data = data_feed.get_market_data('101-004-30719775-001')
        ultra_signals = ultra_strict.analyze_market(primary_market_data)
        print(f"   Signals generated: {len(ultra_signals)}")
        for signal in ultra_signals:
            print(f"   📈 {signal.instrument} {signal.side.value} - Confidence: {signal.confidence:.2f}")
            print(f"      Entry: {signal.units} units, SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}")
        
        # Test Gold Scalping
        print("\n💰 Testing Gold Scalping Strategy...")
        gold_market_data = data_feed.get_market_data('101-004-30719775-002')
        gold_signals = gold_scalping.analyze_market(gold_market_data)
        print(f"   Signals generated: {len(gold_signals)}")
        for signal in gold_signals:
            print(f"   📈 {signal.instrument} {signal.side.value} - Confidence: {signal.confidence:.2f}")
            print(f"      Entry: {signal.units} units, SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}")
        
        # Test Momentum Trading
        print("\n📈 Testing Momentum Trading Strategy...")
        alpha_market_data = data_feed.get_market_data('101-004-30719775-003')
        momentum_signals = momentum_trading.analyze_market(alpha_market_data)
        print(f"   Signals generated: {len(momentum_signals)}")
        for signal in momentum_signals:
            print(f"   📈 {signal.instrument} {signal.side.value} - Confidence: {signal.confidence:.2f}")
            print(f"      Entry: {signal.units} units, SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_strategies()
    if success:
        print("\n✅ Strategy test passed!")
    else:
        print("\n❌ Strategy test failed!")
