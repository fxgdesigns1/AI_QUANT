#!/usr/bin/env python3
"""
Send Telegram update about optimization progress
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.telegram_notifier import TelegramNotifier

def send_update():
    notifier = TelegramNotifier(
        bot_token="${TELEGRAM_TOKEN}",
        chat_id="${TELEGRAM_CHAT_ID}"
    )
    
    message = """
🔬 **COMPREHENSIVE STRATEGY OPTIMIZATION - IN PROGRESS**

I'm running Monte Carlo optimization on all 10 strategies individually to find their optimal parameters based on the past week's real market data.

**Current Phase: Priority Strategies**
⚙️ Trump DNA (Momentum Trading) - Testing 2,187 combinations
⚙️ 75% WR Champion - Testing 128 combinations  
⚙️ Gold Scalping - Testing 128 combinations

**Methodology:**
✅ Using real OANDA market data (5 days lookback)
✅ Testing 7 key parameters per strategy
✅ Measuring: Win rate, P&L, Trade frequency
✅ Each strategy gets UNIQUE parameters (no generic values)

**Data Being Used:**
✅ Historical M5 candles from OANDA
✅ Economic indicators already cached (Fed, CPI, GDP)
✅ All instruments per strategy

**Expected Timeline:**
⏱️ Priority strategies: ~30-45 minutes
⏱️ All 10 strategies: ~90-120 minutes total

**Next Steps After Optimization:**
1️⃣ Document best parameters for each
2️⃣ Verify against past week performance
3️⃣ Implement in strategy files
4️⃣ Deploy to Google Cloud
5️⃣ Monitor live signals

I'll update you when optimization completes with detailed results for each strategy!

📊 **Status:** RUNNING - Started 08:47 AM London Time
"""
    
    notifier.send_alert(
        title="System Optimization In Progress",
        message=message,
        priority="normal"
    )
    print("✅ Telegram update sent!")

if __name__ == '__main__':
    send_update()




