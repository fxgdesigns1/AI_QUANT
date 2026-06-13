#!/usr/bin/env python3
"""Execute trades at current market levels with Trump DNA parameters"""

import os
import sys
sys.path.insert(0, 'google-cloud-trading-system/src')

from dotenv import load_dotenv
load_dotenv('google-cloud-trading-system/oanda_config.env')

import requests
from datetime import datetime

OANDA_API_KEY = os.getenv('OANDA_API_KEY')
OANDA_ENV = os.getenv('OANDA_ENV', 'practice')
BASE_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3' if OANDA_ENV == 'practice' else 'https://api-fxtrade.oanda.com/v3'

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Fail-closed: require critical env vars
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable is required")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

# Trade execution scripts must not invent lanes/accounts.
# Lane 010 is manual_only/protected and must not be targeted by automated helper scripts.
# Require explicit account selection via env allowlist.
ACCOUNT_ID_PREFIX = os.getenv("ACCOUNT_ID_PREFIX", "101-004-30719775-").strip()
ACCOUNT_SUFFIX_ALLOWLIST = [s.strip() for s in os.getenv("ACCOUNT_SUFFIX_ALLOWLIST", "").split(",") if s.strip()]
ALLOW_LANE_010_TESTS = os.getenv("ALLOW_LANE_010_TESTS", "false").lower() == "true"

if not ACCOUNT_SUFFIX_ALLOWLIST:
    raise ValueError("ACCOUNT_SUFFIX_ALLOWLIST is required (e.g., '011'). Refusing to use hardcoded lane assumptions.")
if ("010" in ACCOUNT_SUFFIX_ALLOWLIST) and (not ALLOW_LANE_010_TESTS):
    raise ValueError("Refusing to target protected lane 010. Set ALLOW_LANE_010_TESTS=true to override explicitly.")

# Minimal safe default: execute on allowed lanes only; caller must set instrument/size params explicitly.
TRADES = [
    {
        "account": f"{ACCOUNT_ID_PREFIX}{suffix}",
        "name": f"Lane {suffix}",
        "instrument": os.getenv("EXECUTE_INSTRUMENT", "EUR_USD"),
        "units": int(os.getenv("EXECUTE_UNITS", "100")),
        "sl_pips": int(os.getenv("EXECUTE_SL_PIPS", "20")),
        "tp_pips": int(os.getenv("EXECUTE_TP_PIPS", "50")),
    }
    for suffix in ACCOUNT_SUFFIX_ALLOWLIST
]

def send_telegram(msg):
    requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                 json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg})

def place_trade(trade_config):
    account = trade_config['account']
    instrument = trade_config['instrument']
    units = trade_config['units']
    sl_pips = trade_config['sl_pips']
    tp_pips = trade_config['tp_pips']
    
    headers = {'Authorization': f'Bearer {OANDA_API_KEY}', 'Content-Type': 'application/json'}
    
    # Get current price
    url = f'{BASE_URL}/accounts/{account}/pricing'
    response = requests.get(url, headers=headers, params={'instruments': instrument})
    
    if response.status_code != 200:
        return {'success': False, 'error': f'Price fetch failed: {response.status_code}'}
    
    price_data = response.json()['prices'][0]
    ask = float(price_data['asks'][0]['price'])
    
    # Calculate SL/TP
    if 'XAU' in instrument:
        sl = ask - sl_pips
        tp = ask + tp_pips
    else:
        sl = ask - (sl_pips * 0.0001)
        tp = ask + (tp_pips * 0.0001)
    
    # Place order
    order_data = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "stopLossOnFill": {"price": f"{sl:.5f}" if 'XAU' not in instrument else f"{sl:.2f}"},
            "takeProfitOnFill": {"price": f"{tp:.5f}" if 'XAU' not in instrument else f"{tp:.2f}"}
        }
    }
    
    url = f'{BASE_URL}/accounts/{account}/orders'
    response = requests.post(url, headers=headers, json=order_data)
    
    if response.status_code in [200, 201]:
        result = response.json()
        if 'orderFillTransaction' in result:
            fill = result['orderFillTransaction']
            return {
                'success': True,
                'id': fill['id'],
                'price': fill['price'],
                'instrument': instrument
            }
    
    return {'success': False, 'error': response.text[:100]}

# Execute all trades
print("=" * 80)
print("🎯 EXECUTING TRUMP DNA SNIPER TRADES")
print(f"⏰ {datetime.now().strftime('%H:%M:%S London')}")
print("=" * 80)
print()

send_telegram("🎯 EXECUTING SNIPER TRADES NOW!\\n\\nTrump DNA framework active...\\n")

results = []
for trade in TRADES:
    print(f"Executing: {trade['name']} - {trade['instrument']}")
    result = place_trade(trade)
    
    if result['success']:
        print(f"   ✅ SUCCESS! Trade ID: {result['id']} @ {result['price']}")
        results.append(f"✅ {trade['name']}: {trade['instrument']} @ {result['price']} (ID: {result['id']})")
    else:
        print(f"   ❌ FAILED: {result['error'][:50]}")
        results.append(f"❌ {trade['name']}: {result['error'][:30]}")
    print()

print("=" * 80)
successful = len([r for r in results if '✅' in r])
print(f"📊 RESULTS: {successful}/{len(TRADES)} executed successfully")
print("=" * 80)

# Send results to Telegram
message = f"🎯 SNIPER TRADES EXECUTED!\\n\\n{chr(10).join(results)}\\n\\nTotal: {successful}/{len(TRADES)} successful!"
send_telegram(message)
print("\\n✅ Results sent to Telegram!")



