#!/usr/bin/env python3
"""
STABLE TRADING SYSTEM - NO MIND CHANGING
This system makes ONE decision and sticks to it - no overtrading
"""

import os
import sys
import time
import logging
import yaml
from datetime import datetime, timedelta

# Set up environment
os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import get_account_manager
from src.core.oanda_client import OandaClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StableTradingSystem:
    def __init__(self):
        self.account_manager = get_account_manager()
        self.active_accounts = self.account_manager.get_active_accounts()
        
        # Load accounts.yaml to get strategy mappings
        self.accounts_config = self._load_accounts_config()
        
        # Track what we've already traded to avoid duplicates
        self.traded_today = {}
        self.is_running = False
        self.scan_count = 0
        
        logger.info(f"🎯 STABLE SYSTEM initialized with {len(self.active_accounts)} accounts")
    
    def _load_accounts_config(self):
        """Load accounts configuration"""
        try:
            config_path = '/Users/mac/quant_system_clean/google-cloud-trading-system/accounts.yaml'
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"❌ Failed to load accounts config: {e}")
            return {}
    
    def get_trading_pairs_for_account(self, account_id):
        """Get trading pairs for an account"""
        try:
            for account in self.accounts_config.get('accounts', []):
                if account['id'] == account_id:
                    return account.get('trading_pairs', ['EUR_USD', 'GBP_USD', 'XAU_USD'])
            return ['EUR_USD', 'GBP_USD', 'XAU_USD']
        except Exception as e:
            logger.error(f"❌ Error getting trading pairs for account {account_id}: {e}")
            return ['EUR_USD', 'GBP_USD', 'XAU_USD']
    
    def has_already_traded_today(self, account_id, instrument):
        """Check if we've already traded this instrument today"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"{account_id}_{instrument}_{today}"
        return key in self.traded_today
    
    def mark_as_traded_today(self, account_id, instrument):
        """Mark this instrument as traded today"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"{account_id}_{instrument}_{today}"
        self.traded_today[key] = True
    
    def get_simple_trend_direction(self, market_data):
        """Get simple trend direction - ONE decision only"""
        opportunities = []
        
        for instrument, price_data in market_data.items():
            try:
                # Get current price
                current_price = price_data.ask if hasattr(price_data, 'ask') else price_data
                
                # Simple decision: If price > 1.0 for forex, BUY. If < 1.0, SELL
                # For Gold (XAU_USD), if price > 4000, BUY
                if instrument == 'XAU_USD':
                    if current_price > 4000:
                        direction = 'BUY'
                    else:
                        direction = 'SELL'
                else:
                    # For forex pairs, use a simple rule
                    if current_price > 1.0:
                        direction = 'BUY'
                    else:
                        direction = 'SELL'
                
                opportunities.append({
                    'instrument': instrument,
                    'side': direction,
                    'entry_price': current_price,
                    'stop_loss': current_price * 0.998 if direction == 'BUY' else current_price * 1.002,
                    'take_profit': current_price * 1.004 if direction == 'BUY' else current_price * 0.996,
                    'confidence': 0.8,
                    'reason': f'Simple trend rule for {instrument}'
                })
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return opportunities
    
    def stable_scan_and_execute(self):
        """Stable scan - ONE decision per instrument per day"""
        self.scan_count += 1
        logger.info(f"🎯 STABLE SCAN #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        total_opportunities = 0
        total_executed = 0
        
        # Process each account
        for account_id in self.active_accounts:
            try:
                logger.info(f"🔍 Stable analysis for account {account_id[-3:]}")
                
                # Get trading pairs for this account
                trading_pairs = self.get_trading_pairs_for_account(account_id)
                
                # Get client and market data
                client = self.account_manager.get_account_client(account_id)
                market_data = client.get_current_prices(trading_pairs)
                
                # Get simple opportunities
                opportunities = self.get_simple_trend_direction(market_data)
                
                if opportunities:
                    logger.info(f"🎯 Found {len(opportunities)} opportunities for account {account_id[-3:]}")
                    total_opportunities += len(opportunities)
                    
                    # Execute ONLY if we haven't traded this instrument today
                    for opp in opportunities:
                        if not self.has_already_traded_today(account_id, opp['instrument']):
                            try:
                                logger.info(f"🎯 STABLE EXECUTION: {opp['instrument']} {opp['side']} - {opp['reason']}")
                                
                                # Get account risk settings
                                account_info = client.get_account_info()
                                risk_per_trade = 0.01  # 1% risk per trade
                                
                                # Try to get risk settings from config
                                for account in self.accounts_config.get('accounts', []):
                                    if account['id'] == account_id:
                                        risk_per_trade = account.get('risk_settings', {}).get('max_risk_per_trade', 0.01)
                                        break
                                
                                risk_amount = account_info.balance * risk_per_trade
                                
                                # Calculate position size
                                stop_distance = abs(opp['entry_price'] - opp['stop_loss'])
                                position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 10000
                                
                                # Execute the trade
                                result = client.place_market_order(
                                    instrument=opp['instrument'],
                                    units=position_size if opp['side'] == 'BUY' else -position_size,
                                    stop_loss=opp['stop_loss'],
                                    take_profit=opp['take_profit']
                                )
                                
                                if result:
                                    total_executed += 1
                                    # Mark as traded today to prevent re-entry
                                    self.mark_as_traded_today(account_id, opp['instrument'])
                                    logger.info(f"🎯 STABLE SUCCESS: {opp['instrument']} {opp['side']} - Units: {position_size}")
                                else:
                                    logger.error(f"❌ STABLE MISS: {opp['instrument']} {opp['side']}")
                                    
                            except Exception as e:
                                logger.error(f"❌ Stable execution failed: {e}")
                        else:
                            logger.info(f"⏭️ Already traded {opp['instrument']} today - skipping")
                else:
                    logger.info(f"📊 No opportunities found for account {account_id[-3:]}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to process account {account_id[-3:]}: {e}")
        
        logger.info(f"🎯 STABLE SCAN #{self.scan_count} COMPLETE: {total_opportunities} opportunities, {total_executed} executed")
        return total_executed
    
    def start_stable_trading(self):
        """Start stable trading - EVERY 30 MINUTES (less frequent)"""
        self.is_running = True
        logger.info("🎯 STARTING STABLE TRADING - EVERY 30 MINUTES...")
        
        while self.is_running:
            try:
                executed = self.stable_scan_and_execute()
                logger.info(f"🎯 Next stable scan in 30 minutes... (Executed {executed} trades)")
                time.sleep(1800)  # 30 minutes
            except KeyboardInterrupt:
                logger.info("🛑 Stable system stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Stable system error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def stop(self):
        """Stop trading"""
        self.is_running = False
        logger.info("🛑 Stable system stopped")

def main():
    """Main stable trading loop"""
    logger.info("🎯 STARTING STABLE TRADING SYSTEM - NO MIND CHANGING")
    
    system = StableTradingSystem()
    
    try:
        system.start_stable_trading()
    except KeyboardInterrupt:
        logger.info("🛑 Stable system stopped by user")
        system.stop()

if __name__ == "__main__":
    main()
