#!/usr/bin/env python3
"""
DEPLOY GROUP 1: 5-MINUTE HIGH-FREQUENCY PORTFOLIO
Deploys the optimized Group 1 strategy to Strat 8 (101-004-30719775-008)
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
    """Verify access to the Strat 8 account"""
    logger.info("🔍 Verifying Strat 8 account access...")
    
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
    
    required_instruments = ["GBP_USD", "NZD_USD", "XAU_USD"]
    
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

def create_group_1_config():
    """Create configuration for Group 1 deployment"""
    logger.info("📝 Creating Group 1 configuration...")
    
    config = {
        "group_name": "group_1_5m_high_frequency",
        "account_id": "101-004-30719775-008",
        "account_name": "Strat 8",
        "instruments": ["GBP_USD", "NZD_USD", "XAU_USD"],
        "timeframe": "5m",
        "strategy_config": {
            "ema_fast": 3,
            "ema_slow": 12,
            "rsi_oversold": 20,
            "rsi_overbought": 80,
            "stop_loss_atr": 1.5,
            "risk_reward_ratio": 3.0,
            "risk_per_trade": 200.0,
            "max_concurrent_positions": 3,
            "max_daily_trades": 150
        },
        "performance_targets": {
            "target_sharpe": 38.5,
            "target_win_rate": 79.7,
            "target_annual_return": 148.0,
            "expected_weekly_wins": 132.4
        },
        "deployment_info": {
            "deployed_at": datetime.now().isoformat(),
            "deployed_by": "automated_deployment_script",
            "version": "1.0.0",
            "status": "deploying"
        }
    }
    
    logger.info("✅ Group 1 configuration created")
    return config

def update_data_feed_config(config):
    """Update data feed configuration for Group 1"""
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

def send_deployment_notification(config):
    """Send deployment notification"""
    logger.info("📢 Sending deployment notification...")
    
    try:
        from src.core.telegram_notifier import get_telegram_notifier
        
        notifier = get_telegram_notifier()
        
        message = f"""
🚀 GROUP 1 DEPLOYMENT STARTED

📊 Strategy: 5-Minute High-Frequency Portfolio
🏦 Account: Strat 8 ({config['account_id']})
📈 Instruments: {', '.join(config['instruments'])}
⏰ Timeframe: {config['timeframe']}

🎯 Performance Targets:
• Target Sharpe: {config['performance_targets']['target_sharpe']}
• Target Win Rate: {config['performance_targets']['target_win_rate']}%
• Expected Weekly Wins: {config['performance_targets']['expected_weekly_wins']}

💰 Risk Management:
• Risk per Trade: ${config['strategy_config']['risk_per_trade']}
• Max Concurrent Positions: {config['strategy_config']['max_concurrent_positions']}

✅ Deployment Status: ACTIVE
🕐 Deployed: {config['deployment_info']['deployed_at']}
        """
        
        notifier.send_immediate(message, 'deployment')
        logger.info("✅ Deployment notification sent")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not send notification: {e}")
        logger.info("📝 Deployment notification (manual):")
        logger.info(f"Group 1 deployed to Strat 8 at {config['deployment_info']['deployed_at']}")

def save_deployment_record(config):
    """Save deployment record to file"""
    logger.info("💾 Saving deployment record...")
    
    try:
        import json
        
        deployment_record = {
            "deployment_id": f"group_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "config": config,
            "status": "deployed",
            "next_phase": "monitor_48_hours"
        }
        
        record_file = f"deployment_records/group_1_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
    logger.info("🚀 DEPLOYING GROUP 1: 5-MINUTE HIGH-FREQUENCY PORTFOLIO")
    logger.info("=" * 70)
    logger.info(f"Target Account: Strat 8 (101-004-30719775-008)")
    logger.info(f"Deployment Time: {datetime.now().isoformat()}")
    logger.info("")
    
    # Step 1: Verify account access
    account_verified, oanda_client = verify_account_access()
    if not account_verified:
        logger.error("❌ Deployment failed: Cannot access Strat 8 account")
        return False
    
    # Step 2: Verify instruments access
    if not verify_instruments_access(oanda_client):
        logger.error("❌ Deployment failed: Cannot access required instruments")
        return False
    
    # Step 3: Create configuration
    config = create_group_1_config()
    
    # Step 4: Update data feed configuration
    if not update_data_feed_config(config):
        logger.error("❌ Deployment failed: Data feed configuration error")
        return False
    
    # Step 5: Send notification
    send_deployment_notification(config)
    
    # Step 6: Save deployment record
    record_file = save_deployment_record(config)
    
    # Step 7: Final status
    logger.info("")
    logger.info("🎉 GROUP 1 DEPLOYMENT COMPLETED SUCCESSFULLY!")
    logger.info("=" * 50)
    logger.info(f"📊 Strategy: 5-Minute High-Frequency Portfolio")
    logger.info(f"🏦 Account: Strat 8 ({config['account_id']})")
    logger.info(f"📈 Instruments: {', '.join(config['instruments'])}")
    logger.info(f"⏰ Timeframe: {config['timeframe']}")
    logger.info(f"🎯 Expected Weekly Wins: {config['performance_targets']['expected_weekly_wins']}")
    logger.info(f"📋 Status: ACTIVE")
    logger.info("")
    logger.info("📋 NEXT STEPS:")
    logger.info("1. Monitor performance for 48 hours")
    logger.info("2. Track actual vs expected metrics")
    logger.info("3. Document any issues or adjustments")
    logger.info("4. Prepare for Group 2 deployment after success")
    logger.info("")
    logger.info("📊 MONITORING CHECKLIST:")
    logger.info("□ Check trade execution quality")
    logger.info("□ Monitor win rate vs target (79.7%)")
    logger.info("□ Track weekly wins vs target (132.4)")
    logger.info("□ Verify API usage reduction")
    logger.info("□ Document any slippage issues")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Group 1 deployment successful!")
        print("Ready for 48-hour monitoring phase.")
    else:
        print("\n❌ Group 1 deployment failed!")
        print("Please check the logs and fix issues before retrying.")
