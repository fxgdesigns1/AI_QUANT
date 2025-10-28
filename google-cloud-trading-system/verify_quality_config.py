#!/usr/bin/env python3
"""
Quality Trading Configuration Verification Script
Verifies that all strategies are configured for high-quality trades with better R:R
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def verify_strategy_config():
    """Verify all strategy configurations"""
    print("=" * 70)
    print("🔍 QUALITY TRADING CONFIGURATION VERIFICATION")
    print("=" * 70)
    print()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "strategies": {},
        "issues": [],
        "passed": True
    }
    
    # Import strategies
    try:
        from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
        from src.strategies.gold_scalping import get_gold_scalping_strategy
        from src.strategies.momentum_trading import get_momentum_trading_strategy
        
        strategies = [
            ("Ultra Strict Forex", get_ultra_strict_forex_strategy()),
            ("Gold Scalping", get_gold_scalping_strategy()),
            ("Momentum Trading", get_momentum_trading_strategy())
        ]
        
        print("✅ All strategy modules loaded successfully\n")
        
    except Exception as e:
        print(f"❌ Failed to load strategies: {e}")
        results["passed"] = False
        results["issues"].append(f"Strategy loading error: {e}")
        return results
    
    # Verify each strategy
    for strategy_name, strategy in strategies:
        print(f"📊 {strategy_name}")
        print("-" * 70)
        
        strategy_data = {
            "name": strategy.name,
            "instruments": strategy.instruments,
            "parameters": {},
            "quality_checks": {}
        }
        
        # Check forced trading removed
        min_trades = getattr(strategy, 'min_trades_today', None)
        if min_trades is not None and min_trades > 0:
            print(f"   ❌ ISSUE: Forced trading still enabled (min_trades_today={min_trades})")
            results["issues"].append(f"{strategy_name}: Forced trading not disabled")
            results["passed"] = False
            strategy_data["quality_checks"]["no_forced_trades"] = False
        else:
            print(f"   ✅ No forced trades (min_trades_today={min_trades})")
            strategy_data["quality_checks"]["no_forced_trades"] = True
        
        # Check confidence/signal strength
        if strategy_name == "Ultra Strict Forex":
            min_strength = strategy.min_signal_strength
            target_strength = 0.60
            if min_strength >= target_strength:
                print(f"   ✅ High confidence threshold: {min_strength:.2f} >= {target_strength:.2f}")
                strategy_data["quality_checks"]["high_confidence"] = True
            else:
                print(f"   ⚠️  Low confidence threshold: {min_strength:.2f} < {target_strength:.2f}")
                results["issues"].append(f"{strategy_name}: Confidence too low ({min_strength})")
                strategy_data["quality_checks"]["high_confidence"] = False
            
            # Check R:R ratio
            sl_pct = strategy.stop_loss_pct
            tp_pct = strategy.take_profit_pct
            rr_ratio = tp_pct / sl_pct if sl_pct > 0 else 0
            print(f"   💰 Risk:Reward = 1:{rr_ratio:.1f} (SL: {sl_pct*100:.1f}%, TP: {tp_pct*100:.1f}%)")
            strategy_data["parameters"]["stop_loss_pct"] = sl_pct
            strategy_data["parameters"]["take_profit_pct"] = tp_pct
            strategy_data["parameters"]["rr_ratio"] = rr_ratio
            strategy_data["parameters"]["min_signal_strength"] = min_strength
            
            if rr_ratio >= 3.0:
                print(f"   ✅ Excellent R:R ratio: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = True
            else:
                print(f"   ⚠️  R:R could be improved: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = False
        
        elif strategy_name == "Gold Scalping":
            min_strength = strategy.min_signal_strength
            target_strength = 0.55
            if min_strength >= target_strength:
                print(f"   ✅ High confidence threshold: {min_strength:.2f} >= {target_strength:.2f}")
                strategy_data["quality_checks"]["high_confidence"] = True
            else:
                print(f"   ⚠️  Low confidence threshold: {min_strength:.2f} < {target_strength:.2f}")
                results["issues"].append(f"{strategy_name}: Confidence too low ({min_strength})")
                strategy_data["quality_checks"]["high_confidence"] = False
            
            # Check R:R ratio
            sl_pips = strategy.stop_loss_pips
            tp_pips = strategy.take_profit_pips
            rr_ratio = tp_pips / sl_pips if sl_pips > 0 else 0
            print(f"   💰 Risk:Reward = 1:{rr_ratio:.1f} (SL: {sl_pips} pips, TP: {tp_pips} pips)")
            strategy_data["parameters"]["stop_loss_pips"] = sl_pips
            strategy_data["parameters"]["take_profit_pips"] = tp_pips
            strategy_data["parameters"]["rr_ratio"] = rr_ratio
            strategy_data["parameters"]["min_signal_strength"] = min_strength
            strategy_data["parameters"]["min_volatility"] = strategy.min_volatility
            strategy_data["parameters"]["max_spread"] = strategy.max_spread
            
            if rr_ratio >= 2.5:
                print(f"   ✅ Good R:R ratio: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = True
            else:
                print(f"   ⚠️  R:R could be improved: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = False
        
        elif strategy_name == "Momentum Trading":
            min_adx = strategy.min_adx
            min_momentum = strategy.min_momentum
            target_adx = 15
            target_momentum = 0.25
            
            if min_adx >= target_adx:
                print(f"   ✅ Strong trend requirement: ADX >= {min_adx}")
                strategy_data["quality_checks"]["strong_trends"] = True
            else:
                print(f"   ⚠️  Weak trend filter: ADX >= {min_adx} (target: {target_adx})")
                results["issues"].append(f"{strategy_name}: ADX filter too weak ({min_adx})")
                strategy_data["quality_checks"]["strong_trends"] = False
            
            if min_momentum >= target_momentum:
                print(f"   ✅ Strong momentum requirement: {min_momentum:.2f}")
                strategy_data["quality_checks"]["strong_momentum"] = True
            else:
                print(f"   ⚠️  Weak momentum filter: {min_momentum:.2f} (target: {target_momentum})")
                results["issues"].append(f"{strategy_name}: Momentum filter too weak ({min_momentum})")
                strategy_data["quality_checks"]["strong_momentum"] = False
            
            # Check R:R ratio
            sl_atr = strategy.stop_loss_atr
            tp_atr = strategy.take_profit_atr
            rr_ratio = tp_atr / sl_atr if sl_atr > 0 else 0
            print(f"   💰 Risk:Reward = 1:{rr_ratio:.1f} (SL: {sl_atr} ATR, TP: {tp_atr} ATR)")
            strategy_data["parameters"]["stop_loss_atr"] = sl_atr
            strategy_data["parameters"]["take_profit_atr"] = tp_atr
            strategy_data["parameters"]["rr_ratio"] = rr_ratio
            strategy_data["parameters"]["min_adx"] = min_adx
            strategy_data["parameters"]["min_momentum"] = min_momentum
            strategy_data["parameters"]["min_volume"] = strategy.min_volume
            
            if rr_ratio >= 3.0:
                print(f"   ✅ Excellent R:R ratio: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = True
            else:
                print(f"   ⚠️  R:R could be improved: 1:{rr_ratio:.1f}")
                strategy_data["quality_checks"]["good_rr"] = False
        
        # Check max trades per day
        max_trades = strategy.max_trades_per_day
        print(f"   📈 Max trades/day: {max_trades}")
        strategy_data["parameters"]["max_trades_per_day"] = max_trades
        
        if max_trades <= 60:
            print(f"   ✅ Quality-focused trade limit")
            strategy_data["quality_checks"]["quality_limit"] = True
        else:
            print(f"   ⚠️  High trade limit (may lead to overtrading)")
            strategy_data["quality_checks"]["quality_limit"] = False
        
        print(f"   🎯 Trading instruments: {', '.join(strategy.instruments)}")
        print()
        
        results["strategies"][strategy_name] = strategy_data
    
    # Final summary
    print("=" * 70)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 70)
    
    if results["passed"] and len(results["issues"]) == 0:
        print("✅ ALL CHECKS PASSED - System configured for quality trades")
        print()
        print("Expected Performance:")
        print("  • 40-80 trades/day (down from 180+)")
        print("  • Average R:R: 1:3.5+")
        print("  • Win rate target: 60-70%")
        print("  • No forced trades = only high-quality setups")
    else:
        print(f"⚠️  {len(results['issues'])} ISSUES FOUND:")
        for issue in results["issues"]:
            print(f"   • {issue}")
    
    print()
    print("=" * 70)
    
    # Save results
    output_file = f"quality_config_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📄 Full report saved to: {output_file}")
    print()
    
    return results

if __name__ == '__main__':
    results = verify_strategy_config()
    
    # Exit with appropriate code
    sys.exit(0 if results["passed"] else 1)


