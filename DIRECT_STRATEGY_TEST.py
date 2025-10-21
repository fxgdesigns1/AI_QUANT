#!/usr/bin/env python3
"""
DIRECT TEST - Bypass validation complexity, test strategy directly
"""

import sys
sys.path.insert(0, '/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.oanda_client import OandaClient
from datetime import datetime
import os

print('🔍 DIRECT STRATEGY TEST - LIVE MARKET NOW')
print('=' * 80)
print()

# Get CURRENT live prices (not historical)
api_key = 'REMOVED_SECRET'
account_id = '101-004-30719775-011'

client = OandaClient(api_key=api_key, account_id=account_id)

instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']

print('Getting LIVE prices right now...')
prices = client.get_current_prices(instruments)

print()
for inst, price_data in prices.items():
    print(f'{inst}: Bid={price_data.bid:.5f}, Ask={price_data.ask:.5f}')

print()
print('Now calling momentum strategy with LIVE data...')
print()

# Load strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy
strategy = get_momentum_trading_strategy()

print(f'Strategy: {strategy.name}')
print(f'Parameters: ADX>={strategy.min_adx}, Momentum>={strategy.min_momentum*100:.2f}%, Volume>={strategy.min_volume}')
print()

# Call with live market data
market_data_dict = {}
for inst, price_data in prices.items():
    from src.core.data_feed import MarketData
    market_data_dict[inst] = MarketData(
        pair=inst,
        bid=price_data.bid,
        ask=price_data.ask,
        timestamp=str(datetime.now()),
        is_live=True,
        data_source='OANDA_LIVE',
        spread=price_data.ask - price_data.bid,
        last_update_age=0
    )

signals = strategy.analyze_market(market_data_dict)

print(f'SIGNALS GENERATED: {len(signals)}')
print()

if signals:
    print('✅ STRATEGY WORKING!')
    for sig in signals:
        print(f'  • {sig.instrument} {sig.side.value} @ SL:{sig.stop_loss:.5f} TP:{sig.take_profit:.5f}')
else:
    print('❌ NO SIGNALS - Even with LIVE data!')
    print()
    print('The strategy has fundamental issues blocking ALL signal generation.')
    print('Need to review entire strategy flow.')

