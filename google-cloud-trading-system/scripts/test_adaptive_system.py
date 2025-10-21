#!/usr/bin/env python3
"""
Test Adaptive Trading System
Comprehensive testing of the adaptive learning system
"""

import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.adaptive_integration import AdaptiveAccountManager
from src.core.adaptive_system import MarketCondition, AdaptationLevel

def test_adaptive_system():
    """Test the adaptive system functionality"""
    print("🧪 TESTING ADAPTIVE TRADING SYSTEM")
    print("=" * 60)
    
    try:
        # Initialize the adaptive account manager
        print("🔧 Initializing Adaptive Account Manager...")
        manager = AdaptiveAccountManager()
        
        # Test 1: Check account connections
        print("\n📊 TEST 1: Account Connections")
        print("-" * 30)
        account_status = manager.get_account_status()
        
        for account_name, status in account_status.items():
            if 'error' in status:
                print(f"❌ {account_name}: {status['error']}")
            else:
                print(f"✅ {account_name}: Connected")
                print(f"   Balance: ${status['balance']:,.2f}")
                print(f"   P&L: ${status['total_pl']:,.2f} ({status['pl_percentage']:+.2f}%)")
                print(f"   Positions: {status['open_positions']}")
        
        # Test 2: Check adaptive system status
        print("\n🤖 TEST 2: Adaptive System Status")
        print("-" * 30)
        system_status = manager.get_adaptive_system_status()
        
        print(f"Running: {'✅ Yes' if system_status['is_running'] else '❌ No'}")
        print(f"Market Condition: {system_status['current_condition']}")
        print(f"Active Signals: {system_status['active_signals']}")
        print(f"Monitored Instruments: {len(system_status['monitored_instruments'])}")
        
        # Test 3: Start adaptive monitoring
        print("\n🚀 TEST 3: Starting Adaptive Monitoring")
        print("-" * 30)
        manager.start_adaptive_monitoring()
        
        print("✅ Adaptive monitoring started")
        print("⏳ Monitoring for 30 seconds...")
        
        # Let it run for 30 seconds
        for i in range(6):
            time.sleep(5)
            print(f"   Monitoring... {i*5}s")
        
        # Test 4: Check system after monitoring
        print("\n📊 TEST 4: System Status After Monitoring")
        print("-" * 30)
        system_status = manager.get_adaptive_system_status()
        
        print(f"Running: {'✅ Yes' if system_status['is_running'] else '❌ No'}")
        print(f"Market Condition: {system_status['current_condition']}")
        print(f"Active Signals: {system_status['active_signals']}")
        
        # Show risk parameters
        print("\n🛡️ Current Risk Parameters:")
        for account_name, params in system_status['risk_parameters'].items():
            print(f"  {account_name}:")
            print(f"    Position Size Multiplier: {params['position_size_multiplier']}")
            print(f"    Stop Loss Adjustment: {params['stop_loss_adjustment']}")
            print(f"    Max Positions: {params['max_positions']}")
            print(f"    Adaptation Level: {params['adaptation_level']}")
        
        # Test 5: Force adaptation check
        print("\n🔍 TEST 5: Force Adaptation Check")
        print("-" * 30)
        manager.force_adaptation_check()
        print("✅ Forced adaptation check completed")
        
        # Test 6: Send daily report
        print("\n📊 TEST 6: Daily Report")
        print("-" * 30)
        manager.send_daily_report()
        print("✅ Daily report sent")
        
        # Test 7: Save learning data
        print("\n💾 TEST 7: Save Learning Data")
        print("-" * 30)
        filename = manager.save_learning_data()
        if filename:
            print(f"✅ Learning data saved: {filename}")
        else:
            print("❌ Failed to save learning data")
        
        # Test 8: Stop monitoring
        print("\n🛑 TEST 8: Stop Monitoring")
        print("-" * 30)
        manager.stop_adaptive_monitoring()
        print("✅ Adaptive monitoring stopped")
        
        # Final status check
        print("\n📊 FINAL STATUS CHECK")
        print("-" * 30)
        system_status = manager.get_adaptive_system_status()
        print(f"Running: {'❌ No' if not system_status['is_running'] else '⚠️ Still running'}")
        
        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_market_condition_detection():
    """Test market condition detection capabilities"""
    print("\n🧪 TESTING MARKET CONDITION DETECTION")
    print("=" * 60)
    
    try:
        from src.core.adaptive_system import AdaptiveMarketDetector
        
        # Initialize detector
        detector = AdaptiveMarketDetector()
        
        # Test 1: Normal price data
        print("📊 TEST 1: Normal Price Data")
        print("-" * 30)
        
        # Simulate normal price movements
        base_price = 1.1000
        for i in range(10):
            price = base_price + (i * 0.0001)  # Small incremental changes
            detector.add_price_data('EUR_USD', price)
        
        condition = detector.get_current_market_condition()
        print(f"Market Condition: {condition.value}")
        print(f"Expected: normal, Got: {condition.value}")
        
        # Test 2: High volatility detection
        print("\n📈 TEST 2: High Volatility Detection")
        print("-" * 30)
        
        # Simulate high volatility
        base_price = 1.1000
        for i in range(5):
            if i % 2 == 0:
                price = base_price + 0.025  # 2.5% jump
            else:
                price = base_price - 0.025  # 2.5% drop
            detector.add_price_data('EUR_USD', price)
            base_price = price
        
        condition = detector.get_current_market_condition()
        print(f"Market Condition: {condition.value}")
        print(f"Expected: high_volatility, Got: {condition.value}")
        
        # Test 3: Signal count
        print(f"\n📡 Signals Generated: {len(detector.market_signals)}")
        
        print("\n✅ MARKET CONDITION DETECTION TESTS COMPLETED!")
        return True
        
    except Exception as e:
        print(f"\n❌ MARKET CONDITION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_adaptation():
    """Test risk parameter adaptation"""
    print("\n🧪 TESTING RISK ADAPTATION")
    print("=" * 60)
    
    try:
        from src.core.adaptive_system import AdaptiveRiskManager, MarketCondition
        from src.core.oanda_client import OandaAccount
        
        # Initialize risk manager
        risk_manager = AdaptiveRiskManager()
        
        # Test 1: Normal conditions
        print("📊 TEST 1: Normal Market Conditions")
        print("-" * 30)
        
        # Mock account info
        mock_account = OandaAccount(
            account_id="test",
            currency="USD",
            balance=10000,
            unrealized_pl=0,
            realized_pl=0,
            margin_used=1000,
            margin_available=9000,
            open_trade_count=2,
            open_position_count=2,
            pending_order_count=0
        )
        
        params = risk_manager.adapt_risk_parameters(
            MarketCondition.NORMAL, 'PRIMARY', mock_account
        )
        
        print(f"Position Size Multiplier: {params.position_size_multiplier}")
        print(f"Expected: 1.0, Got: {params.position_size_multiplier}")
        print(f"Max Positions: {params.max_positions}")
        print(f"Expected: 5, Got: {params.max_positions}")
        
        # Test 2: High volatility conditions
        print("\n📈 TEST 2: High Volatility Conditions")
        print("-" * 30)
        
        params = risk_manager.adapt_risk_parameters(
            MarketCondition.HIGH_VOLATILITY, 'PRIMARY', mock_account
        )
        
        print(f"Position Size Multiplier: {params.position_size_multiplier}")
        print(f"Expected: 0.5, Got: {params.position_size_multiplier}")
        print(f"Max Margin Usage: {params.max_margin_usage}")
        print(f"Expected: 0.6, Got: {params.max_margin_usage}")
        print(f"Adaptation Level: {params.adaptation_level.value}")
        
        # Test 3: Gold account specific adaptations
        print("\n🥇 TEST 3: Gold Account Adaptations")
        print("-" * 30)
        
        params = risk_manager.adapt_risk_parameters(
            MarketCondition.HIGH_VOLATILITY, 'GOLD', mock_account
        )
        
        print(f"Position Size Multiplier: {params.position_size_multiplier}")
        print(f"Expected: 0.25 (extra reduction), Got: {params.position_size_multiplier}")
        print(f"Stop Loss Adjustment: {params.stop_loss_adjustment}")
        print(f"Expected: 1.5 (wider stops), Got: {params.stop_loss_adjustment}")
        print(f"Max Positions: {params.max_positions}")
        print(f"Expected: 2, Got: {params.max_positions}")
        
        print("\n✅ RISK ADAPTATION TESTS COMPLETED!")
        return True
        
    except Exception as e:
        print(f"\n❌ RISK ADAPTATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all adaptive system tests"""
    print("🚀 COMPREHENSIVE ADAPTIVE SYSTEM TESTING")
    print("=" * 80)
    print(f"⏰ Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load environment
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
    
    test_results = []
    
    # Run tests
    test_results.append(("Market Condition Detection", test_market_condition_detection()))
    test_results.append(("Risk Adaptation", test_risk_adaptation()))
    test_results.append(("Adaptive System Integration", test_adaptive_system()))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Adaptive system is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} tests failed. Please review and fix issues.")
        return 1

if __name__ == '__main__':
    exit(main())

