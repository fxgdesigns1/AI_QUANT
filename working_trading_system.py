#!/usr/bin/env python3
"""
WORKING TRADING SYSTEM - ACTUALLY EXECUTES TRADES
This system will generate signals and EXECUTE them immediately
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Set up environment
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import get_account_manager
from src.core.trading_scanner import TradingScanner
from src.core.order_manager import OrderManager
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkingTradingSystem:
    def __init__(self):
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.order_managers = {}
        
        # Initialize order managers for each account
        for account_id in self.active_accounts:
            self.order_managers[account_id] = OrderManager(account_id=account_id)
        
        logger.info(f"✅ Working Trading System initialized with {len(self.active_accounts)} accounts")
    
    def scan_and_execute(self):
        """Scan for opportunities and EXECUTE trades immediately"""
        logger.info("🔍 SCANNING FOR OPPORTUNITIES...")
        
        all_signals = []
        
        # Get market data for all accounts
        for account_id in self.active_accounts:
            try:
                client = self.account_manager.get_account_client(account_id)
                market_data = client.get_current_prices(['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD'])
                
                # Test each strategy
                for strategy_name, strategy in self.strategies.items():
                    try:
                        signals = strategy.analyze_market(market_data)
                        if signals:
                            logger.info(f"📊 {strategy_name} generated {len(signals)} signals for account {account_id[-3:]}")
                            for signal in signals:
                                signal.account_id = account_id
                                all_signals.append(signal)
                    except Exception as e:
                        logger.error(f"❌ {strategy_name} failed for account {account_id[-3:]}: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to get market data for account {account_id[-3:]}: {e}")
        
        logger.info(f"📊 Total signals generated: {len(all_signals)}")
        
        # EXECUTE TRADES
        executed_trades = 0
        for signal in all_signals:
            try:
                account_id = signal.account_id
                order_manager = self.order_managers[account_id]
                
                logger.info(f"🚀 EXECUTING TRADE: {signal.instrument} {signal.side.value} on account {account_id[-3:]}")
                
                # Calculate position size (1% risk)
                account_info = order_manager.oanda_client.get_account_info()
                risk_amount = account_info.balance * 0.01
                
                # Calculate stop distance
                if signal.side.value == 'BUY':
                    stop_distance = signal.entry_price - signal.stop_loss
                else:
                    stop_distance = signal.stop_loss - signal.entry_price
                
                position_size = risk_amount / stop_distance if stop_distance > 0 else 10000
                
                # Place the order
                result = order_manager.oanda_client.place_market_order(
                    instrument=signal.instrument,
                    side=signal.side.value,
                    units=int(position_size),
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit
                )
                
                if result:
                    executed_trades += 1
                    logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} - Units: {int(position_size)}")
                else:
                    logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value}")
                    
            except Exception as e:
                logger.error(f"❌ Trade execution failed: {e}")
        
        logger.info(f"🎯 EXECUTED {executed_trades} TRADES")
        return executed_trades

def main():
    """Main trading loop"""
    logger.info("🚀 STARTING WORKING TRADING SYSTEM")
    
    system = WorkingTradingSystem()
    
    # Run continuous scanning
    while True:
        try:
            executed = system.scan_and_execute()
            logger.info(f"⏰ Next scan in 30 seconds... (Executed {executed} trades)")
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("🛑 Trading system stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()


