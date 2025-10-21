#!/usr/bin/env python3
"""
ICT OTE Strategy System Test
Quick test to verify all components work correctly
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("🔍 Testing imports...")
        
        # Test core modules
        from ict_ote_optimizer import ICTOTEOptimizer, OptimizationConfig
        from ict_ote_backtester import ICTOTEBacktester, BacktestConfig
        from ict_ote_monte_carlo import ICTOTEMonteCarlo, MonteCarloConfig
        from ict_ote_comprehensive_optimizer import ICTOTEComprehensiveOptimizer, ComprehensiveConfig
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_optimizer():
    """Test the optimizer component"""
    try:
        print("🔍 Testing optimizer...")
        
        from ict_ote_optimizer import ICTOTEOptimizer, OptimizationConfig
        
        config = OptimizationConfig(
            instruments=['XAU_USD', 'EUR_USD'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            initial_balance=10000.0
        )
        
        optimizer = ICTOTEOptimizer(config)
        print("✅ Optimizer created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Optimizer error: {e}")
        return False

def test_backtester():
    """Test the backtester component"""
    try:
        print("🔍 Testing backtester...")
        
        from ict_ote_backtester import ICTOTEBacktester, BacktestConfig
        
        config = BacktestConfig(
            instruments=['XAU_USD', 'EUR_USD'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            initial_balance=10000.0
        )
        
        backtester = ICTOTEBacktester(config)
        print("✅ Backtester created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Backtester error: {e}")
        return False

def test_monte_carlo():
    """Test the Monte Carlo component"""
    try:
        print("🔍 Testing Monte Carlo simulator...")
        
        from ict_ote_monte_carlo import ICTOTEMonteCarlo, MonteCarloConfig
        
        config = MonteCarloConfig(
            n_simulations=10,  # Small number for testing
            confidence_levels=[0.05, 0.5, 0.95]
        )
        
        monte_carlo = ICTOTEMonteCarlo(config)
        print("✅ Monte Carlo simulator created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Monte Carlo error: {e}")
        return False

def test_comprehensive_optimizer():
    """Test the comprehensive optimizer"""
    try:
        print("🔍 Testing comprehensive optimizer...")
        
        from ict_ote_comprehensive_optimizer import ICTOTEComprehensiveOptimizer, ComprehensiveConfig
        
        config = ComprehensiveConfig(
            instruments=['XAU_USD', 'EUR_USD'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            initial_balance=10000.0,
            n_optimization_combinations=5,  # Small number for testing
            n_monte_carlo_simulations=10
        )
        
        optimizer = ICTOTEComprehensiveOptimizer(config)
        print("✅ Comprehensive optimizer created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive optimizer error: {e}")
        return False

def test_parameter_generation():
    """Test parameter generation"""
    try:
        print("🔍 Testing parameter generation...")
        
        from ict_ote_optimizer import ICTOTEOptimizer, OptimizationConfig
        
        config = OptimizationConfig(
            instruments=['XAU_USD'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            initial_balance=10000.0
        )
        
        optimizer = ICTOTEOptimizer(config)
        combinations = optimizer.generate_parameter_combinations(n_combinations=5)
        
        if len(combinations) == 5:
            print("✅ Parameter generation working correctly")
            return True
        else:
            print(f"❌ Expected 5 combinations, got {len(combinations)}")
            return False
        
    except Exception as e:
        print(f"❌ Parameter generation error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 ICT OTE Strategy System Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Optimizer", test_optimizer),
        ("Backtester", test_backtester),
        ("Monte Carlo", test_monte_carlo),
        ("Comprehensive Optimizer", test_comprehensive_optimizer),
        ("Parameter Generation", test_parameter_generation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed")
        else:
            print(f"❌ {test_name} test failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for optimization.")
        print("\n🚀 To run the full optimization:")
        print("   python run_ict_ote_optimization.py")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        print("   Make sure all dependencies are installed:")
        print("   pip install -r requirements_ict_ote.txt")

if __name__ == "__main__":
    main()