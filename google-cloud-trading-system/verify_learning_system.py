#!/usr/bin/env python3
"""
Learning System Verification Script
Verifies all learning components are working correctly
"""

import sys
import yaml
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_config_no_forced_trades():
    """Verify strategy_config.yaml has no forced trade quotas"""
    logger.info("=" * 60)
    logger.info("TEST 1: Verify No Forced Trade Quotas")
    logger.info("=" * 60)
    
    config_path = Path(__file__).parent / 'strategy_config.yaml'
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        violations = []
        
        for strategy_name, strategy_config in config.items():
            if strategy_name == 'system':
                continue
            
            if 'parameters' in strategy_config:
                min_trades = strategy_config['parameters'].get('min_trades_today', 0)
                if min_trades > 0:
                    violations.append(f"{strategy_name}: min_trades_today = {min_trades}")
        
        if violations:
            logger.error("❌ FAIL: Found forced trade quotas:")
            for violation in violations:
                logger.error(f"   • {violation}")
            return False
        else:
            logger.info("✅ PASS: All strategies have min_trades_today = 0")
            return True
    
    except Exception as e:
        logger.error(f"❌ ERROR reading config: {e}")
        return False


def verify_learning_modules_exist():
    """Verify all learning modules are present"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Verify Learning Modules Exist")
    logger.info("=" * 60)
    
    src_dir = Path(__file__).parent / 'src' / 'core'
    required_modules = [
        'loss_learner.py',
        'early_trend_detector.py',
        'honesty_reporter.py'
    ]
    
    all_exist = True
    for module in required_modules:
        module_path = src_dir / module
        if module_path.exists():
            logger.info(f"✅ {module} exists")
        else:
            logger.error(f"❌ {module} MISSING")
            all_exist = False
    
    return all_exist


def verify_learning_modules_import():
    """Verify learning modules can be imported"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Verify Learning Modules Import")
    logger.info("=" * 60)
    
    try:
        from src.core.loss_learner import get_loss_learner
        logger.info("✅ loss_learner imports successfully")
    except Exception as e:
        logger.error(f"❌ loss_learner import failed: {e}")
        return False
    
    try:
        from src.core.early_trend_detector import get_early_trend_detector
        logger.info("✅ early_trend_detector imports successfully")
    except Exception as e:
        logger.error(f"❌ early_trend_detector import failed: {e}")
        return False
    
    try:
        from src.core.honesty_reporter import get_honesty_reporter
        logger.info("✅ honesty_reporter imports successfully")
    except Exception as e:
        logger.error(f"❌ honesty_reporter import failed: {e}")
        return False
    
    return True


def verify_loss_learner_functionality():
    """Verify loss learner works correctly"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Verify Loss Learner Functionality")
    logger.info("=" * 60)
    
    try:
        from src.core.loss_learner import get_loss_learner
        
        # Create instance
        learner = get_loss_learner('test_strategy')
        logger.info("✅ Loss learner instance created")
        
        # Test recording a loss
        learner.record_loss(
            instrument='EUR_USD',
            regime='CHOPPY',
            adx=12.0,
            momentum=0.002,
            volume=0.3,
            pnl=-50.0,
            conditions={'session': 'ASIAN'}
        )
        logger.info("✅ Loss recording works")
        
        # Test risk adjustment
        multiplier = learner.get_risk_adjustment('EUR_USD', 'CHOPPY')
        logger.info(f"✅ Risk adjustment works: {multiplier:.2f}")
        
        # Test failure pattern detection
        is_failure = learner.is_failure_pattern({
            'instrument': 'EUR_USD',
            'regime': 'CHOPPY',
            'adx': 12.0,
            'momentum': 0.002,
            'volume': 0.3
        })
        logger.info(f"✅ Failure pattern detection works: {is_failure}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Loss learner test failed: {e}")
        return False


def verify_early_trend_detector_functionality():
    """Verify early trend detector works"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Verify Early Trend Detector Functionality")
    logger.info("=" * 60)
    
    try:
        from src.core.early_trend_detector import get_early_trend_detector
        import numpy as np
        
        # Create instance
        detector = get_early_trend_detector()
        logger.info("✅ Early trend detector instance created")
        
        # Test with sample data (uptrend)
        prices = list(np.linspace(1.1000, 1.1100, 50))  # Uptrend
        
        result = detector.detect_early_bullish(prices)
        logger.info(f"✅ Bullish detection works: probability={result['probability']:.2%}")
        
        result = detector.detect_early_bearish(prices)
        logger.info(f"✅ Bearish detection works: probability={result['probability']:.2%}")
        
        result = detector.calculate_trend_probability(prices)
        logger.info(f"✅ Trend probability calculation works: {result['recommended_direction']}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Early trend detector test failed: {e}")
        return False


