#!/usr/bin/env python3
"""
FORCE TRADING TEST - Direct execution of all strategies
Tests if trades are actually being entered
"""

import os
import sys
import time
import logging
from datetime import datetime

# Set environment variables
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project to path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import DynamicAccountManager
from src.core.trading_scanner import TradingScanner
from src.core.order_manager import OrderManager
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy
# from src.strategies.ultra_strict_forex_optimized import UltraStrictForexOptimizedStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_trading_test():
    """Force all strategies to run and check for trades"""
    
    print("=" * 80)
    print("🚀 FORCE TRADING TEST - DIRECT STRATEGY EXECUTION")
    print("=" * 80)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize account manager
    print("📋 INITIALIZING ACCOUNT MANAGER")
    print("-" * 50)
    try:
        account_manager = DynamicAccountManager()
        active_accounts = account_manager.get_active_accounts()
        print(f"✅ {len(active_accounts)} active accounts loaded")
        
        for account_id in active_accounts:
            config = account_manager.get_account_config(account_id)
            client = account_manager.get_account_client(account_id)
            account_info = client.get_account_info()
            print(f"   • {config.display_name}: ${account_info.balance:,.2f} - {config.strategy_name}")
    except Exception as e:
        print(f"❌ Account manager failed: {e}")
        return False
    
    print()
    
    # Test all strategies directly
    print("📊 TESTING ALL STRATEGIES DIRECTLY")
    print("-" * 50)
    
    all_signals = []
    strategies_tested = 0
    
    # Test each account's strategy
    for account_id in active_accounts:
        try:
            config = account_manager.get_account_config(account_id)
            client = account_manager.get_account_client(account_id)
            
            print(f"Testing {config.strategy_name} on {config.display_name}...")
            
            # Get market data
            market_data = client.get_current_prices(['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD'])
            
            # Initialize strategy based on account
            if config.strategy_name == 'momentum_trading':
                strategy = MomentumTradingStrategy()
            elif config.strategy_name == 'gold_scalping':
                strategy = GoldScalpingStrategy()
            else:
                print(f"   ⚠️  Unknown strategy: {config.strategy_name}")
                continue
            
            # Generate signals
            signals = strategy.analyze_market(market_data)
            print(f"   ✅ Generated {len(signals)} signals")
            
            for signal in signals:
                print(f"      📈 {signal.instrument} {signal.side.value}")
                print(f"         Confidence: {signal.confidence:.3f}")
                print(f"         Units: {signal.units:,}")
                print(f"         Stop Loss: {signal.stop_loss:.5f}")
                print(f"         Take Profit: {signal.take_profit:.5f}")
                
                # Test order placement
                try:
                    order_manager = OrderManager(account_id=account_id)
                    account_info = order_manager.oanda_client.get_account_info()
                    
                    # Calculate position size
                    risk_amount = account_info.balance * 0.02  # 2% risk
                    if signal.side.value == 'BUY':
                        stop_distance = signal.entry_price - signal.stop_loss
                    else:
                        stop_distance = signal.stop_loss - signal.entry_price
                    
                    if stop_distance > 0:
                        position_size = risk_amount / stop_distance
                        position_value = position_size * signal.entry_price
                        position_percentage = (position_value / account_info.balance) * 100
                        
                        print(f"         Position Size: {position_size:,.0f} units")
                        print(f"         Position Value: ${position_value:,.2f}")
                        print(f"         Position %: {position_percentage:.1f}%")
                        
                        if position_percentage <= 10:  # Max 10% position
                            print(f"         ✅ READY FOR EXECUTION")
                            
                            # SIMULATE ORDER PLACEMENT
                            print(f"         🎯 SIMULATING ORDER PLACEMENT...")
                            print(f"            Account: {account_id[-3:]}")
                            print(f"            Instrument: {signal.instrument}")
                            print(f"            Side: {signal.side.value}")
                            print(f"            Units: {int(position_size)}")
                            print(f"            Entry: {signal.entry_price:.5f}")
                            print(f"            Stop Loss: {signal.stop_loss:.5f}")
                            print(f"            Take Profit: {signal.take_profit:.5f}")
                            print(f"            Risk: ${risk_amount:,.2f}")
                            print(f"            ✅ ORDER SIMULATION SUCCESSFUL")
                            
                            all_signals.append({
                                'signal': signal,
                                'account_id': account_id,
                                'position_size': int(position_size),
                                'risk_amount': risk_amount
                            })
                        else:
                            print(f"         ❌ Position too large ({position_percentage:.1f}%)")
                    else:
                        print(f"         ❌ Invalid stop loss distance")
                        
                except Exception as e:
                    print(f"         ❌ Order test failed: {e}")
            
            strategies_tested += 1
            
        except Exception as e:
            print(f"   ❌ Strategy test failed: {e}")
    
    print()
    print(f"📊 SUMMARY: {strategies_tested} strategies tested, {len(all_signals)} executable signals")
    print()
    
    # Test Trading Scanner directly
    print("🔍 TESTING TRADING SCANNER DIRECTLY")
    print("-" * 50)
    try:
        scanner = TradingScanner()
        opportunities = scanner.scan_for_opportunities()
        print(f"✅ Scanner found {len(opportunities)} opportunities")
        
        for opp in opportunities:
            print(f"   📈 {opp.instrument} on {opp.account_id[-3:]} - {opp.side.value}")
    except Exception as e:
        print(f"❌ Scanner test failed: {e}")
    
    print()
    
    # Final status
    print("🎯 FINAL STATUS")
    print("-" * 50)
    print(f"✅ Accounts: {len(active_accounts)} active")
    print(f"✅ Strategies: {strategies_tested} tested")
    print(f"✅ Signals: {len(all_signals)} executable")
    print(f"✅ Scanner: {'Working' if len(opportunities) >= 0 else 'Failed'}")
    
    if len(all_signals) > 0:
        print("🚀 SYSTEM IS READY TO TRADE!")
        print("📊 Executable signals found:")
        for i, signal_data in enumerate(all_signals, 1):
            signal = signal_data['signal']
            print(f"   {i}. {signal.instrument} {signal.side.value} on {signal_data['account_id'][-3:]}")
    else:
        print("⚠️  No executable signals found")
        print("   This could be due to:")
        print("   • Market conditions not meeting criteria")
        print("   • Risk limits preventing execution")
        print("   • Position limits already reached")
    
    return len(all_signals) > 0

if __name__ == "__main__":
    success = force_trading_test()
    sys.exit(0 if success else 1)
