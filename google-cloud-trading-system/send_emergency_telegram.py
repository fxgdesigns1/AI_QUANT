#!/usr/bin/env python3
"""Send immediate Telegram update about Account 011"""
import requests

# Your Telegram credentials (from memory)
TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"

message = """🚨 <b>URGENT: ACCOUNT 011 EMERGENCY</b>

⚠️ <b>PROBLEM IDENTIFIED & FIXED:</b>

❌ Account 011 was SELLING USD/CAD
❌ But USD/CAD was RISING (uptrend)
❌ 25 trades fighting the trend
❌ Loss: -$3,690 

✅ <b>ACTIONS TAKEN:</b>

✅ ALL 25 losing trades CLOSED
✅ Account 011 DISABLED  
✅ USD_CAD removed from trading
✅ Loss stopped - no more bleeding

📊 <b>WHAT WENT WRONG:</b>

• Momentum strategy had BROKEN trend detection
• Was selling when it should be buying
• Overtrading (25 positions!)
• No loss limits working

🔧 <b>FIXES IMPLEMENTED:</b>

• Account disabled until strategy fixed
• Profit protection active on other accounts
• Daily loss limits added (-$300 max)
• Weekly targets set (+$750/week)
• Telegram daily reports starting tonight

✅ <b>CURRENT STATUS:</b>

Account 006: Active with protection ✅
Account 007: Active with protection ✅
Account 008: Active with protection ✅
Account 010: Active with protection ✅
Account 011: DISABLED (being fixed)

💰 <b>RECOVERY PLAN:</b>

• Fix momentum strategy logic
• Test thoroughly before re-enabling
• Target: +$750 this week from 4 active accounts
• Goal: Recover -$3,690 loss over next month

📱 <b>YOU'LL NOW GET:</b>

• Daily results: 9:30 PM London every night
• Weekly summary: Sundays
• Real-time loss alerts
• News blocking notifications
• Full transparency

I'm fixing this and you'll see results in Telegram starting tonight at 9:30 PM!

#EmergencyFixed #Account011 #Accountability
"""

try:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data, timeout=10)
    
    if response.status_code == 200:
        print("✅ Emergency Telegram alert SENT successfully!")
        print(f"Chat ID: {CHAT_ID}")
    else:
        print(f"❌ Telegram send failed: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"❌ Error: {e}")



