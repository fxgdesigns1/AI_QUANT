#!/usr/bin/env python3
"""
FORCE TRADES ON ALL ACCOUNTS
This will place trades on ALL active accounts
"""

import os
import sys
import time
import logging

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

def force_trades_all_accounts():
    """Force place trades on ALL accounts"""
    logger.info("🚀 FORCING TRADES ON ALL ACCOUNTS...")
    
    # Get account manager
    account_manager = get_account_manager()
    active_accounts = account_manager.get_active_accounts()
    
    logger.info(f"📊 Found {len(active_accounts)} active accounts")
    
    total_trades_placed = 0
    
    for i, account_id in enumerate(active_accounts):
        try:
            logger.info(f"🎯 ACCOUNT {i+1}/{len(active_accounts)}: {account_id}")
            
            # Create OANDA client for this account
            client = OandaClient(account_id=account_id)
            
            # Get account info
            account_info = client.get_account_info()
            balance = account_info.balance
            logger.info(f"💰 Account balance: ${balance:.2f}")
            
            # Get current prices
            instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD']
            market_data = client.get_current_prices(instruments)
            
            # Place EUR_USD trade
            try:
                logger.info("🚀 PLACING EUR_USD BUY ORDER...")
                
                # Calculate position size (1% risk)
                risk_amount = balance * 0.01
                stop_distance = 0.005  # 50 pips
                position_size = int(risk_amount / stop_distance)
                
                # Place market order
                result = client.place_market_order(
                    instrument='EUR_USD',
                    units=position_size,  # Positive = BUY
                    stop_loss=market_data['EUR_USD'].bid - 0.005,
                    take_profit=market_data['EUR_USD'].ask + 0.01
                )
                
                if result:
                    total_trades_placed += 1
                    logger.info(f"✅ EUR_USD TRADE PLACED! Units: {position_size}")
                else:
                    logger.error("❌ EUR_USD TRADE FAILED!")
                    
            except Exception as e:
                logger.error(f"❌ EUR_USD trade failed: {e}")
            
            # Place XAU_USD trade
            try:
                logger.info("🚀 PLACING XAU_USD BUY ORDER...")
                
                # Calculate position size for Gold
                risk_amount = balance * 0.01
                stop_distance = 5.0  # $5 stop
                position_size = int(risk_amount / stop_distance)
                
                # Place market order
                result = client.place_market_order(
                    instrument='XAU_USD',
                    units=position_size,  # Positive = BUY
                    stop_loss=market_data['XAU_USD'].bid - 5.0,
                    take_profit=market_data['XAU_USD'].ask + 10.0
                )
                
                if result:
                    total_trades_placed += 1
                    logger.info(f"✅ XAU_USD TRADE PLACED! Units: {position_size}")
                else:
                    logger.error("❌ XAU_USD TRADE FAILED!")
                    
            except Exception as e:
                logger.error(f"❌ XAU_USD trade failed: {e}")
            
            # Place GBP_USD trade
            try:
                logger.info("🚀 PLACING GBP_USD BUY ORDER...")
                
                # Calculate position size
                risk_amount = balance * 0.01
                stop_distance = 0.005  # 50 pips
                position_size = int(risk_amount / stop_distance)
                
                # Place market order
                result = client.place_market_order(
                    instrument='GBP_USD',
                    units=position_size,  # Positive = BUY
                    stop_loss=market_data['GBP_USD'].bid - 0.005,
                    take_profit=market_data['GBP_USD'].ask + 0.01
                )
                
                if result:
                    total_trades_placed += 1
                    logger.info(f"✅ GBP_USD TRADE PLACED! Units: {position_size}")
                else:
                    logger.error("❌ GBP_USD TRADE FAILED!")
                    
            except Exception as e:
                logger.error(f"❌ GBP_USD trade failed: {e}")
            
            logger.info(f"✅ Account {account_id} completed")
            time.sleep(1)  # Brief pause between accounts
            
        except Exception as e:
            logger.error(f"❌ Account {account_id} failed: {e}")
    
    logger.info(f"🎯 TOTAL TRADES PLACED: {total_trades_placed}")
    logger.info("✅ ALL ACCOUNTS PROCESSED!")

if __name__ == "__main__":
    force_trades_all_accounts()


