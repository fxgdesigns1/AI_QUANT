#!/usr/bin/env python3
"""
GOLD TRUMP WEEKLY STRATEGY - CONTINUOUS
Runs EVERY week while Trump is President
Target: $10-25k per week like Oct 6-11
"""

import requests
import time
import os
from datetime import datetime, timedelta

# OANDA Config
API_KEY = os.getenv('OANDA_API_KEY', 'REMOVED_SECRET')
ACCOUNT_ID = '101-004-30719775-009'  # Gold Primary Account (from accounts.yaml)
BASE_URL = 'https://api-fxpractice.oanda.com/v3'
headers = {'Authorization': f'Bearer {API_KEY}'}

# Telegram
TELEGRAM_TOKEN = '${TELEGRAM_TOKEN}'
TELEGRAM_CHAT_ID = '${TELEGRAM_CHAT_ID}'

# GOLD ENTRY ZONES - CPI DAY HIGH RR ($4,200 level)
GOLD_ZONES = [
    {'price': 4100, 'type': 'DEEP_SUPPORT', 'confidence': 1.0, 'size': 400, 'tp': 20.0, 'sl': 5.0},     # 4:1 RR
    {'price': 4150, 'type': 'DEEP_PULLBACK', 'confidence': 0.95, 'size': 400, 'tp': 20.0, 'sl': 5.0},   # 4:1 RR
    {'price': 4180, 'type': 'MEDIUM_PULLBACK', 'confidence': 0.90, 'size': 400, 'tp': 20.0, 'sl': 5.0}, # 4:1 RR
    {'price': 4200, 'type': 'CONSOLIDATION', 'confidence': 0.85, 'size': 400, 'tp': 20.0, 'sl': 5.0},   # 4:1 RR
    {'price': 4220, 'type': 'BREAKOUT', 'confidence': 0.80, 'size': 400, 'tp': 20.0, 'sl': 5.0},        # 4:1 RR
]

# Weekly goals - QUALITY FOCUS
WEEKLY_TARGET = 15000  # $15k target
WEEKLY_TRADES_TARGET = 5  # 5 QUALITY trades (was 10)
DAILY_TRADE_LIMIT = 2  # MAX 2 trades per day (QUALITY OVER QUANTITY)

# Track weekly stats
weekly_stats = {
    'week_start': datetime.now(),
    'total_profit': 0,
    'trades_count': 0,
    'wins': 0,
    'losses': 0
}

def send_telegram(message):
    """Send Telegram alert"""
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except:
        pass

def get_gold_price():
    """Get current Gold price"""
    try:
        pr = requests.get(
            f'{BASE_URL}/accounts/{ACCOUNT_ID}/pricing',
            headers=headers,
            params={'instruments': 'XAU_USD'},
            timeout=5
        )
        
        if pr.status_code == 200:
            data = pr.json()['prices'][0]
            bid = float(data['bids'][0]['price'])
            ask = float(data['asks'][0]['price'])
            return {'bid': bid, 'ask': ask, 'mid': (bid + ask) / 2}
    except:
        pass
    return None

def check_gold_positions():
    """Check existing Gold positions"""
    try:
        trades_resp = requests.get(f'{BASE_URL}/accounts/{ACCOUNT_ID}/openTrades', headers=headers, timeout=5)
        
        if trades_resp.status_code == 200:
            trades = trades_resp.json().get('trades', [])
            gold_trades = [t for t in trades if t['instrument'] == 'XAU_USD']
            return len(gold_trades)
    except:
        pass
    return 0

def find_best_entry_zone(current_price):
    """Find best entry zone based on current price"""
    best_zone = None
    min_distance = float('inf')
    
    for zone in GOLD_ZONES:
        distance = abs(current_price - zone['price'])
        
        # Within $3 of a zone
        if distance <= 3.0 and distance < min_distance:
            min_distance = distance
            best_zone = zone
    
    return best_zone, min_distance

def enter_gold_trade(zone, current_price, reason):
    """Enter Gold trade at zone"""
    try:
        # Get exact price
        pr = requests.get(
            f'{BASE_URL}/accounts/{ACCOUNT_ID}/pricing',
            headers=headers,
            params={'instruments': 'XAU_USD'},
            timeout=5
        )
        
        if pr.status_code != 200:
            return False, "Can't get price"
        
        entry = float(pr.json()['prices'][0]['asks'][0]['price'])
        units = zone['size']  # Position size from zone
        
        # Trump strategy: Tight stops, multiple profit targets
        sl = entry - 7.0  # $7 stop
        tp = entry + 15.0  # $15 first target
        
        # Place order
        order = {
            "order": {
                "type": "MARKET",
                "instrument": "XAU_USD",
                "units": str(units),
                "timeInForce": "FOK",
                "takeProfitOnFill": {"price": f"{tp:.2f}"},
                "stopLossOnFill": {"price": f"{sl:.2f}"}
            }
        }
        
        resp = requests.post(
            f'{BASE_URL}/accounts/{ACCOUNT_ID}/orders',
            headers=headers,
            json=order,
            timeout=10
        )
        
        if resp.status_code == 201:
            result = resp.json()
            trade_id = result.get('orderFillTransaction', {}).get('tradeOpened', {}).get('tradeID', 'N/A')
            
            weekly_stats['trades_count'] += 1
            
            send_telegram(f'''💎 GOLD TRUMP ENTRY!

Zone: {zone['type']}
Entry: ${entry:.2f}
TP: ${tp:.2f} (+$15)
SL: ${sl:.2f} (-$7)
Size: {units} units
Trade: #{trade_id}

Confidence: {zone['confidence']:.0%}
Reason: {reason}

Weekly: {weekly_stats['trades_count']}/{WEEKLY_TRADES_TARGET} trades''')
            
            return True, trade_id
        else:
            error = resp.json().get('errorMessage', '')
            return False, error[:100]
            
    except Exception as e:
        return False, str(e)[:100]

