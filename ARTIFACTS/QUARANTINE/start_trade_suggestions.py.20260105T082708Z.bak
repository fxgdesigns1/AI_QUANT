#!/usr/bin/env python3
"""
START TRADE SUGGESTIONS DASHBOARD
=================================

Starts the trade suggestions API and dashboard
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def start_trade_suggestions():
    """Start the trade suggestions dashboard"""
    
    print("🎯 STARTING TRADE SUGGESTIONS DASHBOARD")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%H:%M:%S')} London")
    print()
    
    # Set environment variables
    os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
    os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
    
    print("✅ Environment variables set")
    print("✅ OANDA API configured")
    print("✅ Telegram credentials configured")
    print()
    
    print("🚀 Starting trade suggestions dashboard...")
    print("📊 Features:")
    print("   • AI-powered trade suggestions")
    print("   • Real-time market analysis")
    print("   • One-click trade approval")
    print("   • Direct trade execution")
    print("   • WebSocket real-time updates")
    print()
    
    print("🌐 Dashboard will be available at:")
    print("   • Trade Suggestions: http://localhost:8082/dashboard/trade-suggestions")
    print("   • API Endpoints: http://localhost:8082/api/")
    print()
    
    try:
        # Start the trade suggestions API
        subprocess.run([
            sys.executable, 
            '/Users/mac/quant_system_clean/dashboard/trade_suggestions_api.py'
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Trade suggestions dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting trade suggestions dashboard: {e}")

if __name__ == "__main__":
    start_trade_suggestions()

