#!/usr/bin/env python3
from src.core.settings import settings
"""
Monitor PPI and other economic news releases and send market impact to Telegram
"""

import os
import time
import requests
from datetime import datetime, timezone
import json

# Telegram credentials - from environment variables
TELEGRAM_TOKEN = REDACTED
TELEGRAM_CHAT_ID = settings.telegram_chat_id

# OANDA credentials - from environment variables
OANDA_API_KEY = REDACTED
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT_ID", "101-004-30719775-001")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing' if OANDA_ENV == "practice" else f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing"

# Fail-closed: require critical env vars
if not TELEGRAM_TOKEN:
    REDACTED ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
if not OANDA_API_KEY:
    REDACTED ValueError("OANDA_API_KEY environment variable is required")

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

def monitor_ppi():
    """Monitor for PPI release at 13:30 BST"""
    print("🔍 Monitoring PPI release at 13:30 BST...")
    
    # Get prices before PPI (at 13:29)
    now = datetime.now()
    
    # Wait until 13:29
    target_time = now.replace(hour=13, minute=29, second=0, microsecond=0)
    if now < target_time:
        wait_seconds = (target_time - now).total_seconds()
        print(f"⏰ Waiting {wait_seconds:.0f} seconds until 13:29 to capture pre-PPI prices...")
        time.sleep(wait_seconds)
    
    # Capture pre-PPI prices
    print("📊 Capturing pre-PPI prices...")
    pre_prices = get_live_prices()
    
    if pre_prices:
        message = f"""🔔 PPI DATA INCOMING - PRE-RELEASE SNAPSHOT

⏰ Time: 13:29 BST (1 minute before PPI)

📊 PRICES BEFORE PPI:
🥇 Gold: ${pre_prices['XAU_USD']['mid']:.2f}
💷 GBP/USD: {pre_prices['GBP_USD']['mid']:.5f}
💶 EUR/USD: {pre_prices['EUR_USD']['mid']:.5f}
🇯🇵 USD/JPY: {pre_prices['USD_JPY']['mid']:.3f}

⏰ PPI RELEASES IN 60 SECONDS!
Monitoring market reaction...
"""
        send_telegram(message)
    
    # Wait until 13:30 (PPI release)
    time.sleep(60)
    
    # Wait 30 seconds after release for data to process
    print("⏰ PPI released! Waiting 30 seconds for market reaction...")
    time.sleep(30)
    
    # Capture post-PPI prices
    print("📊 Capturing post-PPI prices...")
    post_prices = get_live_prices()
    
    if pre_prices and post_prices:
        # Calculate changes
        gold_change = post_prices['XAU_USD']['mid'] - pre_prices['XAU_USD']['mid']
        gbp_change = post_prices['GBP_USD']['mid'] - pre_prices['GBP_USD']['mid']
        eur_change = post_prices['EUR_USD']['mid'] - pre_prices['EUR_USD']['mid']
        jpy_change = post_prices['USD_JPY']['mid'] - pre_prices['USD_JPY']['mid']
        
        # Determine market direction
        usd_direction = "STRONG 📈" if jpy_change > 0.1 else "WEAK 📉" if jpy_change < -0.1 else "NEUTRAL ➡️"
        
        message = f"""🔥 PPI DATA - MARKET REACTION

⏰ Time: 13:30:30 BST (30 sec after release)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 USD REACTION: {usd_direction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PRICE CHANGES (30 seconds):

🥇 Gold:
   Before: ${pre_prices['XAU_USD']['mid']:.2f}
   After: ${post_prices['XAU_USD']['mid']:.2f}
   Change: ${gold_change:+.2f} ({gold_change:+.2f} pips)
   {'🚀 SPIKE UP!' if gold_change > 5 else '⚠️ DROP!' if gold_change < -5 else '➡️ Stable'}

💷 GBP/USD:
   Before: {pre_prices['GBP_USD']['mid']:.5f}
   After: {post_prices['GBP_USD']['mid']:.5f}
   Change: {gbp_change*10000:+.1f} pips
   {'🚀 SPIKE UP!' if gbp_change*10000 > 20 else '⚠️ DROP!' if gbp_change*10000 < -20 else '➡️ Stable'}

💶 EUR/USD:
   Before: {pre_prices['EUR_USD']['mid']:.5f}
   After: {post_prices['EUR_USD']['mid']:.5f}
   Change: {eur_change*10000:+.1f} pips
   {'🚀 SPIKE UP!' if eur_change*10000 > 20 else '⚠️ DROP!' if eur_change*10000 < -20 else '➡️ Stable'}

🇯🇵 USD/JPY:
   Before: {pre_prices['USD_JPY']['mid']:.3f}
   After: {post_prices['USD_JPY']['mid']:.3f}
   Change: {jpy_change*100:+.1f} pips
   {'🚀 SPIKE UP!' if jpy_change*100 > 15 else '⚠️ DROP!' if jpy_change*100 < -15 else '➡️ Stable'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TRADING DIRECTION:

"""
        
        # Add trading recommendations
        if gold_change < -5:
            message += "🥇 GOLD: BUY THE DIP ⬆️\n   Entry: Current\n   Target: Pre-PPI level + $5\n\n"
        elif gold_change > 5:
            message += "🥇 GOLD: MOMENTUM LONG ⬆️\n   Entry: Pullback\n   Target: +$10-15 more\n\n"
        
        if gbp_change*10000 < -20:
            message += "💷 GBP: BUY SUPPORT ⬆️\n   Entry: Current\n   Target: Pre-PPI level\n\n"
        elif gbp_change*10000 > 20:
            message += "💷 GBP: RIDE MOMENTUM ⬆️\n   Entry: Pullback\n   Target: +30 pips\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⏰ Monitoring continues...\nWill update in 5 minutes with trend confirmation."
        
        send_telegram(message)
    
    # Wait 5 minutes and send trend update
    print("⏰ Waiting 5 minutes for trend confirmation...")
    time.sleep(300)
    
    # Get 5-minute post prices
    final_prices = get_live_prices()
    
    if pre_prices and final_prices:
        gold_final = final_prices['XAU_USD']['mid'] - pre_prices['XAU_USD']['mid']
        gbp_final = final_prices['GBP_USD']['mid'] - pre_prices['GBP_USD']['mid']
        
        message = f"""📊 PPI IMPACT - 5 MINUTE TREND

⏰ Time: 13:35 BST (5 min after PPI)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 CONFIRMED MOVES:

🥇 Gold: {gold_final:+.2f} pips from pre-PPI
   Current: ${final_prices['XAU_USD']['mid']:.2f}
   Trend: {'BULLISH 🚀' if gold_final > 0 else 'BEARISH 📉'}

💷 GBP/USD: {gbp_final*10000:+.1f} pips from pre-PPI
   Current: {final_prices['GBP_USD']['mid']:.5f}
   Trend: {'BULLISH 🚀' if gbp_final > 0 else 'BEARISH 📉'}

💶 EUR/USD: {(final_prices['EUR_USD']['mid'] - pre_prices['EUR_USD']['mid'])*10000:+.1f} pips
   Current: {final_prices['EUR_USD']['mid']:.5f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SYSTEM SHOULD BE TRADING NOW

Watch for signals in next 30 minutes!
Best trading: 13:45-15:00 ⏰
"""
        send_telegram(message)
    
    print("✅ PPI monitoring complete!")

