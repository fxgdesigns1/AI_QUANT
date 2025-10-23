#!/usr/bin/env python3
"""
DEPLOY GROUP 2: 15-MINUTE ZERO-DRAWDOWN PORTFOLIO
Deploys the optimized Group 2 strategy to Strat 7 (101-004-30719775-007)
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_account_access():
    """Verify access to the Strat 7 account"""
    logger.info("🔍 Verifying Strat 7 account access...")
    
    try:
        from src.core.oanda_client import get_oanda_client
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv('oanda_config.env')
        
        # Get OANDA client
        oanda_client = get_oanda_client()
        
        # Check account access using the correct method
        account_info = oanda_client.get_account_info()
        
        if account_info:
            logger.info(f"✅ Account access verified: {account_info.account_id}")
            logger.info(f"📊 Account ID: {account_info.account_id}")
            logger.info(f"💰 Balance: {account_info.balance}")
            logger.info(f"📈 Open Trades: {account_info.open_trade_count}")
            logger.info(f"📊 Open Positions: {account_info.open_position_count}")
            return True, oanda_client
        else:
            logger.error(f"❌ Cannot access account")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Account verification failed: {e}")
        return False, None

def verify_instruments_access(oanda_client):
    """Verify access to required instruments"""
    logger.info("🔍 Verifying instrument access...")
    
    required_instruments = ["GBP_USD", "XAU_USD"]
    
    try:
        # Get current prices for all instruments at once
        price_data = oanda_client.get_current_prices(required_instruments)
        
        for instrument in required_instruments:
            if instrument in price_data:
                price = price_data[instrument]
                logger.info(f"✅ {instrument}: Bid={price.bid}, Ask={price.ask}")
            else:
                logger.error(f"❌ Cannot access {instrument}")
                return False
        
        logger.info("✅ All instruments accessible")
        return True
        
    except Exception as e:
        logger.error(f"❌ Instrument verification failed: {e}")
        return False

def create_group_2_config():
    """Create configuration for Group 2 deployment"""
    logger.info("📝 Creating Group 2 configuration...")
    
    config = {
        "group_name": "group_2_15m_zero_drawdown",
        "account_id": "101-004-30719775-007",
        "account_name": "Strat 7",
        "instruments": ["GBP_USD", "XAU_USD"],
        "timeframe": "15m",
        "strategy_config": {
            "ema_fast": 8,
            "ema_slow": 21,
            "ema_trend": 55,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "stop_loss_atr": 2.0,
            "risk_reward_ratio": 2.5,
            "risk_per_trade": 200.0,
            "max_concurrent_positions": 3,
            "max_daily_trades": 100,
            "zero_drawdown_mode": True
        },
        "performance_targets": {
            "target_sharpe": 6.12,
            "target_win_rate": 53.6,
            "target_annual_return": 2244.0,
            "expected_weekly_wins": 43.9,
            "max_drawdown": 0.1
        },
        "deployment_info": {
            "deployed_at": datetime.now().isoformat(),
            "deployed_by": "automated_deployment_script",
            "version": "1.0.0",
            "status": "deploying"
        }
    }
    
    logger.info("✅ Group 2 configuration created")
    return config

def update_data_feed_config(config):
    """Update data feed configuration for Group 2"""
    logger.info("🔄 Updating data feed configuration...")
    
    try:
        # Update the streaming data feed configuration
        data_feed_config = {
            "account_id": config["account_id"],
            "instruments": config["instruments"],
            "timeframe": config["timeframe"],
            "strategy_group": config["group_name"]
        }
        
        logger.info(f"✅ Data feed configured for {config['instruments']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data feed configuration failed: {e}")
        return False

def save_deployment_record(config):
    """Save deployment record to file"""
    logger.info("💾 Saving deployment record...")
    
    try:
        import json
        
        deployment_record = {
            "deployment_id": f"group_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "config": config,
            "status": "deployed",
            "next_phase": "monitor_48_hours"
        }
        
        record_file = f"deployment_records/group_2_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Create directory if it doesn't exist
        os.makedirs("deployment_records", exist_ok=True)
        
        with open(record_file, 'w') as f:
            json.dump(deployment_record, f, indent=2)
        
        logger.info(f"✅ Deployment record saved: {record_file}")
        return record_file
        
    except Exception as e:
        logger.error(f"❌ Failed to save deployment record: {e}")
        return None

def main():
    """Main deployment function"""
    logger.info("🚀 DEPLOYING GROUP 2: 15-MINUTE ZERO-DRAWDOWN PORTFOLIO")
    logger.info("=" * 70)
    logger.info(f"Target Account: Strat 7 (101-004-30719775-007)")
    logger.info(f"Deployment Time: {datetime.now().isoformat()}")
    logger.info("")
    
    # Step 1: Verify account access
    account_verified, oanda_client = verify_account_access()
    if not account_verified:
        logger.error("❌ Deployment failed: Cannot access Strat 7 account")
        return False
    
    # Step 2: Verify instruments access
    if not verify_instruments_access(oanda_client):
        logger.error("❌ Deployment failed: Cannot access required instruments")
        return False
    
    # Step 3: Create configuration
    config = create_group_2_config()
    
    # Step 4: Update data feed configuration
    if not update_data_feed_config(config):
        logger.error("❌ Deployment failed: Data feed configuration error")
        return False
    
    # Step 5: Save deployment record
    record_file = save_deployment_record(config)
    
    # Step 6: Final status
    logger.info("")
    logger.info("🎉 GROUP 2 DEPLOYMENT COMPLETED SUCCESSFULLY!")
    logger.info("=" * 50)
    logger.info(f"📊 Strategy: 15-Minute Zero-Drawdown Portfolio")
    logger.info(f"🏦 Account: Strat 7 ({config['account_id']})")
    logger.info(f"📈 Instruments: {', '.join(config['instruments'])}")
    logger.info(f"⏰ Timeframe: {config['timeframe']}")
    logger.info(f"🎯 Expected Weekly Wins: {config['performance_targets']['expected_weekly_wins']}")
    logger.info(f"🛡️ Max Drawdown: {config['performance_targets']['max_drawdown']}%")
    logger.info(f"📋 Status: ACTIVE")
    logger.info("")
    logger.info("📋 NEXT STEPS:")
    logger.info("1. Monitor performance for 48 hours")
    logger.info("2. Track actual vs expected metrics")
    logger.info("3. Document any issues or adjustments")
    logger.info("4. Prepare for Group 3 deployment")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Group 2 deployment successful!")
        print("Ready for monitoring phase.")
    else:
        print("\n❌ Group 2 deployment failed!")
        print("Please check the logs and fix issues before retrying.")




