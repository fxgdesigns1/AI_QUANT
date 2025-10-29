#!/usr/bin/env python3
import requests
import json

# OANDA Configuration
OANDA_API_KEY = 'REMOVED_SECRET'
OANDA_ACCOUNT_ID = '101-004-30719775-008'
OANDA_BASE_URL = 'https://api-fxpractice.oanda.com'

headers = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

# Get account info
try:
    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}'
    response = requests.get(url, headers=headers, timeout=10)
    account_info = response.json()['account']
    
    print('=== ACCOUNT PERFORMANCE ===')
    print(f'Balance: ${float(account_info["balance"]):.2f}')
    print(f'Unrealized P&L: ${float(account_info["unrealizedPL"]):.2f}')
    print(f'Total Equity: ${float(account_info["balance"]) + float(account_info["unrealizedPL"]):.2f}')
    print()
except Exception as e:
    print(f'Error getting account info: {e}')

# Get current positions
try:
    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/positions'
    response = requests.get(url, headers=headers, timeout=10)
    positions = response.json()['positions']
    
    print('=== CURRENT POSITIONS ===')
    for pos in positions:
        instrument = pos['instrument']
        long_units = float(pos['long']['units'])
        short_units = float(pos['short']['units'])
        unrealized_pl = float(pos['unrealizedPL'])
        
        if long_units > 0 or short_units > 0:
            print(f'{instrument}:')
            if long_units > 0:
                print(f'  LONG: {long_units} units')
            if short_units > 0:
                print(f'  SHORT: {short_units} units')
            print(f'  P&L: ${unrealized_pl:.2f}')
            print()
except Exception as e:
    print(f'Error getting positions: {e}')

# Get current prices
try:
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing'
    params = {'instruments': ','.join(instruments)}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    prices = response.json()['prices']
    print('=== CURRENT MARKET PRICES ===')
    for price_data in prices:
        instrument = price_data['instrument']
        bid = float(price_data['bids'][0]['price'])
        ask = float(price_data['asks'][0]['price'])
        mid = (bid + ask) / 2
        spread = ask - bid
        
        print(f'{instrument}: {mid:.5f} (spread: {spread:.5f})')
    print()
except Exception as e:
    print(f'Error getting prices: {e}')

# Analyze what signals the AI would generate
print('=== AI SIGNAL ANALYSIS ===')
try:
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing'
    params = {'instruments': ','.join(instruments)}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    prices = response.json()['prices']
    
    for price_data in prices:
        instrument = price_data['instrument']
        bid = float(price_data['bids'][0]['price'])
        ask = float(price_data['asks'][0]['price'])
        mid = (bid + ask) / 2
        spread = ask - bid
        
        if spread > 0.0005:  # Skip if spread too wide
            continue
            
        signal = None
        if instrument == 'EUR_USD':
            if mid_price > 1.0500:
                signal = f'BUY signal at {mid:.5f} (above 1.0500)'
            elif mid_price < 1.0400:
                signal = f'SELL signal at {mid:.5f} (below 1.0400)'
        elif instrument == 'GBP_USD':
            if mid_price > 1.2500:
                signal = f'BUY signal at {mid:.5f} (above 1.2500)'
            elif mid_price < 1.2300:
                signal = f'SELL signal at {mid:.5f} (below 1.2300)'
        elif instrument == 'XAU_USD':
            if mid_price > 2000:
                signal = f'BUY signal at {mid:.5f} (above 2000)'
            elif mid_price < 1950:
                signal = f'SELL signal at {mid:.5f} (below 1950)'
        
        if signal:
            print(f'{instrument}: {signal}')
        else:
            print(f'{instrument}: Monitoring (no signal)')
            
except Exception as e:
    print(f'Error analyzing signals: {e}')
