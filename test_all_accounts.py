#!/usr/bin/env python3
"""Place test trades on ALL accounts"""

import requests
import json

OANDA_API_KEY = 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a'
TELEGRAM_TOKEN = '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU'
TELEGRAM_CHAT_ID = '6100678501'
BASE_URL = 'https://api-fxpractice.oanda.com/v3'

ALL_ACCOUNTS = {
    '101-004-30719775-001': {'name': 'Gold Trump Week', 'instrument': 'XAU_USD', 'units': 10},
    '101-004-30719775-009': {'name': 'Account 009', 'instrument': 'XAU_USD', 'units': 10},
    '101-004-30719775-010': {'name': 'Account 010', 'instrument': 'EUR_USD', 'units': 100},
    '101-004-30719775-011': {'name': 'Momentum Trading', 'instrument': 'USD_JPY', 'units': 100},
}

def send_telegram(msg):
    requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                 json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg})

def place_order(account_id, instrument, units):
    headers = {'Authorization': f'Bearer {OANDA_API_KEY}', 'Content-Type': 'application/json'}
    
    # Get price
    url = f'{BASE_URL}/accounts/{account_id}/pricing'
    response = requests.get(url, headers=headers, params={'instruments': instrument})
    
    if response.status_code != 200:
        return {'success': False, 'error': f'Price fetch failed: {response.status_code}'}
    
    price_data = response.json()['prices'][0]
    bid = float(price_data['bids'][0]['price'])
    ask = float(price_data['asks'][0]['price'])
    
    # Set SL/TP
    if units > 0:
        entry = ask
        if 'XAU' in instrument:
            sl = entry - 5
            tp = entry + 8
        else:
            sl = entry - 0.0020
            tp = entry + 0.0030
    else:
        entry = bid
        if 'XAU' in instrument:
            sl = entry + 5
            tp = entry - 8
        else:
            sl = entry + 0.0020
            tp = entry - 0.0030
    
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
    
    url = f'{BASE_URL}/accounts/{account_id}/orders'
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
        elif 'orderCancelTransaction' in result:
            return {'success': False, 'error': result['orderCancelTransaction'].get('reason')}
    
    return {'success': False, 'error': response.text[:100]}

print("Testing ALL accounts...")
send_telegram("🧪 TESTING ALL REMAINING ACCOUNTS NOW...")

results = []
for account_id, config in ALL_ACCOUNTS.items():
    name = config['name']
    instrument = config['instrument']
    units = config['units']
    
    print(f"Testing {name}...")
    result = place_order(account_id, instrument, units)
    
    if result['success']:
        print(f"  ✅ Trade ID: {result['id']}")
        results.append(f"✅ {name}: {instrument} @ {result['price']} (ID: {result['id']})")
    else:
        print(f"  ❌ {result['error']}")
        results.append(f"❌ {name}: {result['error'][:50]}")

message = "🧪 ALL ACCOUNTS TEST COMPLETE:\\n\\n" + "\\n".join(results)
send_telegram(message)
print("\\n" + message)




