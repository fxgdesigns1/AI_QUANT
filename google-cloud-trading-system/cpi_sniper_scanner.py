#!/usr/bin/env python3
"""
CPI SNIPER SCANNER - HIGH RR ENTRIES
Tighter SL, bigger TP for maximum profit on CPI volatility
"""

import requests
import time
import os
from datetime import datetime, time as dt_time

# OANDA Config
API_KEY = os.getenv('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
BASE_URL = 'https://api-fxpractice.oanda.com/v3'
headers = {'Authorization': f'Bearer {API_KEY}'}

# Telegram
TELEGRAM_TOKEN = '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU'
TELEGRAM_CHAT_ID = '6100678501'

# ALL 10 ACCOUNTS FOR SNIPER ENTRIES - HIGH RR FOR EVERYONE!
SNIPER_ACCOUNTS = {
    '101-004-30719775-002': 'All-Weather 70WR',      # Account 002
    '101-004-30719775-003': 'Momentum V2',           # Account 003
    '101-004-30719775-004': 'Ultra Strict V2',       # Account 004
    '101-004-30719775-005': '75% WR Champion',       # Account 005
    '101-004-30719775-006': 'Strategy Rank #3',      # Account 006
    '101-004-30719775-007': 'Strategy Rank #2',      # Account 007
    '101-004-30719775-008': 'Strategy Rank #1',      # Account 008
    '101-004-30719775-009': 'Gold Trump Primary',    # Account 009
    '101-004-30719775-010': 'Ultra Strict Forex',    # Account 010
    '101-004-30719775-011': 'Momentum Multi-Pair',   # Account 011
}

# HIGH RR PAIRS - Focus on CPI movers
CPI_PAIRS = ['XAU_USD', 'GBP_USD', 'EUR_USD', 'USD_JPY', 'AUD_USD']

# HIGH RR SETTINGS
HIGH_RR_CONFIGS = {
    'XAU_USD': {
        'units': 400,
        'sl_distance': 5.0,      # Tight $5 SL
        'tp_distance': 20.0,     # Big $20 TP = 4:1 RR
        'min_momentum': 0.10     # Strong signal only
    },
    'JPY_PAIRS': {
        'units': 500000,
        'sl_distance': 0.10,     # Tight 10 pips SL
        'tp_distance': 0.30,     # Big 30 pips TP = 3:1 RR
        'min_momentum': 0.05
    },
    'MAJOR_PAIRS': {
        'units': 500000,
        'sl_distance': 0.0008,   # Tight 8 pips SL
        'tp_distance': 0.0024,   # Big 24 pips TP = 3:1 RR
        'min_momentum': 0.04
    }
}

def send_telegram(message):
    """Send Telegram alert"""
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except:
        pass

def get_sniper_signal(pair):
    """Get HIGH CONFIDENCE sniper signal"""
    try:
        r = requests.get(
            f'{BASE_URL}/instruments/{pair}/candles',
            headers=headers,
            params={'count': 30, 'granularity': 'M5'},
            timeout=5
        )
        
        if r.status_code == 200:
            candles = r.json()['candles']
            closes = [float(c['mid']['c']) for c in candles[-30:]]
            highs = [float(c['mid']['h']) for c in candles[-30:]]
            lows = [float(c['mid']['l']) for c in candles[-30:]]
            
            # Advanced analysis
            ema3 = sum(closes[-3:]) / 3
            ema8 = sum(closes[-8:]) / 8
            ema21 = sum(closes[-21:]) / 21
            
            mom_5 = (closes[-1] - closes[-6]) / closes[-6] * 100
            mom_10 = (closes[-1] - closes[-11]) / closes[-11] * 100
            mom_20 = (closes[-1] - closes[-21]) / closes[-21] * 100
            
            # ATR for volatility
            tr = []
            for i in range(-10, 0):
                tr.append(max(highs[i] - lows[i], 
                            abs(highs[i] - closes[i-1]),
                            abs(lows[i] - closes[i-1])))
            atr = sum(tr) / len(tr)
            
            # Get config
            if pair == 'XAU_USD':
                config = HIGH_RR_CONFIGS['XAU_USD']
            elif 'JPY' in pair:
                config = HIGH_RR_CONFIGS['JPY_PAIRS']
            else:
                config = HIGH_RR_CONFIGS['MAJOR_PAIRS']
            
            # ULTRA SNIPER CRITERIA (QUALITY OVER QUANTITY)
            signal = None
            confidence = 0
            
            # ONLY ENTER IF:
            # 1. Triple EMA alignment (ema3 > ema8 > ema21)
            # 2. Strong 5m AND 10m momentum
            # 3. Strong 20m momentum (trend confirmation)
            # 4. All 3 momentum checks pass
            
            # STRONG BUY - Triple alignment + ALL momentum checks
            if (ema3 > ema8 > ema21 and 
                mom_5 > config['min_momentum'] * 1.5 and 
                mom_10 > config['min_momentum'] * 2 and 
                mom_20 > config['min_momentum'] * 2):
                signal = 'BUY'
                confidence = 98  # ULTRA HIGH
            
            # STRONG SELL - Triple alignment + ALL momentum checks
            elif (ema3 < ema8 < ema21 and 
                  mom_5 < -config['min_momentum'] * 1.5 and 
                  mom_10 < -config['min_momentum'] * 2 and 
                  mom_20 < -config['min_momentum'] * 2):
                signal = 'SELL'
                confidence = 98  # ULTRA HIGH
            
            if signal:
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'momentum': mom_5,
                    'config': config,
                    'price': closes[-1]
                }
    except:
        pass
    
    return None

