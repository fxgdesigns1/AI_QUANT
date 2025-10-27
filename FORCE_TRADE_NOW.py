#!/usr/bin/env python3
"""
FORCE TRADE NOW - DIRECT TRADING SYSTEM
This will place actual trades immediately
"""

import os
import sys
import time
import logging

# Set up environment
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ENVIRONMENT'] = "practice"

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.dynamic_account_manager import get_account_manager
from src.core.oanda_client import OandaClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def force_trade_now():
    """Force place trades immediately"""
    logger.info("🚀 FORCING TRADES NOW...")
    
    # Get account manager
    account_manager = get_account_manager()
    active_accounts = account_manager.get_active_accounts()
    
    logger.info(f"📊 Found {len(active_accounts)} active accounts")
    
    # Get first account for testing
    account_id = active_accounts[0]
    logger.info(f"🎯 Using account: {account_id}")
    
    # Create OANDA client
    client = OandaClient(account_id=account_id)
    
    # Get current prices
    instruments = ['EUR_USD', 'GBP_USD', 'XAU_USD']
    market_data = client.get_current_prices(instruments)
    
    logger.info("📊 Current market prices:")
    for instrument, price in market_data.items():
        logger.info(f"   {instrument}: {price.bid} / {price.ask}")
    
    # Place a simple EUR_USD trade
    try:
        logger.info("🚀 PLACING EUR_USD BUY ORDER...")
        
        # Get account info
        account_info = client.get_account_info()
        balance = account_info.balance
        logger.info(f"💰 Account balance: ${balance:.2f}")
        
        # Calculate position size (1% risk)
        risk_amount = balance * 0.01
        stop_distance = 0.005  # 50 pips
        position_size = int(risk_amount / stop_distance)
        
        logger.info(f"📊 Position size: {position_size} units")
        logger.info(f"📊 Risk amount: ${risk_amount:.2f}")
        
        # Place market order (positive units = BUY)
        result = client.place_market_order(
            instrument='EUR_USD',
            units=position_size,  # Positive = BUY
            stop_loss=market_data['EUR_USD'].bid - 0.005,
            take_profit=market_data['EUR_USD'].ask + 0.01
        )
        
        if result:
            logger.info("✅ TRADE PLACED SUCCESSFULLY!")
            logger.info(f"   Instrument: EUR_USD")
            logger.info(f"   Side: BUY")
            logger.info(f"   Units: {position_size}")
            logger.info(f"   Entry: {market_data['EUR_USD'].ask}")
            logger.info(f"   Stop Loss: {market_data['EUR_USD'].bid - 0.005}")
            logger.info(f"   Take Profit: {market_data['EUR_USD'].ask + 0.01}")
        else:
            logger.error("❌ TRADE FAILED!")
            
    except Exception as e:
        logger.error(f"❌ Trade placement failed: {e}")
    
    # Place a Gold trade
    try:
        logger.info("🚀 PLACING XAU_USD BUY ORDER...")
        
        # Calculate position size for Gold
        risk_amount = balance * 0.01
        stop_distance = 5.0  # $5 stop
        position_size = int(risk_amount / stop_distance)
        
        logger.info(f"📊 Gold position size: {position_size} units")
        
        # Place market order (positive units = BUY)
        result = client.place_market_order(
            instrument='XAU_USD',
            units=position_size,  # Positive = BUY
            stop_loss=market_data['XAU_USD'].bid - 5.0,
            take_profit=market_data['XAU_USD'].ask + 10.0
        )
        
        if result:
            logger.info("✅ GOLD TRADE PLACED SUCCESSFULLY!")
            logger.info(f"   Instrument: XAU_USD")
            logger.info(f"   Side: BUY")
            logger.info(f"   Units: {position_size}")
            logger.info(f"   Entry: {market_data['XAU_USD'].ask}")
            logger.info(f"   Stop Loss: {market_data['XAU_USD'].bid - 5.0}")
            logger.info(f"   Take Profit: {market_data['XAU_USD'].ask + 10.0}")
        else:
            logger.error("❌ GOLD TRADE FAILED!")
            
    except Exception as e:
        logger.error(f"❌ Gold trade placement failed: {e}")
    
    # Check positions
    logger.info("🔍 CHECKING POSITIONS...")
    try:
        trades = client.get_open_trades()
        
        logger.info(f"📊 Open trades: {len(trades)}")
        
        for trade in trades:
            logger.info(f"   Trade: {trade.get('instrument', 'Unknown')} {trade.get('units', 0)} units")
            
    except Exception as e:
        logger.error(f"❌ Failed to check positions: {e}")

if __name__ == "__main__":
    force_trade_now()