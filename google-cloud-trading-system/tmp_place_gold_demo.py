from src.core.settings import settings
import time
from src.strategies.gold_scalping import get_gold_scalping_strategy
from src.core.data_feed import get_data_feed
from src.core.order_manager import get_order_manager

strat = get_gold_scalping_strategy()
feed = get_data_feed()

try:
    feed.start()
except Exception as e:
    print("Start feed error:", e)

signal = None
for i in range(30):
    md = feed.get_market_data("XAU_USD")
    sigs = strat.analyze_market(md)
    if sigs:
        signal = sigs[0]
        print("Signal:", signal.instrument, signal.side.value, round(signal.confidence,2))
        break
    time.sleep(2)

if signal:
    # Use PRIMARY account for gold scalping as configured
    import os
    primary = os.getenv("PRIMARY_ACCOUNT") or settings.oanda_account_id
    om = get_order_manager(primary)
    result = om.execute_trades([signal])
    print("Execution:", {k: (len(v) if isinstance(v, list) else v) for k,v in result.items() if k in ("total_executed","total_failed","error")})
else:
    print("No signal produced in sampling window")

feed.stop()
