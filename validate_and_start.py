#!/usr/bin/env python3
"""
VALIDATE AND START ALL SYSTEMS
Tests connectivity, then starts all trading systems
"""
import os
import sys
import time
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables
os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
os.environ['OANDA_ACCOUNT_ID'] = "101-004-30719775-008"
os.environ['OANDA_ENVIRONMENT'] = "practice"
os.environ['TELEGRAM_TOKEN'] = "7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
os.environ['PYTHONPATH'] = "/workspace"

def test_oanda_connection():
    """Test OANDA API connection"""
    logger.info("🔍 Testing OANDA API connection...")
    try:
        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account = response.json()['account']
            logger.info(f"✅ OANDA connection successful")
            logger.info(f"   Account: {account_id}")
            logger.info(f"   Balance: ${account.get('balance', 'N/A')}")
            return True
        else:
            logger.error(f"❌ OANDA connection failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ OANDA connection error: {e}")
        return False

def test_telegram_connection():
    """Test Telegram bot connection"""
    logger.info("🔍 Testing Telegram connection...")
    try:
        token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            logger.warning("⚠️ Telegram credentials not set")
            return False
        
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            logger.info(f"✅ Telegram connection successful")
            logger.info(f"   Bot: @{bot_info['result'].get('username', 'N/A')}")
            
            # Send test message
            test_url = f"https://api.telegram.org/bot{token}/sendMessage"
            test_msg = f"✅ System validation complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            requests.post(test_url, json={'chat_id': chat_id, 'text': test_msg}, timeout=10)
            logger.info("   Test message sent")
            return True
        else:
            logger.error(f"❌ Telegram connection failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram connection error: {e}")
        return False

def test_imports():
    """Test that all required modules can be imported"""
    logger.info("🔍 Testing Python imports...")
    try:
        import requests
        import yaml
        import flask
        import pandas
        import numpy
        logger.info("✅ All core imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False

def main():
    """Main validation and startup"""
    logger.info("="*80)
    logger.info("🚀 VALIDATING AND STARTING ALL TRADING SYSTEMS")
    logger.info("="*80)
    
    # Run tests
    tests = [
        ("Python Imports", test_imports),
        ("OANDA API", test_oanda_connection),
        ("Telegram Bot", test_telegram_connection),
    ]
    
    results = {}
    for name, test_func in tests:
        results[name] = test_func()
        time.sleep(1)
    
    # Summary
    logger.info("="*80)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("="*80)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("="*80)
        logger.info("✅ ALL TESTS PASSED - STARTING SYSTEMS")
        logger.info("="*80)
        
        # Import and start the unified startup script
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, "/workspace/start_all_systems.py"],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ Startup script launched (PID: {proc.pid})")
        logger.info("📊 Systems should be starting now...")
        
        # Send startup notification
        try:
            token = os.getenv('TELEGRAM_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            message = f"""🚀 TRADING SYSTEMS STARTING

✅ Validation complete
✅ All systems initializing

📊 Systems:
• AI Trading System
• Automated Trading System  
• Dashboard (Port 8080)
• Cloud Trading System

⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

System will be fully operational in 1-2 minutes."""
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
        except Exception as e:
            logger.warning(f"⚠️ Could not send notification: {e}")
    else:
        logger.error("="*80)
        logger.error("❌ VALIDATION FAILED - FIX ISSUES BEFORE STARTING")
        logger.error("="*80)
        sys.exit(1)

if __name__ == "__main__":
    main()
