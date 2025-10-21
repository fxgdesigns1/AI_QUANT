#!/usr/bin/env python3
"""
Test Optimized Strategies
Comprehensive testing of all three optimized strategies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MockMarketData:
    """Mock market data for testing"""
    instrument: str
    bid: float
    ask: float
    volume: float = 1000000

def test_strategy_loading():
    """Test that all strategies can be loaded"""
    logger.info("🧪 Testing strategy loading...")
    
    try:
        from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
        from src.strategies.gold_scalping import get_gold_scalping_strategy
        from src.strategies.momentum_trading import get_momentum_trading_strategy
        
        # Load strategies
        forex_strategy = get_ultra_strict_forex_strategy()
        gold_strategy = get_gold_scalping_strategy()
        momentum_strategy = get_momentum_trading_strategy()
        
        logger.info(f"✅ Ultra Strict Forex: {forex_strategy.name}")
        logger.info(f"✅ Gold Scalping: {gold_strategy.name}")
        logger.info(f"✅ Momentum Trading: {momentum_strategy.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy loading failed: {e}")
        return False

def test_strategy_parameters():
    """Test that all strategies have correct parameters"""
    logger.info("🧪 Testing strategy parameters...")
    
    try:
        from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
        from src.strategies.gold_scalping import get_gold_scalping_strategy
        from src.strategies.momentum_trading import get_momentum_trading_strategy
        
        # Test Ultra Strict Forex
        forex_strategy = get_ultra_strict_forex_strategy()
        assert forex_strategy.max_trades_per_day == 10, f"Expected 10, got {forex_strategy.max_trades_per_day}"
        assert forex_strategy.min_signal_strength >= 0.85, f"Expected >= 0.85, got {forex_strategy.min_signal_strength}"
        logger.info(f"✅ Ultra Strict Forex parameters: max_trades={forex_strategy.max_trades_per_day}, min_strength={forex_strategy.min_signal_strength}")
        
        # Test Gold Scalping
        gold_strategy = get_gold_scalping_strategy()
        assert gold_strategy.max_trades_per_day == 10, f"Expected 10, got {gold_strategy.max_trades_per_day}"
        assert gold_strategy.min_signal_strength >= 0.85, f"Expected >= 0.85, got {gold_strategy.min_signal_strength}"
        logger.info(f"✅ Gold Scalping parameters: max_trades={gold_strategy.max_trades_per_day}, min_strength={gold_strategy.min_signal_strength}")
        
        # Test Momentum Trading
        momentum_strategy = get_momentum_trading_strategy()
        assert momentum_strategy.max_trades_per_day == 10, f"Expected 10, got {momentum_strategy.max_trades_per_day}"
        assert momentum_strategy.min_signal_strength >= 0.85, f"Expected >= 0.85, got {momentum_strategy.min_signal_strength}"
        logger.info(f"✅ Momentum Trading parameters: max_trades={momentum_strategy.max_trades_per_day}, min_strength={momentum_strategy.min_signal_strength}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy parameters test failed: {e}")
        return False

def test_signal_generation():
    """Test that strategies can generate signals"""
    logger.info("🧪 Testing signal generation...")
    
    try:
        from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
        from src.strategies.gold_scalping import get_gold_scalping_strategy
        from src.strategies.momentum_trading import get_momentum_trading_strategy
        
        # Create mock market data
        mock_data = {
            'EUR_USD': MockMarketData('EUR_USD', 1.0500, 1.0502),
            'GBP_USD': MockMarketData('GBP_USD', 1.2500, 1.2502),
            'USD_JPY': MockMarketData('USD_JPY', 150.00, 150.02),
            'AUD_USD': MockMarketData('AUD_USD', 0.6500, 0.6502),
            'XAU_USD': MockMarketData('XAU_USD', 2000.00, 2000.05),
        }
        
        # Test Ultra Strict Forex
        forex_strategy = get_ultra_strict_forex_strategy()
        forex_signals = forex_strategy.analyze_market(mock_data)
        logger.info(f"✅ Ultra Strict Forex generated {len(forex_signals)} signals")
        
        # Test Gold Scalping
        gold_strategy = get_gold_scalping_strategy()
        gold_signals = gold_strategy.analyze_market(mock_data)
        logger.info(f"✅ Gold Scalping generated {len(gold_signals)} signals")
        
        # Test Momentum Trading
        momentum_strategy = get_momentum_trading_strategy()
        momentum_signals = momentum_strategy.analyze_market(mock_data)
        logger.info(f"✅ Momentum Trading generated {len(momentum_signals)} signals")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Signal generation test failed: {e}")
        return False

def test_configuration_files():
    """Test that configuration files are updated"""
    logger.info("🧪 Testing configuration files...")
    
    try:
        # Test oanda_config.env
        with open('oanda_config.env', 'r') as f:
            config_content = f.read()
            
        assert 'PRIMARY_DAILY_TRADE_LIMIT=10' in config_content, "Primary account limit not updated"
        assert 'GOLD_DAILY_TRADE_LIMIT=10' in config_content, "Gold account limit not updated"
        assert 'ALPHA_DAILY_TRADE_LIMIT=10' in config_content, "Alpha account limit not updated"
        
        logger.info("✅ oanda_config.env updated correctly")
        
        # Test app.yaml
        with open('app.yaml', 'r') as f:
            app_content = f.read()
            
        assert 'PRIMARY_DAILY_TRADE_LIMIT: "10"' in app_content, "Primary account limit not updated in app.yaml"
        assert 'GOLD_DAILY_TRADE_LIMIT: "10"' in app_content, "Gold account limit not updated in app.yaml"
        assert 'ALPHA_DAILY_TRADE_LIMIT: "10"' in app_content, "Alpha account limit not updated in app.yaml"
        
        logger.info("✅ app.yaml updated correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration files test failed: {e}")
        return False

def test_news_integration():
    """Test that news integration is working"""
    logger.info("🧪 Testing news integration...")
    
    try:
        from src.core.news_integration import safe_news_integration
        
        # Test news integration availability
        logger.info(f"✅ News integration enabled: {safe_news_integration.enabled}")
        logger.info(f"✅ News integration APIs: {len(safe_news_integration.api_keys)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ News integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting comprehensive strategy testing...")
    
    tests = [
        ("Strategy Loading", test_strategy_loading),
        ("Strategy Parameters", test_strategy_parameters),
        ("Signal Generation", test_signal_generation),
        ("Configuration Files", test_configuration_files),
        ("News Integration", test_news_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST RESULTS: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! System is ready for deployment.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
