#!/usr/bin/env python3
"""
Hourly Gold Monitor - Checks for entry opportunities every hour
"""

import os
import sys
import json
import requests
from datetime import datetime, time, timedelta
import pytz

# Telegram config
BOT_TOKEN = "${TELEGRAM_TOKEN}"
CHAT_ID = "${TELEGRAM_CHAT_ID}"

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
        OANDA_API_KEY = "${OANDA_API_KEY}"
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

def check_entry_opportunities():
    """Check for immediate entry opportunities"""
    try:
        current_price = get_current_gold_price()
        if not current_price:
            print("❌ Could not get current gold price")
            return
        
        # Load strategy levels
        try:
            with open('adaptive_trump_gold_data.json', 'r') as f:
                data = json.load(f)
            current_levels = data.get('current_levels', {})
            entry_zones = current_levels.get('entry_zones', [])
        except:
            print("❌ Could not load strategy data")
            return
        
        if not entry_zones:
            print("❌ No entry zones configured")
            return
        
        london_time = datetime.now(pytz.timezone('Europe/London'))
        
        # Check if price is near any entry zone
        opportunities = []
        for i, zone in enumerate(entry_zones):
            distance = abs(current_price - zone)
            if distance <= 10.0:  # Within $10 of entry zone
                direction = "ABOVE" if current_price > zone else "BELOW"
                opportunities.append({
                    'zone': zone,
                    'distance': distance,
                    'direction': direction,
                    'index': i + 1
                })
        
        if opportunities:
            # Send alert for opportunities
            message = f"""🚨 **ENTRY OPPORTUNITY DETECTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 **Time:** {london_time.strftime('%I:%M %p %Z')}
🥇 **Gold Price:** ${current_price:,.2f}

**🎯 ENTRY ZONES NEARBY:**
"""
            
            for opp in opportunities:
                message += f"• **Zone {opp['index']}:** ${opp['zone']:,.0f} ({opp['direction']} by ${opp['distance']:.1f})\n"
            
            message += f"""
**🚀 STRATEGY STATUS:**
• **Confidence:** HIGH (within $10 of zones)
• **Risk:** 1.5% per trade
• **Max Positions:** 2
• **Profit Targets:** $400-$2,000

**⚡ AUTOMATIC ENTRY ACTIVE**
The system will attempt to enter when conditions are met!"""
            
            success = send_telegram(message)
            if success:
                print(f"✅ Entry opportunity alert sent for {len(opportunities)} zones")
            else:
                print("❌ Failed to send entry opportunity alert")
        else:
            print(f"📊 No entry opportunities (price: ${current_price:,.2f})")
            
    except Exception as e:
        print(f"❌ Error checking entry opportunities: {e}")

def main():
    """Main function"""
    print("🥇 Hourly Gold Monitor")
    print("=" * 30)
    
    check_entry_opportunities()
    print("✅ Hourly monitoring complete")

if __name__ == "__main__":
    main()



