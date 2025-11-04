#!/usr/bin/env python3
import sys, time, logging
sys.path.insert(0, '.')
from datetime import datetime
from src.core.data_feed import get_data_feed
from src.strategies.momentum_trading import get_momentum_trading_strategy

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

instruments = ['XAU_USD','GBP_USD','EUR_USD','USD_JPY','AUD_USD','NZD_USD','USD_CAD']

print("== LIVE QUALITY SNAPSHOT ==")
print(f"Time (London): {datetime.utcnow().strftime('%H:%M:%S')}\n")

feed = get_data_feed()
feed.add_instruments(instruments)

# Start feed if not running
try:
    feed.start()
except Exception as e:
    # Might already be running; continue
    pass

# Wait to accumulate fresh prices
time.sleep(6)

market = feed.get_latest_data()

from src.core.data_feed import MarketData
strategy = get_momentum_trading_strategy()

for inst in instruments:
    data = market.get(inst)
    if not data:
        print(f"{inst}: no live data yet")
        continue
    md = {inst: data}
    print(f"-- {inst} -- bid {data.bid:.5f} / ask {data.ask:.5f} spread {data.spread:.5f}")
    strategy.analyze_market(md)

print("\nNote: Look for 'Skipping <PAIR>: quality X < Y' or 'QUALITY PASS' lines above, which include ADX and momentum.")
