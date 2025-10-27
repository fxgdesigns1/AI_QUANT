#!/usr/bin/env python3
"""
FIXED SNIPER TRADING SYSTEM - EXECUTES ALL SIGNALS
This system will execute ALL signals, not just the "best opportunity" instrument
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta

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

class FixedSniperTradingSystem:
    def __init__(self):
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        self.strategies = {
            'momentum': MomentumTradingStrategy(),
            'gold': GoldScalpingStrategy()
        }
        self.is_running = False
        self.scan_count = 0
        
        logger.info(f"🎯 FIXED SNIPER SYSTEM initialized with {len(self.active_accounts)} accounts")
    
    def sniper_scan_and_execute(self):
        """FIXED Sniper scan - execute ALL signals, not just best opportunity"""
        self.scan_count += 1
        logger.info(f"🎯 FIXED SNIPER SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        total_signals = 0
        total_executed = 0
        
        # Get market data for all accounts
        for account_id in self.active_accounts:
            try:
                client = self.account_manager.get_account_client(account_id)
                market_data = client.get_current_prices(['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'USD_CAD'])
                
                # Test each strategy and execute ALL signals
                for strategy_name, strategy in self.strategies.items():
                    try:
                        signals = strategy.analyze_market(market_data)
                        if signals:
                            logger.info(f"🎯 {strategy_name} generated {len(signals)} signals for account {account_id[-3:]}")
                            total_signals += len(signals)
                            
                            # EXECUTE ALL SIGNALS (not just best opportunity)
                            for signal in signals:
                                try:
                                    logger.info(f"🎯 EXECUTING SIGNAL: {signal.instrument} {signal.side.value} - Confidence: {signal.confidence:.3f}")
                                    
                                    # Calculate position size (1% risk - Conservative)
                                    account_info = client.get_account_info()
                                    risk_amount = account_info.balance * 0.01  # 1% risk
                                    
                                    # Get entry price from market data
                                    current_price = market_data.get(signal.instrument)
                                    if current_price:
                                        entry_price = current_price.ask if signal.side.value == 'BUY' else current_price.bid
                                    else:
                                        entry_price = 0.0
                                    
                                    # Calculate stop distance
                                    if signal.side.value == 'BUY':
                                        stop_distance = entry_price - signal.stop_loss
                                    else:
                                        stop_distance = signal.stop_loss - entry_price
                                    
                                    position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 10000
                                    
                                    # FIXED SNIPER EXECUTION
                                    result = client.place_market_order(
                                        instrument=signal.instrument,
                                        units=position_size,
                                        stop_loss=signal.stop_loss,
                                        take_profit=signal.take_profit
                                    )
                                    
                                    if result:
                                        total_executed += 1
                                        logger.info(f"🎯 SNIPER HIT: {signal.instrument} {signal.side.value} - Units: {position_size}")
                                    else:
                                        logger.error(f"❌ SNIPER MISS: {signal.instrument} {signal.side.value}")
                                        
                                except Exception as e:
                                    logger.error(f"❌ Signal execution failed: {e}")
                                    
                    except Exception as e:
                        logger.error(f"❌ {strategy_name} failed for account {account_id[-3:]}: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to get market data for account {account_id[-3:]}: {e}")
        
        logger.info(f"🎯 FIXED SNIPER SCAN #{self.scan_count} COMPLETE: {total_signals} signals, {total_executed} executed")
        return total_executed
    
    def start_sniper_scanning(self):
        """Start sniper scanning - EVERY 5 MINUTES (More frequent for testing)"""
        self.is_running = True
        logger.info("🎯 STARTING FIXED SNIPER SCANNING - EVERY 5 MINUTES...")
        
        while self.is_running:
            try:
                executed = self.sniper_scan_and_execute()
                logger.info(f"🎯 Next fixed sniper scan in 5 minutes... (Executed {executed} trades)")
                time.sleep(300)  # 5 minutes for testing
            except KeyboardInterrupt:
                logger.info("🛑 Fixed sniper system stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Fixed sniper system error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop scanning"""
        self.is_running = False
        logger.info("🛑 Fixed sniper system stopped")

def main():
    """Main fixed sniper system loop"""
    logger.info("🎯 STARTING FIXED SNIPER TRADING SYSTEM - EXECUTES ALL SIGNALS")
    
    sniper = FixedSniperTradingSystem()
    
    try:
        sniper.start_sniper_scanning()
    except KeyboardInterrupt:
        logger.info("🛑 Fixed sniper system stopped by user")
        sniper.stop()

if __name__ == "__main__":
    main()