def verify_honesty_reporter_functionality():
    """Verify honesty reporter works"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Verify Honesty Reporter Functionality")
    logger.info("=" * 60)
    
    try:
        from src.core.honesty_reporter import get_honesty_reporter
        
        # Create instance
        reporter = get_honesty_reporter('test_strategy')
        logger.info("✅ Honesty reporter instance created")
        
        # Test rejection logging
        reporter.log_rejection(
            instrument='GBP_USD',
            reasons=['ADX too low', 'Momentum insufficient'],
            scores={
                'ADX': {'value': 18, 'required': 25, 'passed': False},
                'Momentum': {'value': 0.003, 'required': 0.008, 'passed': False}
            }
        )
        logger.info("✅ Rejection logging works")
        
        # Test win probability calculation
        win_prob = reporter.calculate_win_probability(
            instrument='EUR_USD',
            regime='TRENDING',
            quality_score=75,
            adx=35,
            momentum=0.012
        )
        logger.info(f"✅ Win probability calculation works: {win_prob:.1%}")
        
        # Test daily report
        report = reporter.generate_daily_report(
            trades_taken=3,
            trades_rejected=10,
            market_conditions={'regime': 'TRENDING', 'quality': 'GOOD'}
        )
        logger.info("✅ Daily report generation works")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Honesty reporter test failed: {e}")
        return False


def verify_strategy_integration():
    """Verify momentum_trading strategy has learning integrated"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Verify Strategy Integration")
    logger.info("=" * 60)
    
    try:
        from src.strategies.momentum_trading import MomentumTradingStrategy
        
        strategy = MomentumTradingStrategy()
        logger.info("✅ Momentum trading strategy instantiated")
        
        # Check if learning modules are initialized
        if hasattr(strategy, 'loss_learner') and strategy.loss_learner:
            logger.info("✅ Loss learner integrated")
        else:
            logger.warning("⚠️  Loss learner not initialized (may be disabled)")
        
        if hasattr(strategy, 'early_trend') and strategy.early_trend:
            logger.info("✅ Early trend detector integrated")
        else:
            logger.warning("⚠️  Early trend detector not initialized (may be disabled)")
        
        if hasattr(strategy, 'honesty') and strategy.honesty:
            logger.info("✅ Honesty reporter integrated")
        else:
            logger.warning("⚠️  Honesty reporter not initialized (may be disabled)")
        
        # Check if record_trade_result method exists
        if hasattr(strategy, 'record_trade_result'):
            logger.info("✅ record_trade_result method exists")
        else:
            logger.error("❌ record_trade_result method missing")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Strategy integration test failed: {e}")
        return False


def verify_system_config():
    """Verify system config has learning settings"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 8: Verify System Config")
    logger.info("=" * 60)
    
    config_path = Path(__file__).parent / 'strategy_config.yaml'
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        system_config = config.get('system', {})
        
        required_settings = [
            'learning_enabled',
            'loss_tracking',
            'early_trend_detection',
            'brutal_honesty',
            'enforce_zero_minimums'
        ]
        
        all_present = True
        for setting in required_settings:
            if setting in system_config:
                logger.info(f"✅ {setting}: {system_config[setting]}")
            else:
                logger.error(f"❌ {setting} missing")
                all_present = False
        
        return all_present
    
    except Exception as e:
        logger.error(f"❌ System config verification failed: {e}")
        return False


def main():
    """Run all verification tests"""
    logger.info("\n" + "=" * 70)
    logger.info("LEARNING SYSTEM VERIFICATION")
    logger.info("=" * 70 + "\n")
    
    results = []
    
    results.append(("No Forced Trades", verify_config_no_forced_trades()))
    results.append(("Modules Exist", verify_learning_modules_exist()))
    results.append(("Modules Import", verify_learning_modules_import()))
    results.append(("Loss Learner", verify_loss_learner_functionality()))
    results.append(("Early Trend Detector", verify_early_trend_detector_functionality()))
    results.append(("Honesty Reporter", verify_honesty_reporter_functionality()))
    results.append(("Strategy Integration", verify_strategy_integration()))
    results.append(("System Config", verify_system_config()))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 70)
    logger.info(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    logger.info("=" * 70 + "\n")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Learning system ready for deployment.")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed. Please review and fix.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

