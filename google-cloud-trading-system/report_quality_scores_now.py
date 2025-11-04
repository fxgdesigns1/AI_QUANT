#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from datetime import datetime
from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

instruments = ['XAU_USD','GBP_USD','EUR_USD','USD_JPY','AUD_USD','NZD_USD','USD_CAD']

print("== QUALITY SCORE SNAPSHOT ==")
print(f"Time (London): {datetime.utcnow().strftime('%H:%M:%S')}\n")

fetcher = get_historical_fetcher()
recent = fetcher.get_recent_data_for_strategy(instruments, hours=24)

strategy = get_momentum_trading_strategy()

results = []
for inst in instruments:
    data = recent.get(inst, [])
    if not data:
        results.append((inst, None, None, None))
        continue
    last = data[-1]
    price = float(last['close'])
    market = {inst: MarketData(pair=inst, bid=price, ask=price+0.5, timestamp=last['time'], is_live=True, data_source='OANDA', spread=0.5, last_update_age=0)}
    # analyze_market will log quality and reasons; we only want to trigger internal calc
    strategy.analyze_market(market)

print("\n(See logs above for per-instrument quality, threshold, ADX, momentum)")
