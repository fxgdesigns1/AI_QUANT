#!/usr/bin/env python3
"""
WORKING AUTO SCANNER - RUNS CONTINUOUSLY AND EXECUTES TRADES
This will run the scanner automatically every 5 minutes
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime

# Set up environment
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import get_account_manager
from src.core.oanda_client import OandaClient
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkingAutoScanner:
    def __init__(self):
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.is_running = False
        self.scan_count = 0
        
        logger.info(f"✅ Working Auto Scanner initialized with {len(self.active_accounts)} accounts")
    
    def scan_and_execute(self):
        """Scan for opportunities and EXECUTE trades immediately"""
        self.scan_count += 1
        logger.info(f"🔍 SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        total_signals = 0
        total_executed = 0
        
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
                            total_signals += len(signals)
                            
                            # EXECUTE TRADES
                            for signal in signals:
                                try:
                                    # Calculate position size (1% risk)
                                    account_info = client.get_account_info()
                                    risk_amount = account_info.balance * 0.01
                                    
                                    # Get entry price from market data
                                    current_price = market_data.get(signal.instrument)
                                    if current_price:
                                        entry_price = current_price.ask if signal.side.value == 'BUY' else current_price.bid
                                    else:
                                        entry_price = 0.0  # Fallback
                                    
                                    # Calculate stop distance
                                    if signal.side.value == 'BUY':
                                        stop_distance = entry_price - signal.stop_loss
                                    else:
                                        stop_distance = signal.stop_loss - entry_price
                                    
                                    position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 10000
                                    
                                    # Place the order
                                    result = client.place_market_order(
                                        instrument=signal.instrument,
                                        units=position_size,
                                        stop_loss=signal.stop_loss,
                                        take_profit=signal.take_profit
                                    )
                                    
                                    if result:
                                        total_executed += 1
                                        logger.info(f"✅ TRADE EXECUTED: {signal.instrument} {signal.side.value} - Units: {position_size}")
                                    else:
                                        logger.error(f"❌ TRADE FAILED: {signal.instrument} {signal.side.value}")
                                        
                                except Exception as e:
                                    logger.error(f"❌ Trade execution failed: {e}")
                                    
                    except Exception as e:
                        logger.error(f"❌ {strategy_name} failed for account {account_id[-3:]}: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to get market data for account {account_id[-3:]}: {e}")
        
        logger.info(f"📊 SCAN #{self.scan_count} COMPLETE: {total_signals} signals, {total_executed} executed")
        return total_executed
    
    def start_scanning(self):
        """Start continuous scanning"""
        self.is_running = True
        logger.info("🚀 STARTING CONTINUOUS SCANNING...")
        
        while self.is_running:
            try:
                executed = self.scan_and_execute()
                logger.info(f"⏰ Next scan in 5 minutes... (Executed {executed} trades)")
                time.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                logger.info("🛑 Scanner stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Scanner error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop scanning"""
        self.is_running = False
        logger.info("🛑 Scanner stopped")

def main():
    """Main scanner loop"""
    logger.info("🚀 STARTING WORKING AUTO SCANNER")
    
    scanner = WorkingAutoScanner()
    
    try:
        scanner.start_scanning()
    except KeyboardInterrupt:
        logger.info("🛑 Scanner stopped by user")
        scanner.stop()

if __name__ == "__main__":
    main()
