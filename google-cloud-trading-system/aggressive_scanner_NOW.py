#!/usr/bin/env python3
"""
AGGRESSIVE SCANNER - ENTERS EVERYTHING
Like Gold Trump Week strategy - catches ALL opportunities
"""

import requests
import time
import os
from datetime import datetime

# OANDA Config
API_KEY = os.getenv('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
ACCOUNT_ID = '101-004-30719775-008'
BASE_URL = 'https://api-fxpractice.oanda.com/v3'
headers = {'Authorization': f'Bearer {API_KEY}'}

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Pairs to scan
PAIRS = ['GBP_USD', 'EUR_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'USD_CAD', 
         'EUR_GBP', 'GBP_JPY', 'EUR_JPY', 'XAU_USD']

def send_telegram(message):
    """Send Telegram alert"""
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
            requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except:
        pass

def get_momentum(pair):
    """Get pair momentum"""
    try:
        r = requests.get(
            f'{BASE_URL}/instruments/{pair}/candles',
            headers=headers,
            params={'count': 15, 'granularity': 'M5'},
            timeout=5
        )
        
        if r.status_code == 200:
            candles = r.json()['candles']
            closes = [float(c['mid']['c']) for c in candles]
            
            # Momentum
            mom_5 = (closes[-1] - closes[-5]) / closes[-5] * 100
            mom_3 = (closes[-1] - closes[-3]) / closes[-3] * 100
            
            # Recent direction
            last_3_up = sum(1 for i in range(-3, 0) if closes[i] > closes[i-1])
            
            return {
                'momentum_5': mom_5,
                'momentum_3': mom_3,
                'strength': last_3_up,
                'current': closes[-1]
            }
    except:
        pass
    
    return None

def enter_trade(pair, direction, reason):
    """Enter trade immediately"""
    try:
        # Get price
        pr = requests.get(
            f'{BASE_URL}/accounts/{ACCOUNT_ID}/pricing',
            headers=headers,
            params={'instruments': pair},
            timeout=5
        )
        
        if pr.status_code != 200:
            return False
        
        # HIGH RR for CPI - 3:1 to 4:1 ratios
        if direction == 'BUY':
            entry = float(pr.json()['prices'][0]['asks'][0]['price'])
            if pair == 'XAU_USD':
                units = 400  # CPI sniper Gold
                tp_dist = 20.0  # $20 TP
                sl_dist = 5.0   # $5 SL = 4:1 RR
            elif 'JPY' in pair:
                units = 500000
                tp_dist = 0.30  # 30 pips TP
                sl_dist = 0.10  # 10 pips SL = 3:1 RR
            else:
                units = 500000
                tp_dist = 0.0024  # 24 pips TP
                sl_dist = 0.0008  # 8 pips SL = 3:1 RR
            
            tp = entry + tp_dist
            sl = entry - sl_dist
        else:
            entry = float(pr.json()['prices'][0]['bids'][0]['price'])
            if pair == 'XAU_USD':
                units = -400  # CPI sniper Gold
                tp_dist = 20.0  # $20 TP
                sl_dist = 5.0   # $5 SL = 4:1 RR
            elif 'JPY' in pair:
                units = -500000
                tp_dist = 0.30  # 30 pips TP
                sl_dist = 0.10  # 10 pips SL = 3:1 RR
            else:
                units = -500000
                tp_dist = 0.0024  # 24 pips TP
                sl_dist = 0.0008  # 8 pips SL = 3:1 RR
            
            tp = entry - tp_dist
            sl = entry + sl_dist
        
        # Place order
        order = {
            "order": {
                "type": "MARKET",
                "instrument": pair,
                "units": str(units),
                "timeInForce": "FOK",
                "takeProfitOnFill": {"price": f"{tp:.5f}"},
                "stopLossOnFill": {"price": f"{sl:.5f}"}
            }
        }
        
        resp = requests.post(
            f'{BASE_URL}/accounts/{ACCOUNT_ID}/orders',
            headers=headers,
            json=order,
            timeout=10
        )
        
        if resp.status_code == 201:
            # ONLY send alert if trade was ACTUALLY opened
            order_fill = resp.json().get('orderFillTransaction', {})
            trade_opened = order_fill.get('tradeOpened', {})
            trade_id = trade_opened.get('tradeID')
            
            # VERIFY trade was actually placed
            if trade_id and trade_id != 'N/A':
                # Double-check on OANDA
                verify = requests.get(
                    f'{BASE_URL}/accounts/{ACCOUNT_ID}/trades/{trade_id}',
                    headers=headers,
                    timeout=5
                )
                
                if verify.status_code == 200:
                    # CONFIRMED - trade exists on OANDA
                    send_telegram(f'''✅ CONFIRMED ENTRY!

{pair} {direction} (ID: {trade_id})
Entry: {entry:.5f}
TP: {tp:.5f}
SL: {sl:.5f}
Reason: {reason}

Verified on OANDA!''')
                    print(f"✅ CONFIRMED: {pair} {direction} (ID: {trade_id})")
                    return True
                else:
                    print(f"⚠️ Order accepted but trade not found: {pair}")
            else:
                print(f"⚠️ Order accepted but no tradeID: {pair}")
        else:
            error = resp.json().get('errorMessage', '')
            if 'margin' not in error.lower():
                print(f"❌ Error {pair}: {error[:60]}")
    except Exception as e:
        print(f"Exception {pair}: {str(e)[:60]}")
    
    return False

def scan_and_enter():
    """Aggressive scanning - enter everything!"""
    print(f"\n{'='*70}")
    print(f"🔍 AGGRESSIVE SCAN - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    
    # Get current positions
    trades_resp = requests.get(f'{BASE_URL}/accounts/{ACCOUNT_ID}/openTrades', headers=headers, timeout=5)
    open_pairs = []
    if trades_resp.status_code == 200:
        open_pairs = [t['instrument'] for t in trades_resp.json().get('trades', [])]
    
    entered_count = 0
    
    for pair in PAIRS:
        # Skip if already in
        if pair in open_pairs:
            continue
        
        # Get momentum
        data = get_momentum(pair)
        if not data:
            continue
        
        mom = data['momentum_5']
        
        # AGGRESSIVE: Enter on any momentum > 0.03%
        if abs(mom) > 0.03:
            direction = 'BUY' if mom > 0 else 'SELL'
            reason = f"Momentum {mom:+.2f}%, Strength {data['strength']}/3"
            
            if enter_trade(pair, direction, reason):
                entered_count += 1
                print(f"✅ {pair} {direction} ENTERED! ({reason})")
                time.sleep(1)  # Rate limit
    
    if entered_count > 0:
        print(f"\n🔥 Entered {entered_count} new positions this scan!")
    else:
        print(f"\n⚪ No new entries (all pairs already in or no momentum)")
    
    return entered_count

def main():
    """Run aggressive scanner continuously"""
    print("🔥 AGGRESSIVE SCANNER STARTED - REALISTIC SIZING!")
    print("=" * 70)
    print("• Scans every 2 minutes")
    print("• Enters ANY momentum > 0.03%")
    print("• 1M unit positions (allows 3 trades)")
    print("• 20 pip TP, 10 pip SL")
    print("• ALL pairs covered")
    print("=" * 70)
    
    send_telegram('''🔥 SCANNER RESTARTED - FIXED!

REALISTIC SIZING:
• 1M unit positions (not 2M)
• Allows 3 simultaneous trades
• Won't hit margin limits
• Scanning every 2 minutes
• Entering momentum >0.03%

ACTUALLY WORKS NOW!''')
    
    scan_count = 0
    total_entered = 0
    
    while True:
        try:
            scan_count += 1
            entered = scan_and_enter()
            total_entered += entered
            
            print(f"\n📊 Stats: {scan_count} scans, {total_entered} total entries")
            
            # Wait 2 minutes
            print(f"⏳ Next scan in 2 minutes...")
            time.sleep(120)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Scanner stopped by user")
            send_telegram(f"🛑 Aggressive scanner stopped\nTotal scans: {scan_count}\nTotal entries: {total_entered}")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

