#!/usr/bin/env python3
"""
Check Trading System Status and Recent Trades
"""
import os
import sys
import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables
os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
os.environ['OANDA_ACCOUNT_ID'] = "101-004-30719775-008"

def check_account_status():
    """Check account status and positions"""
    try:
        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Get account info
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account = response.json()['account']
            logger.info(f"✅ Account Status:")
            logger.info(f"   Balance: ${account.get('balance', 'N/A')}")
            logger.info(f"   Unrealized P&L: ${account.get('unrealizedPL', 'N/A')}")
            logger.info(f"   NAV: ${account.get('NAV', 'N/A')}")
        
        # Get positions
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/positions"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            positions = response.json().get('positions', [])
            logger.info(f"📊 Open Positions: {len(positions)}")
            for pos in positions:
                if float(pos.get('long', {}).get('units', 0)) != 0 or float(pos.get('short', {}).get('units', 0)) != 0:
                    logger.info(f"   • {pos['instrument']}: Long={pos.get('long', {}).get('units', 0)}, Short={pos.get('short', {}).get('units', 0)}, P&L={pos.get('unrealizedPL', '0')}")
        
        # Get trades
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            trades = response.json().get('trades', [])
            logger.info(f"📈 Open Trades: {len(trades)}")
            for trade in trades[:5]:  # Show first 5
                logger.info(f"   • {trade['instrument']} {trade['currentUnits']} @ {trade.get('price', 'N/A')} | P&L: ${trade.get('unrealizedPL', '0')}")
        
        # Get recent transactions
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/transactions"
        since = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'
        params = {'since': since}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            transactions = response.json().get('transactions', [])
            recent_trades = [t for t in transactions if t.get('type') == 'ORDER_FILL']
            logger.info(f"🔄 Recent Trades (Last Hour): {len(recent_trades)}")
            for trade in recent_trades[-5:]:  # Show last 5
                logger.info(f"   • {trade.get('instrument', 'N/A')} {trade.get('units', 0)} @ {trade.get('price', 'N/A')} | Time: {trade.get('time', 'N/A')}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking account: {e}")
        return False

def check_system_processes():
    """Check if trading systems are running"""
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = {
            'ai_trading': 'ai_trading_system.py' in result.stdout,
            'automated_trading': 'automated_trading_system.py' in result.stdout,
            'dashboard': 'advanced_dashboard.py' in result.stdout,
            'cloud_system': 'google-cloud-trading-system/main.py' in result.stdout,
        }
        
        logger.info("🖥️  System Processes:")
        for name, running in processes.items():
            status = "✅ Running" if running else "❌ Not Running"
            logger.info(f"   • {name}: {status}")
        
        return all(processes.values())
    except Exception as e:
        logger.error(f"❌ Error checking processes: {e}")
        return False

def main():
    """Main check"""
    logger.info("="*80)
    logger.info("📊 TRADING SYSTEM STATUS CHECK")
    logger.info("="*80)
    
    check_system_processes()
    logger.info("")
    check_account_status()
    
    logger.info("="*80)
    logger.info("✅ Status check complete")
    logger.info("="*80)

if __name__ == "__main__":
    main()
