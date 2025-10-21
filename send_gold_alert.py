#!/usr/bin/env python3
"""
Send urgent Telegram alert about gold position
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add google-cloud-trading-system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
load_dotenv(env_path)

from src.core.telegram_notifier import get_telegram_notifier

def send_gold_alert():
    """Send focused alert about gold position"""
    
    notifier = get_telegram_notifier()
    
    if not notifier.enabled:
        print("❌ Telegram notifier not enabled")
        return
    
    message = f"""
🥇 <b>GOLD POSITION ALERT</b>

💰 <b>MAJOR WIN IN PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━━━━

<b>XAU_USD LONG Position</b>
• Account: Gold Trump Week (001)
• Entry: $3,948.72
• Current: $3,982.71
• Profit: +$7,565.39
• Units: 300
• Gain: +$25.18 per ounce

📊 <b>Performance</b>
• ROI: +19% on this trade
• Distance to target: $17.29
• Stop Loss: $3,941.49 (protected)

💡 <b>RECOMMENDATION</b>
━━━━━━━━━━━━━━━━━━━━━━━

Consider taking PARTIAL PROFITS:

1️⃣ Close 150 units (50%) NOW
   → Lock in ~$6,188 profit

2️⃣ Keep 150 units running
   → Target: $4,000-$4,050
   → Move stop to $3,970 (breakeven+)

<b>Why partial close?</b>
✅ Secures majority of gain
✅ Eliminates downside risk  
✅ Keeps you in the trend
✅ Professional risk management

⚠️ Gold at strong level, taking profit is wise!

#GoldAlert #TakeProfit #RiskManagement
"""
    
    success = notifier.send_message(message)
    
    if success:
        print("✅ Gold alert sent successfully")
    else:
        print("❌ Failed to send gold alert")

if __name__ == "__main__":
    send_gold_alert()












