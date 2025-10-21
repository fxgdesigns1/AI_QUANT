#!/usr/bin/env python3
"""
Place small test trades on all accounts to verify trading capability
"""

import requests
import json
from datetime import datetime

# OANDA Configuration - CORRECT API KEY
OANDA_API_KEY = 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a'
OANDA_ENV = 'practice'
OANDA_BASE_URL = f'https://api-fxpractice.oanda.com/v3'

# Telegram
TELEGRAM_TOKEN = '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU'
TELEGRAM_CHAT_ID = '6100678501'

# Test accounts and instruments - CLOUD ACTIVE ACCOUNTS
TEST_ACCOUNTS = {
    '101-004-30719775-008': {'name': 'Primary (Multi-Strategy)', 'instrument': 'GBP_USD', 'units': 100},
    '101-004-30719775-007': {'name': 'Gold Scalp (Ultra Strict)', 'instrument': 'XAU_USD', 'units': 10},
    '101-004-30719775-006': {'name': 'Strategy Alpha (Momentum)', 'instrument': 'EUR_USD', 'units': 100},
}

def send_telegram(message):
    """Send message to Telegram"""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except:
        return False

def get_current_price(account_id, instrument):
    """Get current price for instrument"""
    headers = {
        'Authorization': f'Bearer {OANDA_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    url = f'{OANDA_BASE_URL}/accounts/{account_id}/pricing'
    params = {'instruments': instrument}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'prices' in data and len(data['prices']) > 0:
                price_data = data['prices'][0]
                bid = float(price_data['bids'][0]['price'])
                ask = float(price_data['asks'][0]['price'])
                return {'bid': bid, 'ask': ask, 'mid': (bid + ask) / 2}
    except Exception as e:
        print(f"Error getting price: {e}")
    return None

def place_test_trade(account_id, instrument, units):
    """Place a small test trade"""
    headers = {
        'Authorization': f'Bearer {OANDA_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    url = f'{OANDA_BASE_URL}/accounts/{account_id}/orders'
    
    # Get current price to set stop loss and take profit
    price_info = get_current_price(account_id, instrument)
    if not price_info:
        return {'success': False, 'error': 'Could not get price'}
    
    # Calculate SL and TP (tight for test trade)
    if units > 0:  # BUY
        entry_price = price_info['ask']
        stop_loss = entry_price - 0.0020  # 20 pips for forex, $2 for gold
        take_profit = entry_price + 0.0030  # 30 pips for forex, $3 for gold
    else:  # SELL
        entry_price = price_info['bid']
        stop_loss = entry_price + 0.0020
        take_profit = entry_price - 0.0030
    
    # For gold, adjust
    if instrument == 'XAU_USD':
        if units > 0:
            stop_loss = entry_price - 5
            take_profit = entry_price + 8
        else:
            stop_loss = entry_price + 5
            take_profit = entry_price - 8
    
    order_data = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "stopLossOnFill": {
                "price": f"{stop_loss:.5f}" if instrument != 'XAU_USD' else f"{stop_loss:.2f}"
            },
            "takeProfitOnFill": {
                "price": f"{take_profit:.5f}" if instrument != 'XAU_USD' else f"{take_profit:.2f}"
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=order_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            if 'orderFillTransaction' in result:
                fill = result['orderFillTransaction']
                return {
                    'success': True,
                    'trade_id': fill.get('id'),
                    'price': fill.get('price'),
                    'units': fill.get('units'),
                    'instrument': instrument,
                    'pl': fill.get('pl', '0'),
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
            elif 'orderCancelTransaction' in result:
                cancel = result['orderCancelTransaction']
                return {
                    'success': False,
                    'error': f"Order cancelled: {cancel.get('reason', 'Unknown')}"
                }
        
        return {
            'success': False,
            'error': f"HTTP {response.status_code}: {response.text[:200]}"
        }
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("="*80)
    print("🧪 PLACING TEST TRADES ON ALL ACCOUNTS")
    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S London')}")
    print("="*80)
    print()
    
    # Send start notification
    send_telegram("🧪 TEST TRADES STARTING NOW!\n\nPlacing small test orders on all accounts to verify trading capability...")
    
    results = []
    successful = 0
    failed = 0
    
    for account_id, config in TEST_ACCOUNTS.items():
        account_name = config['name']
        instrument = config['instrument']
        units = config['units']
        
        print(f"📊 Testing {account_name} ({account_id[-3:]})")
        print(f"   Instrument: {instrument}")
        print(f"   Units: {units}")
        
        result = place_test_trade(account_id, instrument, units)
        
        if result['success']:
            successful += 1
            print(f"   ✅ SUCCESS!")
            print(f"      Trade ID: {result['trade_id']}")
            print(f"      Price: {result['price']}")
            print(f"      SL: {result['stop_loss']:.5f}")
            print(f"      TP: {result['take_profit']:.5f}")
            
            results.append({
                'account': account_name,
                'status': '✅ SUCCESS',
                'instrument': instrument,
                'price': result['price'],
                'trade_id': result['trade_id']
            })
        else:
            failed += 1
            print(f"   ❌ FAILED: {result['error']}")
            
            results.append({
                'account': account_name,
                'status': '❌ FAILED',
                'instrument': instrument,
                'error': result['error']
            })
        
        print()
    
    # Summary
    print("="*80)
    print(f"📊 TEST RESULTS SUMMARY")
    print("="*80)
    print(f"✅ Successful: {successful}/{len(TEST_ACCOUNTS)}")
    print(f"❌ Failed: {failed}/{len(TEST_ACCOUNTS)}")
    print()
    
    # Build Telegram message
    message = f"""🧪 TEST TRADES COMPLETE!

⏰ Time: {datetime.now().strftime('%H:%M:%S London')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RESULTS:

✅ Successful: {successful}/{len(TEST_ACCOUNTS)}
❌ Failed: {failed}/{len(TEST_ACCOUNTS)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DETAILED RESULTS:

"""
    
    for r in results:
        if r['status'] == '✅ SUCCESS':
            message += f"""{r['status']} {r['account']}
   {r['instrument']} @ {r['price']}
   Trade ID: {r['trade_id']}

"""
        else:
            message += f"""{r['status']} {r['account']}
   {r['instrument']}
   Error: {r.get('error', 'Unknown')[:50]}

"""
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    if successful == len(TEST_ACCOUNTS):
        message += "🎉 ALL ACCOUNTS CAN TRADE!\n\nSystem is READY for live trading!\nBring on PPI and CPI! 🚀💰"
    elif successful > 0:
        message += f"⚠️ {successful} accounts working!\n\nPartial success - investigate failed accounts.\nWorking accounts can trade PPI/CPI!"
    else:
        message += "🚨 NO ACCOUNTS TRADING!\n\nCritical issue - need to diagnose!"
    
    send_telegram(message)
    
    print("="*80)
    print("✅ Test trades complete!")
    print("📱 Results sent to Telegram")
    print("="*80)
    
    return successful, failed

if __name__ == "__main__":
    successful, failed = main()
    exit(0 if failed == 0 else 1)