def send_cpi_reminder():
    """Send reminder about tomorrow's CPI"""
    message = """📅 TOMORROW'S MEGA EVENT REMINDER

🔥 WEDNESDAY 13:30 BST - U.S. CPI 🔥

THE BIGGEST EVENT OF THE WEEK!

Expected Impact:
• Markets will move 150-200 pips
• Gold could swing $20-30
• EXTREME volatility

Trading Plan:
⏰ 08:00-13:00: Normal trading
⚠️ 13:00-13:30: CLOSE all positions
⏸️ 13:30-13:45: WAIT for CPI data
🚀 13:45-16:00: MASSIVE opportunities

Profit Potential: $8,000-15,000! 💰

I'll monitor and send updates:
• Pre-CPI snapshot (13:29)
• Immediate reaction (13:31)
• 5-min trend (13:35)
• Trading signals (13:45+)

Get ready for MEGA DAY tomorrow! 🚀
"""
    send_telegram(message)

if __name__ == "__main__":
    # Start monitoring
    send_telegram("🔍 News monitoring activated! Will send PPI results and market impact shortly...")
    
    # Monitor PPI
    monitor_ppi()
    
    # Send CPI reminder for tomorrow
    time.sleep(60)
    send_cpi_reminder()
    
    print("✅ Monitoring complete!")




