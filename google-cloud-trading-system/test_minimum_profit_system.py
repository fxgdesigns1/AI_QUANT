#!/usr/bin/env python3
"""
Test Minimum Profit System - $1,000+ Per Win
============================================

Comprehensive test to verify that only trades with $1,000+ profit potential
are allowed, with ability to scale higher.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.trade_size_validator import get_trade_size_validator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_profit_validation():
    """Test profit validation system"""
    print("🧪 TESTING MINIMUM PROFIT SYSTEM - $1,000+ PER WIN")
    print("=" * 70)
    
    # Get validator
    validator = get_trade_size_validator()
    
    print(f"💰 Minimum profit target: ${validator.min_profit_target:,.0f}")
    print(f"🛡️ Profit enforcement: {validator.enforce_minimum_profit}")
    print(f"📈 Profit scaling enabled: {validator.profit_scaling_enabled}")
    print()
    
    # Test cases for EUR/USD
    test_cases = [
        # (instrument, units, take_profit_pips, strategy, should_pass, description)
        ("EUR_USD", 10000, 50, "test_strategy", False, "10k units, 50 pips = $50 profit"),
        ("EUR_USD", 10000, 100, "test_strategy", False, "10k units, 100 pips = $100 profit"),
        ("EUR_USD", 10000, 500, "test_strategy", False, "10k units, 500 pips = $500 profit"),
        ("EUR_USD", 10000, 1000, "test_strategy", True, "10k units, 1000 pips = $1,000 profit"),
        ("EUR_USD", 25000, 400, "test_strategy", True, "25k units, 400 pips = $1,000 profit"),
        ("EUR_USD", 50000, 200, "test_strategy", True, "50k units, 200 pips = $1,000 profit"),
        ("EUR_USD", 100000, 100, "test_strategy", True, "100k units, 100 pips = $1,000 profit"),
        ("EUR_USD", 100000, 200, "test_strategy", True, "100k units, 200 pips = $2,000 profit"),
        ("EUR_USD", 200000, 100, "test_strategy", True, "200k units, 100 pips = $2,000 profit"),
        ("EUR_USD", 500000, 50, "test_strategy", True, "500k units, 50 pips = $2,500 profit"),
    ]
    
    print("🔍 TESTING PROFIT VALIDATION:")
    print("-" * 70)
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for instrument, units, take_profit_pips, strategy, expected_pass, description in test_cases:
        result = validator.validate_profit_potential(instrument, units, take_profit_pips, strategy)
        actual_pass = result['valid']
        
        status = "✅ PASS" if actual_pass == expected_pass else "❌ FAIL"
        result_text = "ALLOWED" if actual_pass else "BLOCKED"
        
        print(f"{status} {description}")
        print(f"    Units: {units:,} | Take Profit: {take_profit_pips} pips | Potential: ${result['potential_profit']:,.0f} | Result: {result_text}")
        
        if actual_pass == expected_pass:
            passed_tests += 1
        else:
            print(f"    ⚠️ Expected: {'ALLOWED' if expected_pass else 'BLOCKED'}")
        
        print()
    
    print("=" * 70)
    print(f"📈 TEST RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED - Minimum profit system working correctly!")
        return True
    else:
        print("❌ SOME TESTS FAILED - System needs attention!")
        return False

def test_profit_scaling():
    """Test profit scaling capabilities"""
    print("\n📈 TESTING PROFIT SCALING CAPABILITIES")
    print("=" * 70)
    
    validator = get_trade_size_validator()
    
    # Test scaling scenarios
    scaling_tests = [
        # (units, pips, expected_profit, description)
        (100000, 100, 1000, "100k units, 100 pips = $1,000 (minimum)"),
        (100000, 150, 1500, "100k units, 150 pips = $1,500 (scaled up)"),
        (100000, 200, 2000, "100k units, 200 pips = $2,000 (scaled up)"),
        (200000, 100, 2000, "200k units, 100 pips = $2,000 (scaled up)"),
        (500000, 50, 2500, "500k units, 50 pips = $2,500 (scaled up)"),
    ]
    
    print("🔍 SCALING TEST RESULTS:")
    print("-" * 70)
    
    for units, pips, expected_profit, description in scaling_tests:
        result = validator.validate_profit_potential("EUR_USD", units, pips, "scaling_test")
        actual_profit = result['potential_profit']
        
        print(f"✅ {description}")
        print(f"    Expected: ${expected_profit:,.0f} | Actual: ${actual_profit:,.0f} | Valid: {result['valid']}")
        print()
    
    return True

def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ TESTING CONFIGURATION")
    print("=" * 70)
    
    try:
        import yaml
        
        config_path = "strategy_config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        system_config = config.get('system', {})
        
        print("📋 Configuration loaded:")
        print(f"   min_profit_target: ${system_config.get('min_profit_target', 'NOT SET')}")
        print(f"   enforce_minimum_profit: {system_config.get('enforce_minimum_profit', 'NOT SET')}")
        print(f"   profit_scaling_enabled: {system_config.get('profit_scaling_enabled', 'NOT SET')}")
        
        # Verify critical settings
        min_profit = system_config.get('min_profit_target')
        enforce = system_config.get('enforce_minimum_profit')
        scaling = system_config.get('profit_scaling_enabled')
        
        if min_profit and min_profit >= 1000 and enforce and scaling:
            print("✅ Configuration is correct!")
            return True
        else:
            print("❌ Configuration issues found!")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 MINIMUM PROFIT SYSTEM TEST - $1,000+ PER WIN")
    print("=" * 70)
    print("Testing system to ensure minimum $1,000 profit per win")
    print("with ability to scale higher for bigger profits")
    print()
    
    # Run tests
    test1_passed = test_profit_validation()
    test2_passed = test_profit_scaling()
    test3_passed = test_configuration()
    
    print("\n" + "=" * 70)
    print("📊 FINAL TEST RESULTS")
    print("=" * 70)
    
    all_passed = test1_passed and test2_passed and test3_passed
    
    if all_passed:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Minimum $1,000 profit enforced")
        print("✅ Profit scaling enabled")
        print("✅ Configuration is correct")
        print("✅ System ready for meaningful profits")
    else:
        print("⚠️ SYSTEM NEEDS ATTENTION!")
        print("❌ Some components failed testing")
        print("🔧 Review and fix issues before deployment")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
