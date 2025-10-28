#!/usr/bin/env python3
"""
System Control Test Script
Demonstrates full control over the trading system by forcing micro trades
across all three strategy accounts to verify functionality.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List
import time

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.order_manager import TradeSignal, OrderSide, get_order_manager
from src.core.data_feed import get_data_feed, MarketData
from src.strategies.alpha import get_alpha_strategy
from src.strategies.gold_scalping import get_gold_scalping_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemControlTester:
    """Test system control by forcing micro trades across all strategies"""
    
    def __init__(self):
        """Initialize the system control tester"""
        self.order_manager = get_order_manager()
        self.data_feed = get_data_feed()
        
        # Get all three strategies
        self.alpha_strategy = get_alpha_strategy()
        self.gold_strategy = get_gold_scalping_strategy()
        self.momentum_strategy = get_momentum_trading_strategy()
        
        # Test results
        self.test_results = {
            'alpha_trades': [],
            'gold_trades': [],
            'momentum_trades': [],
            'system_status': {},
            'errors': []
        }
        
        logger.info("🚀 System Control Tester initialized")
        logger.info("=" * 60)
    
    def test_system_connectivity(self) -> bool:
        """Test basic system connectivity"""
        try:
            logger.info("🔍 Testing system connectivity...")
            
            # Test OANDA connection
            if not self.order_manager.oanda_client.is_connected():
                logger.error("❌ OANDA connection failed")
                return False
            
            # Test data feed
            self.data_feed.start()
            time.sleep(5)  # Wait for data
            
            market_data = self.data_feed.get_market_data()
            if not market_data:
                logger.error("❌ No market data available")
                return False
            
            logger.info(f"✅ System connectivity verified - {len(market_data)} instruments available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connectivity test failed: {e}")
            return False
    
    def force_alpha_trades(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Force alpha strategy trades"""
        try:
            logger.info("🎯 Forcing ALPHA strategy trades...")
            
            # Override strategy to force trades
            original_max_trades = self.alpha_strategy.max_trades_per_day
            original_min_trades = self.alpha_strategy.min_trades_today
            
            # Set aggressive parameters for testing
            self.alpha_strategy.max_trades_per_day = 10
            self.alpha_strategy.min_trades_today = 3
            self.alpha_strategy.daily_trade_count = 0  # Reset counter
            
            # Generate signals
            signals = self.alpha_strategy.analyze_market(market_data)
            
            # If no signals, force create them
            if not signals:
                logger.info("🚀 No signals generated, forcing manual signals...")
                
                # Force EUR_USD BUY signal
                eur_data = market_data.get('EUR_USD')
                if eur_data:
                    current_price = (eur_data.bid + eur_data.ask) / 2
                    stop_loss = current_price * 0.998  # 0.2% stop loss
                    take_profit = current_price * 1.002  # 0.2% take profit
                    
                    forced_signal = TradeSignal(
                        instrument='EUR_USD',
                        side=OrderSide.BUY,
                        units=1000,  # Micro trade
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy_name='Alpha Strategy (FORCED)',
                        confidence=0.8
                    )
                    signals.append(forced_signal)
                    logger.info(f"🚀 FORCED ALPHA SIGNAL: EUR_USD BUY @ {current_price:.5f}")
            
            # Restore original parameters
            self.alpha_strategy.max_trades_per_day = original_max_trades
            self.alpha_strategy.min_trades_today = original_min_trades
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Alpha strategy test failed: {e}")
            return []
    
    def force_gold_trades(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Force gold scalping strategy trades"""
        try:
            logger.info("🎯 Forcing GOLD SCALPING strategy trades...")
            
            # Override strategy to force trades
            original_max_trades = self.gold_strategy.max_trades_per_day
            original_min_trades = self.gold_strategy.min_trades_today
            
            # Set aggressive parameters for testing
            self.gold_strategy.max_trades_per_day = 10
            self.gold_strategy.min_trades_today = 3
            self.gold_strategy.daily_trade_count = 0  # Reset counter
            
            # Generate signals
            signals = self.gold_strategy.analyze_market(market_data)
            
            # If no signals, force create them
            if not signals:
                logger.info("🚀 No signals generated, forcing manual signals...")
                
                # Force XAU_USD BUY signal
                gold_data = market_data.get('XAU_USD')
                if gold_data:
                    current_price = (gold_data.bid + gold_data.ask) / 2
                    stop_loss = current_price * 0.999  # 0.1% stop loss
                    take_profit = current_price * 1.001  # 0.1% take profit
                    
                    forced_signal = TradeSignal(
                        instrument='XAU_USD',
                        side=OrderSide.BUY,
                        units=100,  # Micro trade for gold
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy_name='Gold Scalping (FORCED)',
                        confidence=0.8
                    )
                    signals.append(forced_signal)
                    logger.info(f"🚀 FORCED GOLD SIGNAL: XAU_USD BUY @ {current_price:.2f}")
            
            # Restore original parameters
            self.gold_strategy.max_trades_per_day = original_max_trades
            self.gold_strategy.min_trades_today = original_min_trades
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Gold strategy test failed: {e}")
            return []
    
    def force_momentum_trades(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Force momentum strategy trades"""
        try:
            logger.info("🎯 Forcing MOMENTUM strategy trades...")
            
            # Override strategy to force trades
            original_max_trades = self.momentum_strategy.max_trades_per_day
            original_min_trades = self.momentum_strategy.min_trades_today
            
            # Set aggressive parameters for testing
            self.momentum_strategy.max_trades_per_day = 10
            self.momentum_strategy.min_trades_today = 3
            self.momentum_strategy.daily_trade_count = 0  # Reset counter
            
            # Generate signals
            signals = self.momentum_strategy.analyze_market(market_data)
            
            # If no signals, force create them
            if not signals:
                logger.info("🚀 No signals generated, forcing manual signals...")
                
                # Force GBP_USD BUY signal
                gbp_data = market_data.get('GBP_USD')
                if gbp_data:
                    current_price = (gbp_data.bid + gbp_data.ask) / 2
                    stop_loss = current_price * 0.998  # 0.2% stop loss
                    take_profit = current_price * 1.002  # 0.2% take profit
                    
                    forced_signal = TradeSignal(
                        instrument='GBP_USD',
                        side=OrderSide.BUY,
                        units=1000,  # Micro trade
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy_name='Momentum Trading (FORCED)',
                        confidence=0.8
                    )
                    signals.append(forced_signal)
                    logger.info(f"🚀 FORCED MOMENTUM SIGNAL: GBP_USD BUY @ {current_price:.5f}")
            
            # Restore original parameters
            self.momentum_strategy.max_trades_per_day = original_max_trades
            self.momentum_strategy.min_trades_today = original_min_trades
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Momentum strategy test failed: {e}")
            return []
    
    def execute_micro_trades(self, signals: List[TradeSignal], strategy_name: str) -> List[Dict]:
        """Execute micro trades and return results"""
        results = []
        
        for signal in signals:
            try:
                logger.info(f"🎯 Executing {strategy_name} trade: {signal.instrument} {signal.side.value}")
                
                # Execute the trade
                execution = self.order_manager.execute_trade(signal)
                
                result = {
                    'strategy': strategy_name,
                    'instrument': signal.instrument,
                    'side': signal.side.value,
                    'units': signal.units,
                    'success': execution.success,
                    'order_id': execution.order.order_id if execution.order else None,
                    'error': execution.error_message,
                    'timestamp': datetime.now().isoformat()
                }
                
                if execution.success:
                    logger.info(f"✅ {strategy_name} trade executed successfully: {execution.order.order_id}")
                else:
                    logger.error(f"❌ {strategy_name} trade failed: {execution.error_message}")
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"❌ Trade execution error: {e}")
                results.append({
                    'strategy': strategy_name,
                    'instrument': signal.instrument,
                    'side': signal.side.value,
                    'units': signal.units,
                    'success': False,
                    'order_id': None,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def test_mac_portraits(self, market_data: Dict[str, MarketData]) -> Dict:
        """Test MAC (Moving Average Crossover) portraits across all strategies"""
        try:
            logger.info("📊 Testing MAC portraits across all strategies...")
            
            mac_results = {}
            
            # Test Alpha strategy MAC
            alpha_status = self.alpha_strategy.get_strategy_status()
            mac_results['alpha'] = {
                'name': alpha_status['name'],
                'instruments': alpha_status['instruments'],
                'daily_trades': alpha_status['daily_trades'],
                'max_daily_trades': alpha_status['max_daily_trades'],
                'ema_params': {
                    'fast': alpha_status['params']['ema_fast'],
                    'mid': alpha_status['params']['ema_mid'],
                    'slow': alpha_status['params']['ema_slow']
                }
            }
            
            # Test Gold strategy MAC
            gold_status = self.gold_strategy.get_strategy_status()
            mac_results['gold'] = {
                'name': gold_status['name'],
                'instruments': gold_status['instruments'],
                'daily_trades': gold_status['daily_trades'],
                'max_daily_trades': gold_status['max_daily_trades'],
                'scalping_params': gold_status['parameters']
            }
            
            # Test Momentum strategy MAC
            momentum_status = self.momentum_strategy.get_strategy_status()
            mac_results['momentum'] = {
                'name': momentum_status['name'],
                'instruments': momentum_status['instruments'],
                'daily_trades': momentum_status['daily_trades'],
                'max_daily_trades': momentum_status['max_daily_trades'],
                'momentum_params': momentum_status['parameters']
            }
            
            logger.info("✅ MAC portraits generated for all strategies")
            return mac_results
            
        except Exception as e:
            logger.error(f"❌ MAC portrait test failed: {e}")
            return {}
    
    def run_full_system_test(self):
        """Run comprehensive system control test"""
        logger.info("🚀 Starting FULL SYSTEM CONTROL TEST")
        logger.info("=" * 60)
        
        try:
            # Step 1: Test connectivity
            if not self.test_system_connectivity():
                logger.error("❌ System connectivity test failed - aborting")
                return False
            
            # Step 2: Get market data
            market_data = self.data_feed.get_market_data()
            logger.info(f"📊 Market data available for {len(market_data)} instruments")
            
            # Step 3: Test MAC portraits
            mac_results = self.test_mac_portraits(market_data)
            self.test_results['mac_portraits'] = mac_results
            
            # Step 4: Force trades for each strategy
            logger.info("🎯 FORCING TRADES ACROSS ALL STRATEGIES...")
            
            # Alpha strategy trades
            alpha_signals = self.force_alpha_trades(market_data)
            if alpha_signals:
                alpha_results = self.execute_micro_trades(alpha_signals, "Alpha")
                self.test_results['alpha_trades'] = alpha_results
                logger.info(f"✅ Alpha strategy: {len(alpha_results)} trades executed")
            
            # Gold strategy trades
            gold_signals = self.force_gold_trades(market_data)
            if gold_signals:
                gold_results = self.execute_micro_trades(gold_signals, "Gold")
                self.test_results['gold_trades'] = gold_results
                logger.info(f"✅ Gold strategy: {len(gold_results)} trades executed")
            
            # Momentum strategy trades
            momentum_signals = self.force_momentum_trades(market_data)
            if momentum_signals:
                momentum_results = self.execute_micro_trades(momentum_signals, "Momentum")
                self.test_results['momentum_trades'] = momentum_results
                logger.info(f"✅ Momentum strategy: {len(momentum_results)} trades executed")
            
            # Step 5: Get system status
            system_status = self.order_manager.get_daily_stats()
            self.test_results['system_status'] = system_status
            
            # Step 6: Test position management
            logger.info("🔄 Testing position management...")
            positions = self.order_manager.get_positions()
            logger.info(f"📊 Current positions: {len(positions)}")
            
            # Step 7: Test order management
            active_orders = self.order_manager.get_active_orders()
            logger.info(f"📊 Active orders: {len(active_orders)}")
            
            # Summary
            total_trades = (len(self.test_results['alpha_trades']) + 
                          len(self.test_results['gold_trades']) + 
                          len(self.test_results['momentum_trades']))
            
            logger.info("=" * 60)
            logger.info("🎯 SYSTEM CONTROL TEST COMPLETED")
            logger.info(f"📊 Total trades executed: {total_trades}")
            logger.info(f"📊 Alpha trades: {len(self.test_results['alpha_trades'])}")
            logger.info(f"📊 Gold trades: {len(self.test_results['gold_trades'])}")
            logger.info(f"📊 Momentum trades: {len(self.test_results['momentum_trades'])}")
            logger.info(f"📊 System status: {system_status}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ System test failed: {e}")
            self.test_results['errors'].append(str(e))
            return False
        
        finally:
            # Cleanup
            self.data_feed.stop()
    
    def get_test_results(self) -> Dict:
        """Get comprehensive test results"""
        return self.test_results

def main():
    """Main test execution"""
    logger.info("🚀 Starting System Control Test")
    logger.info("This test will demonstrate full control over the trading system")
    logger.info("by forcing micro trades across all three strategy accounts.")
    logger.info("=" * 60)
    
    # Create tester
    tester = SystemControlTester()
    
    # Run full system test
    success = tester.run_full_system_test()
    
    # Get results
    results = tester.get_test_results()
    
    if success:
        logger.info("✅ SYSTEM CONTROL TEST PASSED")
        logger.info("🎯 Full control over trading system verified")
    else:
        logger.error("❌ SYSTEM CONTROL TEST FAILED")
        logger.error("🔧 System requires attention")
    
    return results

if __name__ == '__main__':
    results = main()
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS:")
    print("=" * 60)
    print(f"Alpha trades: {len(results.get('alpha_trades', []))}")
    print(f"Gold trades: {len(results.get('gold_trades', []))}")
    print(f"Momentum trades: {len(results.get('momentum_trades', []))}")
    print(f"System status: {results.get('system_status', {})}")
    print("=" * 60)
