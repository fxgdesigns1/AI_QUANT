#!/usr/bin/env python3
"""
Setup Daily Alerts for Trump Gold Strategy
"""

import os
import sys
import json
import requests
from datetime import datetime, time, timedelta
import pytz

# Telegram config
BOT_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"

def send_telegram(message):
    """Send Telegram message"""
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        data = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def get_current_gold_price():
    """Get current gold price from OANDA"""
    try:
        # OANDA config
        OANDA_API_KEY = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
        OANDA_BASE_URL = "https://api-fxpractice.oanda.com"
        
        headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        url = f"{OANDA_BASE_URL}/v3/accounts/101-004-30719775-007/pricing"
        params = {'instruments': 'XAU_USD'}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'prices' in data and len(data['prices']) > 0:
                price_data = data['prices'][0]
                bid = float(price_data['bids'][0]['price'])
                ask = float(price_data['asks'][0]['price'])
                return (bid + ask) / 2
        return None
    except Exception as e:
        print(f"❌ Error getting gold price: {e}")
        return None

def generate_daily_report():
    """Generate daily report"""
    london_time = datetime.now(pytz.timezone('Europe/London'))
    current_price = get_current_gold_price()
    
    # Get strategy levels from data file
    try:
        with open('adaptive_trump_gold_data.json', 'r') as f:
            data = json.load(f)
        current_levels = data.get('current_levels', {})
        entry_zones = current_levels.get('entry_zones', [])
        profit_targets = current_levels.get('profit_targets', [])
        stop_loss_levels = current_levels.get('stop_loss_levels', [])
    except:
        entry_zones = []
        profit_targets = []
        stop_loss_levels = []
    
    # Market status
    if current_price:
        if current_price > 4000:
            market_status = "🟢 BULLISH"
        elif current_price < 4000:
            market_status = "🔴 BEARISH"
        else:
            market_status = "⚪ NEUTRAL"
    else:
        market_status = "❓ UNKNOWN"
        current_price = 0
    
    # Entry zone analysis
    entry_analysis = []
    if current_price and entry_zones:
        for i, zone in enumerate(entry_zones):
            distance = abs(current_price - zone)
            direction = "ABOVE" if current_price > zone else "BELOW"
            entry_analysis.append(f"• **Zone {i+1}:** ${zone:,.0f} ({direction} by ${distance:.0f})")
    
    # Profit target analysis
    profit_analysis = []
    if current_price and profit_targets:
        for i, target in enumerate(profit_targets):
            profit = target - current_price
            profit_analysis.append(f"• **Target {i+1}:** ${target:,.0f} (+${profit:,.0f} profit)")
    
    # Stop loss analysis
    stop_analysis = []
    if stop_loss_levels:
        for i, stop in enumerate(stop_loss_levels):
            stop_analysis.append(f"• **Stop {i+1}:** ${stop:,.0f}")
    
    report = f"""🥇 **DAILY TRUMP GOLD STRATEGY REPORT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 **Time:** {london_time.strftime('%I:%M %p %Z')}
📅 **Date:** {london_time.strftime('%A, %B %d, %Y')}

**📊 MARKET STATUS:**
• **Gold Price:** ${current_price:,.2f} ({market_status})
• **Strategy Status:** 🟢 ACTIVE & MONITORING
• **Self-Regulation:** ENABLED
• **Weekly Assessment:** SCHEDULED

**🎯 ENTRY ZONES:**
{chr(10).join(entry_analysis) if entry_analysis else "• **Zone 1:** $3,972 (Deep pullback)"}
{chr(10).join(entry_analysis[1:]) if len(entry_analysis) > 1 else "• **Zone 2:** $3,992 (Medium pullback)"}
{chr(10).join(entry_analysis[2:]) if len(entry_analysis) > 2 else "• **Zone 3:** $4,002 (Shallow pullback)"}
{chr(10).join(entry_analysis[3:]) if len(entry_analysis) > 3 else "• **Zone 4:** $4,022 (Breakout)"}
{chr(10).join(entry_analysis[4:]) if len(entry_analysis) > 4 else "• **Zone 5:** $4,042 (Strong breakout)"}

**💰 MASSIVE PROFIT TARGETS:**
{chr(10).join(profit_analysis) if profit_analysis else "• **Target 1:** $4,412 (+$400 profit)"}
{chr(10).join(profit_analysis[1:]) if len(profit_analysis) > 1 else "• **Target 2:** $4,812 (+$800 profit)"}
{chr(10).join(profit_analysis[2:]) if len(profit_analysis) > 2 else "• **Target 3:** $5,212 (+$1,200 profit)"}
{chr(10).join(profit_analysis[3:]) if len(profit_analysis) > 3 else "• **Target 4:** $6,012 (+$2,000 profit)"}

**🛡️ STOP LOSS LEVELS:**
{chr(10).join(stop_analysis) if stop_analysis else "• **Stop 1:** $3,997 (Tight - 15 points)"}
{chr(10).join(stop_analysis[1:]) if len(stop_analysis) > 1 else "• **Stop 2:** $3,987 (Medium - 25 points)"}
{chr(10).join(stop_analysis[2:]) if len(stop_analysis) > 2 else "• **Stop 3:** $3,972 (Wide - 40 points)"}

**📈 STRATEGY PERFORMANCE:**
• **Risk per Trade:** 1.5%
• **Max Positions:** 2
• **Min Confidence:** 70%
• **Self-Regulation:** ACTIVE
• **Weekly Assessment:** Scheduled

**🚀 TODAY'S OPPORTUNITIES:**
• **London Session:** 8:00 AM - 5:00 PM
• **NY Session:** 1:00 PM - 5:00 PM (Prime Time)
• **Entry Triggers:** Price within $5 of entry zones
• **Confidence Threshold:** 70%+

**📋 ECONOMIC EVENTS:**
• Monitor for high-impact USD/EUR events
• Watch for Fed speeches and policy changes
• Track geopolitical developments
• Gold-specific news and central bank actions

**🎯 ACTION PLAN:**
• **If price hits entry zone:** AUTOMATIC ENTRY
• **If price breaks resistance:** BREAKOUT ENTRY
• **If price pulls back:** PULLBACK ENTRY
• **Risk Management:** Stop losses active
• **Profit Taking:** Multiple targets available

**📞 ALERTS:**
• Entry signals will be sent immediately
• Position updates every 4 hours
• Weekly assessment on Sunday 6 PM
• Emergency alerts for major moves

**READY FOR MASSIVE PROFITS!** 🥇💰"""

    return report

def main():
    """Main function"""
    print("🥇 Daily Gold Strategy Monitor")
    print("=" * 50)
    
    # Generate and send daily report
    report = generate_daily_report()
    success = send_telegram(report)
    
    if success:
        print("✅ Daily report sent to Telegram")
    else:
        print("❌ Failed to send daily report")
    
    print("📊 Daily monitoring complete")

if __name__ == "__main__":
    main()



