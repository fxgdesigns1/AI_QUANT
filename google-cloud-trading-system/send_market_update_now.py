#!/usr/bin/env python3
"""
Send market update immediately to Telegram
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from start_daily_telegram_updates import morning_briefing, send_telegram
from datetime import datetime

if __name__ == "__main__":
    print("🚀 Sending market update NOW...")
    print("="*60)
    
    # Call morning briefing function which will get fresh data and send
    try:
        morning_briefing()
        print("\n✅ Market update sent successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Send error notification
        error_msg = f"""⚠️ <b>Market Update Error</b>

Failed to send market update: {str(e)}

Time: {datetime.now().strftime('%I:%M %p')}
"""
        send_telegram(error_msg)