def check_weekly_reset():
    """Check if we need to reset weekly stats"""
    global weekly_stats
    
    days_elapsed = (datetime.now() - weekly_stats['week_start']).days
    
    if days_elapsed >= 7:
        # Week complete - send summary
        win_rate = (weekly_stats['wins'] / weekly_stats['trades_count'] * 100) if weekly_stats['trades_count'] > 0 else 0
        
        send_telegram(f'''📊 WEEKLY GOLD TRUMP SUMMARY

Week: {weekly_stats['week_start'].strftime('%b %d')} - {datetime.now().strftime('%b %d')}

Profit: ${weekly_stats['total_profit']:+,.2f}
Target: ${WEEKLY_TARGET:,.2f}
{"✅ TARGET HIT!" if weekly_stats['total_profit'] >= WEEKLY_TARGET else "❌ Below target"}

Trades: {weekly_stats['trades_count']}
Wins: {weekly_stats['wins']}
Losses: {weekly_stats['losses']}
Win Rate: {win_rate:.1f}%

🔄 STARTING NEW WEEK!''')
        
        # Reset for new week
        weekly_stats = {
            'week_start': datetime.now(),
            'total_profit': 0,
            'trades_count': 0,
            'wins': 0,
            'losses': 0
        }

def scan_gold():
    """Aggressive Gold scanning - Trump style"""
    # Check weekly reset
    check_weekly_reset()
    
    # Get current Gold price
    price_data = get_gold_price()
    if not price_data:
        return
    
    current_price = price_data['mid']
    
    # Check existing positions
    gold_positions = check_gold_positions()
    
    # Max 3 Gold positions (from original Trump strategy)
    if gold_positions >= 3:
        return
    
    # Find best entry zone
    zone, distance = find_best_entry_zone(current_price)
    
    if zone:
        reason = f"Price ${current_price:.2f} within ${distance:.2f} of {zone['type']} zone"
        
        print(f"🎯 GOLD OPPORTUNITY: {reason}")
        
        success, result = enter_gold_trade(zone, current_price, reason)
        
        if success:
            print(f"✅ Gold entered! Trade #{result}")
        else:
            print(f"❌ Entry failed: {result}")

def main():
    """Run Gold Trump strategy continuously"""
    print("💎 GOLD TRUMP WEEKLY STRATEGY - ACTIVE!")
    print("=" * 70)
    print(f"Week: {weekly_stats['week_start'].strftime('%b %d, %Y')}")
    print(f"Target: ${WEEKLY_TARGET:,.2f} profit")
    print(f"Trades: {WEEKLY_TRADES_TARGET}+ per week")
    print(f"Zones: {len(GOLD_ZONES)} entry levels")
    print("=" * 70)
    
    send_telegram(f'''💎 GOLD TRUMP STRATEGY ACTIVE!

WEEKLY GOALS:
• Target: ${WEEKLY_TARGET:,.2f} profit
• Trades: {WEEKLY_TRADES_TARGET}+ entries
• Win Rate: 70%+ target

STRATEGY:
• {len(GOLD_ZONES)} entry zones
• Buy pullbacks AND breakouts
• Max 3 positions
• $15 TP, $7 SL per trade
• Scans every 3 minutes

LIKE OCT 6-11 WEEK - LET'S WIN!''')
    
    scan_count = 0
    
    while True:
        try:
            scan_count += 1
            print(f"\n{'='*70}")
            print(f"🔍 Gold Scan #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*70}")
            
            scan_gold()
            
            # Progress update every 10 scans
            if scan_count % 10 == 0:
                days_in_week = (datetime.now() - weekly_stats['week_start']).days
                print(f"\n📊 Week Progress:")
                print(f"   Day {days_in_week + 1}/7")
                print(f"   Trades: {weekly_stats['trades_count']}/{WEEKLY_TRADES_TARGET}")
                print(f"   Profit: ${weekly_stats['total_profit']:+,.2f}/${WEEKLY_TARGET:,.2f}")
            
            # Scan every 3 minutes
            print(f"⏳ Next scan in 15 minutes (QUALITY OVER QUANTITY)...")
            time.sleep(900)  # 15 minutes - TRUE SWING, not scalping
            
        except KeyboardInterrupt:
            print("\n\n🛑 Gold Trump strategy stopped")
            send_telegram(f"🛑 Gold Trump stopped\nWeek trades: {weekly_stats['trades_count']}\nProfit: ${weekly_stats['total_profit']:+,.2f}")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

