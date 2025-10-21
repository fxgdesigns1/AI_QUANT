#!/usr/bin/env python3
"""
Progressive Trading Scanner
Continuously relaxes trading criteria until trades are found, then reports via Telegram
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressiveTradingScanner:
    """Progressive relaxation scanner that keeps loosening criteria until trades are found"""
    
    def __init__(self):
        """Initialize the progressive scanner"""
        self.relaxation_levels = [
            # Level 0: Relaxed but still quality (50% - better than random)
            {
                'min_signal_strength': 0.50,
                'stop_loss_pct': 0.006,
                'take_profit_pct': 0.010,
                'min_data_points': 15,
                'min_momentum_data': 15,
                'force_trade_threshold': 0  # NO forced trades
            },
            # Level 1: More relaxed (40% - minimum acceptable)
            {
                'min_signal_strength': 0.40,
                'stop_loss_pct': 0.008,
                'take_profit_pct': 0.012,
                'min_data_points': 10,
                'min_momentum_data': 10,
                'force_trade_threshold': 0  # NO forced trades
            },
            # REMOVED Level 3 and 4 - TOO DANGEROUS (5% and 1% thresholds)
            # Minimum acceptable threshold is 20% (Level 1)
            # Going lower than 20% = random gambling
        ]
        
        self.current_level = 0
        self.max_levels = len(self.relaxation_levels)
        
        # Initialize components
        self._init_components()
        
        logger.info(f"🔄 Progressive Trading Scanner initialized with {self.max_levels} relaxation levels")
    
    def _init_components(self):
        """Initialize trading system components"""
        try:
            from src.dashboard.advanced_dashboard import AdvancedDashboardManager
            from src.core.telegram_notifier import get_telegram_notifier
            
            self.dashboard_manager = AdvancedDashboardManager()
            self.telegram_notifier = get_telegram_notifier()
            
            logger.info("✅ Components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            self.dashboard_manager = None
            self.telegram_notifier = None
    
    def _apply_relaxation_level(self, level: int) -> Dict[str, Any]:
        """Apply relaxation level to trading strategies"""
        if level >= self.max_levels:
            level = self.max_levels - 1
        
        params = self.relaxation_levels[level]
        
        try:
            # Get the Ultra Strict Forex strategy and apply relaxed parameters
            from src.strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
            
            strategy = get_ultra_strict_forex_strategy()
            
            # Apply relaxed parameters
            strategy.min_signal_strength = params['min_signal_strength']
            strategy.stop_loss_pct = params['stop_loss_pct']
            strategy.take_profit_pct = params['take_profit_pct']
            strategy.min_trades_today = params['force_trade_threshold']
            
            logger.info(f"📊 Applied relaxation level {level}:")
            logger.info(f"   • Confidence threshold: {params['min_signal_strength']}")
            logger.info(f"   • Stop loss: {params['stop_loss_pct']*100:.1f}%")
            logger.info(f"   • Take profit: {params['take_profit_pct']*100:.1f}%")
            logger.info(f"   • Force trades: {params['force_trade_threshold']}")
            
            return params
            
        except Exception as e:
            logger.error(f"❌ Failed to apply relaxation level {level}: {e}")
            return {}
    
    def _execute_trading_scan(self) -> Dict[str, Any]:
        """Execute trading scan with current parameters"""
        try:
            if not self.dashboard_manager:
                return {'error': 'Dashboard manager not available'}
            
            # Execute trading signals
            results = self.dashboard_manager.execute_trading_signals()
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Trading scan failed: {e}")
            return {'error': str(e)}
    
    def _force_execute_trades(self, min_trades_per_account: Dict[str, int]) -> Dict[str, Any]:
        """FORCE trade execution when progressive scan finds nothing"""
        
        # CHECK FOR TRADING DISABLED - CRITICAL SAFETY CHECK
        import os
        weekend_mode = os.getenv('WEEKEND_MODE', 'false').lower() == 'true'
        trading_disabled = os.getenv('TRADING_DISABLED', 'false').lower() == 'true'
        
        if weekend_mode or trading_disabled:
            logger.info("🛑 TRADING DISABLED - Skipping ALL forced trades")
            return {'success': True, 'total_trades': 0, 'message': 'Trading disabled', 'results': {}}
        
        logger.warning("🔥 FORCING trade execution - no opportunities found with relaxed criteria")
        logger.info(f"📊 Min trades per account: {min_trades_per_account}")
        
        try:
            from src.core.account_manager import get_account_manager
            from src.core.order_manager import get_order_manager
            
            logger.info("📊 Importing account manager...")
            account_manager = get_account_manager()
            logger.info(f"📊 Account manager loaded, active accounts: {len(account_manager.get_active_accounts())}")
            
            results = {}
            total_forced = 0
            
            active_accts = account_manager.get_active_accounts()
            logger.info(f"📊 Active accounts list: {active_accts}")
            
            for account_id in active_accts:
                logger.info(f"📊 Processing account: {account_id}")
                config = account_manager.get_account_config(account_id)
                logger.info(f"📊 Config loaded: {config is not None}")
                
                if not config:
                    logger.warning(f"⚠️ No config for {account_id}, skipping")
                    continue
                
                min_trades = min_trades_per_account.get(account_id, 3)
                instruments = config.instruments
                logger.info(f"📊 Instruments for {account_id}: {instruments}")
                
                logger.info(f"🎯 Forcing {min_trades} trades for account {account_id}")
                
                account_trades = []
                for i, instrument in enumerate(instruments[:min_trades]):
                    try:
                        order_mgr = get_order_manager(account_id)
                        
                        # Simple logic: alternate BUY/SELL
                        side = "BUY" if i % 2 == 0 else "SELL"
                        
                        # Get current price for SL/TP calculation
                        client = account_manager.get_account_client(account_id)
                        
                        # Get pricing using proper OANDA API method
                        prices = client.get_current_prices([instrument])
                        
                        if not prices or instrument not in prices:
                            logger.warning(f"⚠️ No price data for {instrument}")
                            continue
                        
                        price_obj = prices[instrument]
                        entry_price = price_obj.ask if side == "BUY" else price_obj.bid
                        logger.info(f"📊 Current price for {instrument}: bid={price_obj.bid}, ask={price_obj.ask}")
                        
                        # Calculate position size (conservative)
                        units = 100000  # 1 lot for forex
                        is_gold = 'XAU' in instrument
                        
                        if is_gold:
                            units = 500  # Very small gold size (0.005 lots)
                        
                        # Calculate SL/TP - different for gold vs forex
                        if is_gold:
                            # Gold: use $ amounts not percentages
                            sl_amount = 10.0  # $10 stop loss
                            tp_amount = 15.0  # $15 take profit
                            if side == "BUY":
                                stop_loss = entry_price - sl_amount
                                take_profit = entry_price + tp_amount
                            else:
                                stop_loss = entry_price + sl_amount
                                take_profit = entry_price - tp_amount
                                units = -units
                        else:
                            # Forex: use percentages
                            sl_pct = 0.005  # 0.5%
                            tp_pct = 0.008  # 0.8%
                            if side == "BUY":
                                stop_loss = entry_price * (1 - sl_pct)
                                take_profit = entry_price * (1 + tp_pct)
                            else:
                                stop_loss = entry_price * (1 + sl_pct)
                                take_profit = entry_price * (1 - tp_pct)
                                units = -units
                        
                        # Place MARKET order for INSTANT execution at real price
                        try:
                            logger.info(f"🎯 Placing MARKET order: {instrument} {side} {abs(units)} units with SL={stop_loss:.5f}, TP={take_profit:.5f}")
                            
                            order_result = order_mgr.oanda_client.place_market_order(
                                instrument=instrument,
                                units=units,
                                stop_loss=stop_loss,
                                take_profit=take_profit
                            )
                            
                            if order_result:
                                account_trades.append({'success': True, 'order': order_result})
                                total_forced += 1
                                logger.info(f"✅ MARKET order FILLED: {instrument} {side} {abs(units)} units at market price")
                            
                        except Exception as order_err:
                            logger.error(f"❌ Order placement failed for {instrument}: {order_err}")
                            continue
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to force trade for {instrument}: {e}")
                        continue
                
                results[account_id] = {
                    'forced_trades': len(account_trades),
                    'executed_trades': account_trades
                }
            
            logger.info(f"✅ Forced {total_forced} total trades across all accounts")
            return {
                'success': True,
                'total_trades': total_forced,
                'results': results,
                'forced': True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to force execute trades: {e}")
            return {'error': str(e), 'success': False}
    
    def _count_total_trades(self, results: Dict[str, Any]) -> int:
        """Count total trades across all accounts"""
        total_trades = 0
        
        if isinstance(results, dict):
            for account_id, account_results in results.items():
                if isinstance(account_results, dict):
                    executed_trades = account_results.get('executed_trades', [])
                    if isinstance(executed_trades, list):
                        total_trades += len(executed_trades)
        
        return total_trades
    
    def _send_telegram_report(self, level: int, trades_found: int, results: Dict[str, Any]):
        """Send results report via Telegram"""
        try:
            if not self.telegram_notifier or not getattr(self.telegram_notifier, 'enabled', False):
                logger.warning("⚠️ Telegram notifier not available")
                return
            
            # Build report message
            message_lines = [
                f"🔄 PROGRESSIVE TRADING SCAN COMPLETE",
                f"📊 Relaxation Level: {level}/{self.max_levels-1}",
                f"🎯 Total Trades Found: {trades_found}",
                f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            
            # Add account-specific results
            if isinstance(results, dict):
                for account_id, account_results in results.items():
                    if isinstance(account_results, dict):
                        executed_trades = account_results.get('executed_trades', [])
                        if isinstance(executed_trades, list) and executed_trades:
                            message_lines.append(f"• {account_id}: {len(executed_trades)} trades")
            
            # Add parameters used
            if level < self.max_levels:
                params = self.relaxation_levels[level]
                message_lines.extend([
                    "",
                    "📋 Parameters Used:",
                    f"• Confidence: {params['min_signal_strength']*100:.1f}%",
                    f"• Stop Loss: {params['stop_loss_pct']*100:.1f}%",
                    f"• Take Profit: {params['take_profit_pct']*100:.1f}%"
                ])
            
            message = "\n".join(message_lines)
            
            # Send via Telegram
            self.telegram_notifier.send_message(message)
            logger.info("📱 Telegram report sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram report: {e}")
    
    def run_progressive_scan(self, max_attempts: int = None):
        """Run progressive scan with increasing relaxation"""
        if max_attempts is None:
            max_attempts = self.max_levels
        
        logger.info(f"🚀 Starting progressive trading scan (max {max_attempts} attempts)")
        
        for attempt in range(max_attempts):
            current_level = attempt
            logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts} - Relaxation Level {current_level}")
            
            # Apply relaxation level
            params = self._apply_relaxation_level(current_level)
            if not params:
                logger.error(f"❌ Failed to apply relaxation level {current_level}")
                continue
            
            # Execute trading scan
            results = self._execute_trading_scan()
            
            # Count trades found
            trades_found = self._count_total_trades(results)
            
            logger.info(f"📊 Level {current_level}: Found {trades_found} trades")
            
            # If trades found, report and exit
            if trades_found > 0:
                logger.info(f"✅ SUCCESS! Found {trades_found} trades at level {current_level}")
                self._send_telegram_report(current_level, trades_found, results)
                return {
                    'success': True,
                    'level': current_level,
                    'trades_found': trades_found,
                    'results': results
                }
            
            # If no trades found and not at max level, continue
            if attempt < max_attempts - 1:
                logger.info(f"⚠️ No trades found at level {current_level}, relaxing further...")
                time.sleep(2)  # Brief pause between attempts
            else:
                logger.warning(f"⚠️ No trades found even at maximum relaxation level {current_level}")
                logger.warning("🔥 FORCING TRADES - will place orders on all accounts")
                
                # Force minimum trades per account - OPTIMIZED
                # DISABLED: Never force trades - only trade on genuine signals  
                logger.info("❌ Maximum relaxation reached - NO forced trades (disabled for safety)")
                forced_results = {'success': True, 'total_trades': 0, 'message': 'Force trading disabled'}
                
                if forced_results.get('success'):
                    total_forced = forced_results.get('total_trades', 0)
                    logger.info(f"✅ FORCED {total_forced} trades across all accounts")
                    self._send_telegram_report(current_level, total_forced, forced_results.get('results', {}))
                    return {
                        'success': True,
                        'total_trades': total_forced,
                        'forced': True,
                        'results': forced_results.get('results', {}),
                        'level': current_level,
                        'trades_found': total_forced
                    }
                else:
                    logger.error("❌ Failed to force execute trades")
                    self._send_telegram_report(current_level, 0, results)
                    return {
                        'success': False,
                        'level': current_level,
                        'trades_found': 0,
                        'results': results
                    }
        
        return {'success': False, 'error': 'Max attempts reached'}

def main():
    """Main function to run progressive scan"""
    scanner = ProgressiveTradingScanner()
    results = scanner.run_progressive_scan()
    
    if results['success']:
        print(f"✅ Progressive scan completed successfully!")
        print(f"   Level: {results['level']}")
        print(f"   Trades found: {results['trades_found']}")
    else:
        print(f"⚠️ Progressive scan completed with no trades found")
        print(f"   Final level: {results.get('level', 'unknown')}")

if __name__ == "__main__":
    main()


