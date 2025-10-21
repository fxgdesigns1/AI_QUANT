#!/usr/bin/env python3
"""
Pre-Deployment Validation Check
Validates ALL active strategies before allowing deployment
Prevents deploying broken configurations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from validate_strategy import StrategyValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pre_deployment_validation():
    """
    MUST pass this before any deployment!
    Validates all 10 active strategies
    """
    
    print("🔍 PRE-DEPLOYMENT VALIDATION - ALL STRATEGIES")
    print("=" * 100)
    print()
    
    # Define all active strategies to validate
    strategies_to_validate = [
        {
            'name': 'momentum_trading',
            'display': '📈 Momentum Multi-Pair',
            'module': 'src.strategies.momentum_trading',
            'function': 'get_momentum_trading_strategy',
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
        },
        {
            'name': 'gold_scalping',
            'display': '🥇 Gold Scalping',
            'module': 'src.strategies.gold_scalping',
            'function': 'get_gold_scalping_strategy',
            'instruments': ['XAU_USD']
        },
        {
            'name': 'ultra_strict_forex',
            'display': '💱 Ultra Strict Fx',
            'module': 'src.strategies.ultra_strict_forex',
            'function': 'get_ultra_strict_forex_strategy',
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        },
        {
            'name': 'gbp_usd_5m_rank_1',
            'display': '🏆 Strategy #1',
            'module': 'src.strategies.gbp_usd_optimized',
            'function': 'get_strategy_rank_1',
            'instruments': ['GBP_USD']
        },
        {
            'name': 'gbp_usd_5m_rank_2',
            'display': '🥈 Strategy #2',
            'module': 'src.strategies.gbp_usd_optimized',
            'function': 'get_strategy_rank_2',
            'instruments': ['GBP_USD', 'GBP_JPY']
        },
        {
            'name': 'gbp_usd_5m_rank_3',
            'display': '🥉 Strategy #3',
            'module': 'src.strategies.gbp_usd_optimized',
            'function': 'get_strategy_rank_3',
            'instruments': ['GBP_USD', 'EUR_JPY']
        },
        {
            'name': 'champion_75wr',
            'display': '🏆 75% WR Champion',
            'module': 'src.strategies.champion_75wr',
            'function': 'get_champion_75wr_strategy',
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        },
        {
            'name': 'ultra_strict_v2',
            'display': '💎 Ultra Strict V2',
            'module': 'src.strategies.ultra_strict_v2',
            'function': 'get_ultra_strict_v2_strategy',
            'instruments': ['EUR_USD', 'USD_JPY', 'AUD_USD']
        },
        {
            'name': 'momentum_v2',
            'display': '⚡ Momentum V2',
            'module': 'src.strategies.momentum_v2',
            'function': 'get_momentum_v2_strategy',
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        },
        {
            'name': 'all_weather_70wr',
            'display': '🌦️ All-Weather 70WR',
            'module': 'src.strategies.all_weather_70wr',
            'function': 'get_all_weather_70wr_strategy',
            'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        }
    ]
    
    all_passed = True
    report = []
    total_signals_4h = 0
    total_signals_day_est = 0
    
    print("Validating each strategy against last 4 hours...")
    print()
    
    for strat_config in strategies_to_validate:
        strategy_name = strat_config['name']
        display_name = strat_config['display']
        
        print(f"Validating {display_name}...", end=" ")
        
        try:
            # Import strategy
            module_path = strat_config['module']
            function_name = strat_config['function']
            
            module = __import__(module_path, fromlist=[function_name])
            get_strategy = getattr(module, function_name)
            strategy = get_strategy()
            
            # Get historical data for this strategy's instruments
            validator = StrategyValidator(strategy_name, lookback_hours=4)
            historical_data = validator.get_historical_data(
                strat_config['instruments'], 
                hours=4
            )
            
            # Run backtest
            results = validator.run_strategy_backtest(strategy, historical_data)
            
            # Validate
            validation = validator.validate_parameters(results)
            
            trades_4h = results['signals_generated']
            trades_day_est = validation['estimated_per_day']
            avg_quality = results['avg_quality']
            
            total_signals_4h += trades_4h
            total_signals_day_est += trades_day_est
            
            # Determine status
            if 3 <= trades_day_est <= 10:
                status = "✅ PASS"
                passed = True
            elif trades_day_est < 3:
                if trades_day_est == 0:
                    status = "❌ FAIL (ZERO trades)"
                else:
                    status = "⚠️ WARN (too few)"
                passed = False
            else:
                status = "⚠️ WARN (may overtrade)"
                passed = True  # Warning but not fail
            
            report.append({
                'display': display_name,
                'trades_4h': trades_4h,
                'trades_day_est': trades_day_est,
                'avg_quality': avg_quality,
                'status': status,
                'passed': passed,
                'adjustment': validation['adjustment_needed']
            })
            
            all_passed = all_passed and passed
            
            print(f"{status}")
            
        except Exception as e:
            logger.error(f"❌ Error validating {display_name}: {e}")
            report.append({
                'display': display_name,
                'trades_4h': 0,
                'trades_day_est': 0,
                'avg_quality': 0,
                'status': "❌ ERROR",
                'passed': False,
                'adjustment': str(e)[:50]
            })
            all_passed = False
            print(f"❌ ERROR")
    
    # Print detailed report
    print()
    print("=" * 100)
    print("VALIDATION REPORT - LAST 4 HOURS LOOKBACK")
    print("=" * 100)
    print(f"{'Strategy':<30} {'Trades (4h)':<15} {'Est/Day':<12} {'Quality':<10} {'Status'}")
    print("-" * 100)
    
    for r in report:
        quality_str = f"{r['avg_quality']:.1f}" if r['avg_quality'] > 0 else "N/A"
        print(f"{r['display']:<30} {r['trades_4h']:<15} {r['trades_day_est']:<12.1f} {quality_str:<10} {r['status']}")
    
    print("-" * 100)
    print(f"{'TOTAL (All Strategies)':<30} {total_signals_4h:<15} {total_signals_day_est:<12.1f} {'':<10} {'8-10 should pass'}")
    print("=" * 100)
    print()
    
    # Summary
    passed_count = sum(1 for r in report if r['passed'])
    failed_count = len(report) - passed_count
    
    print("📊 SUMMARY:")
    print("-" * 100)
    print(f"Strategies Validated: {len(report)}")
    print(f"Passed: {passed_count}")
    print(f"Failed/Warned: {failed_count}")
    print(f"Total Signals (4h): {total_signals_4h}")
    print(f"Estimated/Day (All): {total_signals_day_est:.1f} trades")
    print()
    
    # Overall validation
    if all_passed and total_signals_day_est >= 30:  # 10 strategies × 3 minimum
        print("✅ VALIDATION: PASSED")
        print("   All strategies validated successfully")
        print(f"   Expected daily output: {total_signals_day_est:.0f} trades across all strategies")
        print("   Safe to deploy to production!")
        result_code = 0
    elif total_signals_day_est < 20:
        print("❌ VALIDATION: CRITICAL FAIL")
        print(f"   Only {total_signals_day_est:.0f} trades/day expected (need 30+)")
        print("   Strategies are TOO STRICT - will barely trade")
        print()
        print("REQUIRED ACTIONS:")
        for r in report:
            if not r['passed'] or r['trades_day_est'] < 3:
                print(f"   • {r['display']}: {r['adjustment']}")
        result_code = 1
    else:
        print("⚠️ VALIDATION: NEEDS TUNING")
        print(f"   {failed_count} strategies need adjustment")
        print("   Can deploy with warnings, or fix first")
        print()
        print("SUGGESTED TUNING:")
        for r in report:
            if not r['passed']:
                print(f"   • {r['display']}: {r['adjustment']}")
        result_code = 1
    
    print("=" * 100)
    print()
    
    return result_code


if __name__ == "__main__":
    result_code = run_pre_deployment_validation()
    sys.exit(result_code)








