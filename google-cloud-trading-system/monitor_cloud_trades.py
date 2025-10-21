#!/usr/bin/env python3
"""
Google Cloud Trade Monitor Script
Monitors the Google Cloud trading system and alerts if no trades are generated within a specified time period.
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_cloud_app_url():
    """Get the URL of the Google Cloud App Engine application"""
    # Try to get from environment variable
    app_url = os.environ.get('CLOUD_APP_URL')
    if app_url:
        return app_url
    
    # Try to get from gcloud command
    import subprocess
    try:
        result = subprocess.run(['gcloud', 'app', 'describe', '--format=json'], 
                              capture_output=True, text=True, check=True)
        app_info = json.loads(result.stdout)
        default_hostname = app_info.get('defaultHostname')
        if default_hostname:
            return f"https://{default_hostname}"
    except:
        pass
    
    # Ask the user
    print("Could not determine Google Cloud App URL automatically.")
    app_url = input("Please enter your Google Cloud App URL: ")
    return app_url

def check_for_trades(app_url, api_key=None, max_wait_minutes=30):
    """Check if trades have been executed within the specified time period"""
    logger.info(f"🔍 Monitoring for trades on {app_url} (max wait: {max_wait_minutes} minutes)")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=max_wait_minutes)
    
    # Initial trade count
    initial_trade_count = get_trade_count(app_url, api_key)
    logger.info(f"📊 Initial trade count: {initial_trade_count}")
    
    while datetime.now() < end_time:
        # Check current trade count
        current_trade_count = get_trade_count(app_url, api_key)
        new_trades = current_trade_count - initial_trade_count
        
        if new_trades > 0:
            logger.info(f"✅ {new_trades} new trades detected!")
            return True
        
        # Check system status
        system_status = get_system_status(app_url, api_key)
        logger.info(f"📊 System status: {system_status}")
        
        # Sleep for a bit
        logger.info(f"⏳ Waiting for trades... ({int((end_time - datetime.now()).total_seconds())} seconds remaining)")
        time.sleep(60)  # Check every minute
    
    logger.warning(f"❌ No trades detected within {max_wait_minutes} minutes")
    return False

def get_trade_count(app_url, api_key=None):
    """Get the current trade count from the Google Cloud application"""
    try:
        headers = {}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        
        response = requests.get(f"{app_url}/api/trades/count", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('count', 0)
        else:
            logger.warning(f"⚠️ Failed to get trade count: {response.status_code}")
            return 0
    except Exception as e:
        logger.error(f"❌ Error getting trade count: {e}")
        return 0

def get_system_status(app_url, api_key=None):
    """Get the current system status from the Google Cloud application"""
    try:
        headers = {}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        
        response = requests.get(f"{app_url}/api/system/status", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"⚠️ Failed to get system status: {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        return {}

def alert_no_trades():
    """Alert that no trades have been generated"""
    logger.error("🚨 ALERT: No trades generated within the specified time period")
    logger.error("🔧 Consider checking the following:")
    logger.error("   1. Google Cloud logs for errors")
    logger.error("   2. Market conditions (low volatility?)")
    logger.error("   3. Strategy parameters (still too strict?)")
    logger.error("   4. Data feed issues (receiving fresh data?)")
    logger.error("   5. Order execution issues (OANDA connection?)")

def main():
    """Main monitoring function"""
    logger.info("🚀 Starting Google Cloud Trade Monitor")
    
    # Get the Google Cloud App URL
    app_url = get_cloud_app_url()
    logger.info(f"🔗 Google Cloud App URL: {app_url}")
    
    # Check for trades with a 30-minute timeout
    trades_detected = check_for_trades(app_url, max_wait_minutes=30)
    
    if not trades_detected:
        alert_no_trades()
        return False
    
    logger.info("✅ Trading system is active and generating trades")
    return True

if __name__ == '__main__':
    main()