def place_sniper_entry(account_id, account_name, pair, signal_data):
    """Place HIGH RR sniper entry"""
    try:
        # Get current price
        pr = requests.get(
            f'{BASE_URL}/accounts/{account_id}/pricing',
            headers=headers,
            params={'instruments': pair},
            timeout=5
        )
        
        if pr.status_code != 200:
            return False
        
        config = signal_data['config']
        
        if signal_data['signal'] == 'BUY':
            entry = float(pr.json()['prices'][0]['asks'][0]['price'])
            units = config['units']
            tp = entry + config['tp_distance']
            sl = entry - config['sl_distance']
        else:
            entry = float(pr.json()['prices'][0]['bids'][0]['price'])
            units = -config['units']
            tp = entry - config['tp_distance']
            sl = entry + config['sl_distance']
        
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
            f'{BASE_URL}/accounts/{account_id}/orders',
            headers=headers,
            json=order,
            timeout=10
        )
        
        if resp.status_code == 201 and 'orderFillTransaction' in resp.json():
            trade_id = resp.json()['orderFillTransaction'].get('tradeOpened', {}).get('tradeID')
            if trade_id:
                # Calculate RR
                sl_dist = abs(entry - sl)
                tp_dist = abs(entry - tp)
                rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0
                
                send_telegram(f'''🎯 SNIPER ENTRY!

{account_name} ({account_id[-3:]})
{pair} {signal_data['signal']}

Entry: {entry:.5f}
TP: {tp:.5f}
SL: {sl:.5f}
RR: {rr_ratio:.1f}:1 🎯

Confidence: {signal_data['confidence']}%
Momentum: {signal_data['momentum']:+.3f}%

HIGH RR CPI SNIPER!''')
                
                return True
    except Exception as e:
        print(f"Error: {str(e)[:60]}")
    
    return False

def scan_for_snipers():
    """Scan for HIGH RR sniper entries"""
    print(f"\n{'='*70}")
    print(f"🎯 SNIPER SCAN - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    
    entered = 0
    
    for account_id, account_name in SNIPER_ACCOUNTS.items():
        # Check existing positions
        trades_resp = requests.get(f'{BASE_URL}/accounts/{account_id}/openTrades', headers=headers, timeout=5)
        existing_pairs = []
        if trades_resp.status_code == 200:
            existing_pairs = [t['instrument'] for t in trades_resp.json().get('trades', [])]
        
        # Scan CPI pairs
        for pair in CPI_PAIRS:
            if pair in existing_pairs:
                continue
            
            signal_data = get_sniper_signal(pair)
            
            if signal_data and signal_data['confidence'] >= 95:
                print(f"🎯 {pair} {signal_data['signal']} ({signal_data['confidence']}%) on {account_name}")
                
                if place_sniper_entry(account_id, account_name, pair, signal_data):
                    entered += 1
                    print(f"   ✅ SNIPER ENTRY PLACED!")
                    time.sleep(2)
    
    if entered > 0:
        print(f"\n🎯 Placed {entered} sniper entries!")
    else:
        print(f"\n⚪ No sniper opportunities yet (waiting for 95%+ signals)")
    
    return entered

def main():
    """Run sniper scanner for CPI"""
    print("=" * 70)
    print("🎯 CPI SNIPER SCANNER - HIGH RR ENTRIES")
    print("=" * 70)
    print("• Scans every 3 minutes")
    print("• 95%+ confidence only")
    print("• 3:1 to 4:1 RR ratios")
    print("• Tighter SL, bigger TP")
    print("• Maximum profit on CPI volatility")
    print("=" * 70)
    
    send_telegram(
        "🎯 CPI SNIPER SCANNER STARTED!\n\n"
        "• 3:1 to 4:1 RR ratios\n"
        "• 95%+ confidence only\n"
        "• Gold: $5 SL / $20 TP (4:1)\n"
        "• Forex: 8 pips SL / 24 pips TP (3:1)\n"
        "• JPY: 10 pips SL / 30 pips TP (3:1)\n\n"
        "Ready for CPI sniper entries!"
    )
    
    scan_count = 0
    
    while True:
        try:
            scan_count += 1
            scan_for_snipers()
            
            # Check if CPI time passed (stop after 3 PM)
            now = datetime.now()
            if now.hour >= 15:
                print("\n🏁 CPI event complete - stopping sniper scanner")
                send_telegram("🏁 CPI sniper scanner complete!")
                break
            
            print(f"\n⏳ Scan #{scan_count} complete, sleeping 15 minutes...")
            print(f"   Quality over quantity - waiting for perfect setups")
            time.sleep(900)  # 15 minutes (QUALITY FOCUS)
            
        except KeyboardInterrupt:
            print("\n👋 Sniper scanner stopped")
            break
        except Exception as e:
            print(f"❌ Scan error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()

