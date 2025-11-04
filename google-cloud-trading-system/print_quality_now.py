#!/usr/bin/env python3
import sys, logging
sys.path.insert(0, '.')
from datetime import datetime
from src.core.data_feed import get_data_feed
from src.strategies.momentum_trading import get_momentum_trading_strategy

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

instruments = ['XAU_USD','GBP_USD','EUR_USD','USD_JPY','AUD_USD','NZD_USD','USD_CAD']

print("== LIVE QUALITY SNAPSHOT ==")
print(f"Time (London): {datetime.utcnow().strftime('%H:%M:%S')}\n")

feed = get_data_feed()
prices = feed.get_latest_prices(instruments)

strategy = get_momentum_trading_strategy()

from src.core.data_feed import MarketData

for inst in instruments:
    p = prices.get(inst)
    if not p:
        print(f"{inst}: no price")
        continue
    md = {inst: MarketData(pair=inst, bid=p.bid, ask=p.ask, timestamp=p.timestamp, is_live=True, data_source='OANDA', spread=p.ask-p.bid, last_update_age=0)}
    print(f"-- {inst} -- bid {p.bid:.5f} / ask {p.ask:.5f} spread {p.ask-p.bid:.5f}")
    # analyze_market logs quality like: Skipping XAU_USD: quality 62.3 < 85 (...)
    strategy.analyze_market(md)

print("\nNote: Look for 'Skipping <PAIR>: quality X < Y' or 'QUALITY PASS' lines above.")
