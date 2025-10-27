#!/usr/bin/env python3
"""
START SEMI-AUTOMATIC TRADING ALERTS
==================================

Quick start script for semi-automatic trading alerts
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def start_semi_auto_alerts():
    """Start the semi-automatic trading alert system"""
    
    print("🤖 STARTING SEMI-AUTOMATIC TRADING ALERTS")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%H:%M:%S')} London")
    print()
    
    # Set environment variables
    os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
    os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
    
    print("✅ Environment variables set")
    print("✅ Telegram credentials configured")
    print("✅ Semi-automatic account: 101-004-30719775-001")
    print()
    
    print("🚀 Starting alert system...")
    print("📱 You will receive alerts for:")
    print("   • Trading opportunities (every 5 minutes)")
    print("   • Account updates (every 30 minutes)")
    print("   • Market conditions (every hour)")
    print()
    
    try:
        # Start the alert system
        subprocess.run([
            sys.executable, 
            '/Users/mac/quant_system_clean/google-cloud-trading-system/semi_auto_telegram_alerts.py'
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Alert system stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting alert system: {e}")

if __name__ == "__main__":
    start_semi_auto_alerts()

