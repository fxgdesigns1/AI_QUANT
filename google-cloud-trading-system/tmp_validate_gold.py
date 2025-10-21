import time
from src.strategies.gold_scalping import get_gold_scalping_strategy
from src.core.data_feed import get_data_feed

strat = get_gold_scalping_strategy()
feed = get_data_feed()

try:
    feed.start()
except Exception as e:
    print("Start feed error:", e)

for i in range(30):
    md = feed.get_market_data("XAU_USD")
    sigs = strat.analyze_market(md)
    if sigs:
        print("Signals:", [(s.instrument, s.side.value, round(s.confidence,2)) for s in sigs])
        break
    time.sleep(2)

feed.stop()
