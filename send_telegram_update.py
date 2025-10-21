#!/usr/bin/env python3
"""
Send Telegram update with portfolio status
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

def send_update():
    """Send comprehensive portfolio update"""
    
    notifier = get_telegram_notifier()
    
    if not notifier.enabled:
        print("❌ Telegram notifier not enabled")
        return
    
    message = f"""
🔍 <b>PORTFOLIO ANALYSIS COMPLETE</b>
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

💰 <b>PORTFOLIO STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Total Balance: $486,647.49
• Unrealized P&L: +$10,013.06 ✅
• Open Trades: 70 positions
• Average Exposure: 31% (Safe)

🏆 <b>TOP PERFORMERS</b>
━━━━━━━━━━━━━━━━━━━━━━━
1. 🥇 Gold (XAU_USD): +$7,565 
2. 📈 EUR_JPY LONG: +$1,157
3. 📉 USD_CAD SHORT: +$900

📊 <b>ACCOUNT STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━
✅ Momentum (011): +$1,185 | 38 trades
✅ High Win (006): +$1,572 | 15 trades
🔴 Zero DD (007): -$161 | 7 trades
🔴 High Freq (008): -$148 | 9 trades
🟢 Gold Week (001): +$7,565 | 1 trade

⚠️ <b>RISK STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━
🟢 Portfolio Exposure: 31% (Safe)
✅ All 70 trades have protective stops
✅ Drawdown accounts have low exposure
🟡 2 accounts at 54-55% exposure

💡 <b>RECOMMENDATIONS</b>
━━━━━━━━━━━━━━━━━━━━━━━
1. Consider taking partial profits on Gold
2. Monitor GBP_USD LONG positions
3. Let USD_CAD SHORT winners run
4. System at healthy position limits

🎯 <b>MARKET CONDITIONS</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Spreads: EXCELLENT (0.6-1.6 pips)
• Trending: USD_CAD, XAU_USD
• Quality: All markets tradeable

#PortfolioUpdate #ManualCheck
"""
    
    success = notifier.send_message(message)
    
    if success:
        print("✅ Telegram update sent successfully")
    else:
        print("❌ Failed to send Telegram update")

if __name__ == "__main__":
    send_update()












