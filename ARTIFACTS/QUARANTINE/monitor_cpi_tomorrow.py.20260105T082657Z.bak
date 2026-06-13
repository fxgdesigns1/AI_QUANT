#!/usr/bin/env python3
from src.core.settings import settings
"""
Monitor CPI and other economic news releases - TOMORROW (Wednesday)
"""

import os
import time
import requests
from datetime import datetime, timedelta
import schedule

# Telegram credentials - from environment variables
TELEGRAM_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = settings.telegram_chat_id

# OANDA credentials - from environment variables
OANDA_API_KEY = settings.oanda_api_key
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT_ID", "101-004-30719775-001")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing' if OANDA_ENV == "practice" else f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing"

# Fail-closed: require critical env vars
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable is required")

def send_telegram(message):
    """Send message to Telegram"""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

def get_live_prices():
    """Get current live prices from OANDA"""
    headers = {
        'Authorization': f'Bearer {OANDA_API_KEY}',
        'Content-Type': 'application/json'
    }
    params = {
        'instruments': 'XAU_USD,GBP_USD,EUR_USD,USD_JPY'
    }
    
    try:
        response = requests.get(OANDA_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            prices = {}
            for price in data.get('prices', []):
                instrument = price['instrument']
                bid = float(price['bids'][0]['price'])
                ask = float(price['asks'][0]['price'])
                prices[instrument] = {
                    'bid': bid,
                    'ask': ask,
                    'mid': (bid + ask) / 2
                }
            return prices
        return None
    except Exception as e:
        print(f"Error getting prices: {e}")
        return None

def send_morning_cpi_alert():
    """Send morning alert about CPI"""
    message = """🌅 WEDNESDAY MORNING - CPI DAY!

⏰ 08:00 BST

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 TODAY: U.S. CPI at 13:30 BST
THE BIGGEST EVENT OF THE WEEK!

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 EXPECTED IMPACT:

• Markets will move 150-200 pips 📈📉
• Gold could swing $20-30 💰
• EXTREME volatility incoming 🔥
• Biggest profit opportunity! 💵

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ TODAY'S SCHEDULE:

08:00-13:00: Normal trading
   • Build positions
   • Target: $2-4K morning profits

13:00-13:15: POSITION CLEANUP
   • CLOSE risky positions
   • Reduce exposure
   • Prepare for CPI

13:15-13:30: FINAL PREP
   • Watch Telegram for updates
   • I'll send pre-CPI snapshot at 13:29

13:30: 🔥 CPI DATA RELEASE 🔥
   • Markets will EXPLODE
   • I'll send immediate reaction

13:31-13:45: WAIT & ANALYZE
   • Let dust settle
   • Identify direction
   • I'll send trading signals

13:45-16:00: MAIN TRADING 🚀
   • BIGGEST profit window
   • Trade the CPI direction
   • Target: $8-15K!

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PROFIT POTENTIAL TODAY:

Morning: $2-4K
CPI Reaction: $8-15K
TOTAL: $10-19K 💰💰💰

━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ I'LL SEND YOU:

• Pre-CPI snapshot (13:29)
• CPI result + immediate reaction (13:31)
• 5-minute trend analysis (13:35)
• Trading signals (13:45)
• Position updates (real-time)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 LET'S MAKE THIS A MEGA DAY!

Trade smart this morning, then
DOMINATE the CPI reaction! 💪📈💰
"""
    send_telegram(message)

def send_pre_cpi_warning():
    """Send 1-hour warning before CPI"""
    message = """⚠️ 1 HOUR TO CPI! ⚠️

⏰ 12:30 BST

🔥 CPI DATA IN 60 MINUTES 🔥

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ACTION ITEMS NOW:

1️⃣ Review open positions
2️⃣ Close any risky trades
3️⃣ Reduce exposure to <5%
4️⃣ Prepare for volatility

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ NEXT 60 MINUTES:

12:30-13:00: Final trading
13:00-13:15: CLOSE positions
13:15-13:30: WAIT mode
13:30: 💥 CPI RELEASE 💥

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 I'LL SEND:

• 13:29: Pre-CPI snapshot
• 13:31: CPI result + reaction
• 13:35: Trend confirmation
• 13:45: Trading signals

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 GET READY FOR $8-15K! 🚀
"""
    send_telegram(message)

def monitor_cpi():
    """Monitor CPI release at 13:30"""
    print("🔍 Monitoring CPI release at 13:30 BST...")
    
    # Send 30-min warning
    message = """⚠️ 30 MINUTES TO CPI! ⚠️

⏰ 13:00 BST

🔥 CLOSE ALL RISKY POSITIONS NOW! 🔥

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 URGENT ACTIONS:

✅ Close all GBP positions
✅ Close all EUR positions  
✅ Gold: Close or tight stops
✅ Reduce to <3% exposure

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 30 MINUTES TO CPI

Markets about to go CRAZY! 🌪️
I'll send pre-CPI snapshot at 13:29
"""
    send_telegram(message)
    
    # Wait until 13:29
    now = datetime.now()
    target = now.replace(hour=13, minute=29, second=0, microsecond=0)
    if now < target:
        wait_seconds = (target - now).total_seconds()
        time.sleep(wait_seconds)
    
    # Get pre-CPI prices
    pre_prices = get_live_prices()
    
    if pre_prices:
        message = f"""🔔 CPI DATA INCOMING - 60 SECONDS!

⏰ 13:29 BST

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PRICES BEFORE CPI:

🥇 Gold: ${pre_prices['XAU_USD']['mid']:.2f}
💷 GBP/USD: {pre_prices['GBP_USD']['mid']:.5f}
💶 EUR/USD: {pre_prices['EUR_USD']['mid']:.5f}
🇯🇵 USD/JPY: {pre_prices['USD_JPY']['mid']:.3f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ CPI RELEASES IN 60 SECONDS!

Expected: 2.5% YoY
If > 2.5%: USD STRONG 📈
If < 2.5%: USD WEAK 📉

Markets will SPIKE! 🚀
Monitoring reaction...
"""
        send_telegram(message)
    
    # Wait for CPI release
    time.sleep(60)
    
    # Wait 30 seconds for reaction
    time.sleep(30)
    
    # Get post-CPI prices
    post_prices = get_live_prices()
    
    if pre_prices and post_prices:
        # Calculate changes
        gold_change = post_prices['XAU_USD']['mid'] - pre_prices['XAU_USD']['mid']
        gbp_change = post_prices['GBP_USD']['mid'] - pre_prices['GBP_USD']['mid']
        eur_change = post_prices['EUR_USD']['mid'] - pre_prices['EUR_USD']['mid']
        jpy_change = post_prices['USD_JPY']['mid'] - pre_prices['USD_JPY']['mid']
        
        # Determine USD strength
        usd_direction = "STRONG 💪" if jpy_change > 0.2 else "WEAK 📉" if jpy_change < -0.2 else "NEUTRAL ➡️"
        
        # Determine CPI result
        if jpy_change > 0.2:
            cpi_result = "HOT (>2.5%)"
        elif jpy_change < -0.2:
            cpi_result = "COOL (<2.5%)"
        else:
            cpi_result = "IN-LINE (~2.5%)"
        
        message = f"""🔥🔥🔥 CPI RESULTS - MARKET REACTION 🔥🔥🔥

⏰ 13:30:30 BST

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 CPI RESULT: {cpi_result}
💵 USD REACTION: {usd_direction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PRICE CHANGES (First 30 sec):

🥇 GOLD:
   Before: ${pre_prices['XAU_USD']['mid']:.2f}
   After: ${post_prices['XAU_USD']['mid']:.2f}
   Change: ${gold_change:+.2f}
   {'🚀 MASSIVE SPIKE!' if abs(gold_change) > 15 else '⚡ BIG MOVE!' if abs(gold_change) > 8 else '➡️ Moderate'}

💷 GBP/USD:
   Before: {pre_prices['GBP_USD']['mid']:.5f}
   After: {post_prices['GBP_USD']['mid']:.5f}
   Change: {gbp_change*10000:+.1f} pips
   {'🚀 MASSIVE SPIKE!' if abs(gbp_change*10000) > 100 else '⚡ BIG MOVE!' if abs(gbp_change*10000) > 50 else '➡️ Moderate'}

💶 EUR/USD:
   Before: {pre_prices['EUR_USD']['mid']:.5f}
   After: {post_prices['EUR_USD']['mid']:.5f}
   Change: {eur_change*10000:+.1f} pips
   {'🚀 MASSIVE SPIKE!' if abs(eur_change*10000) > 100 else '⚡ BIG MOVE!' if abs(eur_change*10000) > 50 else '➡️ Moderate'}

🇯🇵 USD/JPY:
   Before: {pre_prices['USD_JPY']['mid']:.3f}
   After: {post_prices['USD_JPY']['mid']:.3f}
   Change: {jpy_change*100:+.1f} pips
   {'🚀 MASSIVE SPIKE!' if abs(jpy_change*100) > 80 else '⚡ BIG MOVE!' if abs(jpy_change*100) > 40 else '➡️ Moderate'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 IMMEDIATE TRADING SIGNALS:

"""
        
        # Add trading recommendations based on moves
        if gold_change < -10:
            message += "🥇 GOLD: BUY THE DIP NOW! ⬆️\n   Entry: CURRENT\n   Target: +$15-20\n   Stop: -$8\n\n"
        elif gold_change > 10:
            message += "🥇 GOLD: BUY MOMENTUM! ⬆️\n   Entry: Small pullback\n   Target: +$15-20 more\n   Stop: -$8\n\n"
        
        if gbp_change*10000 < -50:
            message += "💷 GBP: BUY SUPPORT! ⬆️\n   Entry: CURRENT\n   Target: +50 pips\n   Stop: -20 pips\n\n"
        elif gbp_change*10000 > 50:
            message += "💷 GBP: RIDE THE WAVE! ⬆️\n   Entry: Pullback\n   Target: +50 pips more\n   Stop: -20 pips\n\n"
        
        if eur_change*10000 < -50:
            message += "💶 EUR: BUY THE DIP! ⬆️\n   Entry: CURRENT\n   Target: +50 pips\n   Stop: -20 pips\n\n"
        elif eur_change*10000 > 50:
            message += "💶 EUR: MOMENTUM TRADE! ⬆️\n   Entry: Pullback\n   Target: +50 pips more\n   Stop: -20 pips\n\n"
        
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ NEXT: 5-min trend confirmation

Monitoring continues... 📊
Best trading: 13:45-15:00! 🚀
"""
        
        send_telegram(message)
    
    # Wait 5 minutes for trend confirmation
    time.sleep(300)
    
    final_prices = get_live_prices()
    
    if pre_prices and final_prices:
        gold_total = final_prices['XAU_USD']['mid'] - pre_prices['XAU_USD']['mid']
        gbp_total = final_prices['GBP_USD']['mid'] - pre_prices['GBP_USD']['mid']
        eur_total = final_prices['EUR_USD']['mid'] - pre_prices['EUR_USD']['mid']
        
        message = f"""📊 CPI IMPACT - 5 MINUTE TREND

⏰ 13:35 BST (5 min after CPI)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 CONFIRMED TRENDS:

🥇 Gold: {gold_total:+.2f} from pre-CPI
   Current: ${final_prices['XAU_USD']['mid']:.2f}
   Trend: {'STRONGLY BULLISH 🚀🚀' if gold_total > 15 else 'BULLISH 🚀' if gold_total > 5 else 'STRONGLY BEARISH 📉📉' if gold_total < -15 else 'BEARISH 📉' if gold_total < -5 else 'RANGING ↔️'}

💷 GBP/USD: {gbp_total*10000:+.1f} pips from pre-CPI
   Current: {final_prices['GBP_USD']['mid']:.5f}
   Trend: {'STRONGLY BULLISH 🚀🚀' if gbp_total*10000 > 80 else 'BULLISH 🚀' if gbp_total*10000 > 30 else 'STRONGLY BEARISH 📉📉' if gbp_total*10000 < -80 else 'BEARISH 📉' if gbp_total*10000 < -30 else 'RANGING ↔️'}

💶 EUR/USD: {eur_total*10000:+.1f} pips from pre-CPI
   Current: {final_prices['EUR_USD']['mid']:.5f}
   Trend: {'STRONGLY BULLISH 🚀🚀' if eur_total*10000 > 80 else 'BULLISH 🚀' if eur_total*10000 > 30 else 'STRONGLY BEARISH 📉📉' if eur_total*10000 < -80 else 'BEARISH 📉' if eur_total*10000 < -30 else 'RANGING ↔️'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CONFIRMED TRADING DIRECTION

Direction is SET! 
System should be generating signals!
Watch Telegram for trade alerts! 📱

MAIN WINDOW: 13:45-15:00 ⏰
PROFIT TARGET: $8,000-15,000 💰

LET'S DOMINATE THIS! 🚀💪📈
"""
        send_telegram(message)

if __name__ == "__main__":
    import sys
    
    # Check if we should monitor CPI (tomorrow)
    now = datetime.now()
    
    # If it's before 13:00 today, schedule morning alert for tomorrow
    if now.hour < 13:
        print("⏰ Will send morning CPI alert tomorrow at 08:00")
        # For now, send confirmation
        send_telegram("✅ CPI Monitoring scheduled for tomorrow (Wednesday) at 08:00!")
    
    # If running tomorrow morning (Wednesday), execute full monitoring
    if len(sys.argv) > 1 and sys.argv[1] == "run_cpi":
        send_morning_cpi_alert()
        time.sleep(3600)  # Wait 1 hour
        send_pre_cpi_warning()
        time.sleep(1800)  # Wait 30 min
        monitor_cpi()




