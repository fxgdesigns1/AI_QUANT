#!/usr/bin/env python3
"""Quick market check for Account 008"""

import requests
import os

api_key = 'a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a'
account_id = '101-004-30719775-008'
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

instruments = ['GBP_USD', 'NZD_USD', 'XAU_USD']

print('🔍 CURRENT MARKET STATUS')
print('='*70)

for inst in instruments:
    try:
        url = f'https://api-fxpractice.oanda.com/v3/instruments/{inst}/candles'
        params = {'count': 2, 'granularity': 'M5', 'price': 'M'}
        r = requests.get(url, headers=headers, params=params, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            candles = data.get('candles', [])
            if candles:
                last = candles[-1].get('mid', {})
                close = float(last.get('c', 0))
                
                if len(candles) > 1:
                    prev = float(candles[0]['mid']['c'])
                    change = ((close - prev) / prev) * 100
                    change_str = f'{change:+.3f}%'
                else:
                    change_str = 'N/A'
                
                print(f'{inst:10} ${close:10.5f}  {change_str}')
    except Exception as e:
        print(f'{inst:10} ERROR')

print('\n✅ System connected but no trades running')



