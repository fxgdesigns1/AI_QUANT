#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.insert(0, '.')

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
    os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Import the Telegram notifier
try:
    from src.core.telegram_notifier import TelegramNotifier
    from src.core.oanda_client import OandaClient
    from src.core.session_manager import get_session_manager
    logger.info("✅ Core modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import core modules: {e}")
    sys.exit(1)

def send_final_status():
    """Send a final status update to Telegram"""
    
    # Initialize modules
    notifier = TelegramNotifier()
    client = OandaClient()
    session_manager = get_session_manager()
    
    # Get account info
    account_info = client.get_account_info()
    balance = account_info.balance
    
    # Get current session info
    now = datetime.now()
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    # Get open positions
    positions = client.get_positions()
    open_positions = []
    for position in positions:
        # Parse the position data based on the actual structure
        # This may vary depending on the OANDA API response format
        try:
            position_data = position if isinstance(position, dict) else position.__dict__
            instrument = position_data.get('instrument', 'Unknown')
            
            # Check if long/short are dictionaries or objects
            long_data = position_data.get('long', {})
            short_data = position_data.get('short', {})
            
            if isinstance(long_data, dict):
                long_units = long_data.get('units', '0')
                long_avg_price = long_data.get('averagePrice', '0')
            else:
                long_units = getattr(long_data, 'units', '0')
                long_avg_price = getattr(long_data, 'averagePrice', '0')
                
            if isinstance(short_data, dict):
                short_units = short_data.get('units', '0')
                short_avg_price = short_data.get('averagePrice', '0')
            else:
                short_units = getattr(short_data, 'units', '0')
                short_avg_price = getattr(short_data, 'averagePrice', '0')
            
            units = long_units if long_units != "0" else short_units
            side = "LONG" if long_units != "0" else "SHORT"
            entry_price = long_avg_price if long_units != "0" else short_avg_price
            pl = position_data.get('unrealizedPL', '0')
            
            open_positions.append({
                "instrument": instrument,
                "side": side,
                "units": units,
                "entry_price": entry_price,
                "pl": pl
            })
        except Exception as e:
            logger.warning(f"Error parsing position data: {e}")
            # Add a simplified entry if we can't parse the full data
            open_positions.append({
                "instrument": "Unknown",
                "side": "Unknown",
                "units": "Unknown",
                "entry_price": "Unknown",
                "pl": "Unknown"
            })
    
    # Construct the message
    message = f"""📊 <b>CONTEXTUAL TRADING SYSTEM - FINAL STATUS</b>

<b>Implementation Complete!</b> 🎉

<b>Current Status:</b>
- Account Balance: {balance} USD
- Open Positions: {len(open_positions)}
- Current Session: {session_description} (Quality: {session_quality}/100)

<b>Core Modules Implemented:</b>
✅ Session Manager
✅ Historical News Fetcher
✅ Price Context Analyzer
✅ Quality Scoring System
✅ Trade Approver
✅ Hybrid Execution System
✅ Enhanced Morning Scanner
✅ Scheduled Scanners
✅ Contextual Backtest System

<b>Next Steps:</b>
1. Run Monte Carlo optimization with contextual modules
2. Calibrate quality scoring algorithm
3. Fix Gold pip calculation
4. Integrate real news API
5. Complete TALib integration

<b>Documentation:</b>
- CONTEXTUAL_TRADING_SYSTEM_FINAL.md
- DEPLOYMENT_PLAN.md
- SUMMARY_FOR_USER.md

The system is ready for optimization and deployment!
"""
    
    # Send the message
    notifier.send_system_status(message)
    logger.info("✅ Final status update sent to Telegram")

if __name__ == "__main__":
    send_final_status()
