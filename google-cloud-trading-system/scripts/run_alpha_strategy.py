#!/usr/bin/env python3
"""
Run Alpha EMA Strategy against the STRATEGY_ALPHA demo account.

Practice-only. Streams live prices via LiveDataFeed and submits trades
through OrderManager with proper risk checks.
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.data_feed import LiveDataFeed
from src.core.order_manager import OrderManager, OrderSide
from src.strategies.alpha import get_alpha_strategy


def main():
    load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
    env = os.getenv('OANDA_ENVIRONMENT', 'practice')
    if env != 'practice':
        print('❌ Refusing to run: environment is not practice (demo).')
        sys.exit(1)

    alpha_id = os.getenv('STRATEGY_ALPHA_ACCOUNT')
    if not alpha_id:
        print('❌ Missing STRATEGY_ALPHA_ACCOUNT in oanda_config.env')
        sys.exit(1)

    # Target roughly $1000 wins per trade via env; OM will cap by risk
    os.environ['TARGET_WIN_USD'] = os.getenv('TARGET_WIN_USD', '1000')
    strategy = get_alpha_strategy()

    # Instruments from strategy definition
    feed = LiveDataFeed(account_id=alpha_id, instruments=strategy.instruments)
    om = OrderManager(account_id=alpha_id)

    def on_data(market_data):
        signals = strategy.analyze_market(market_data)
        if not signals:
            return
        for sig in signals:
            # Place LIMIT entries with wider favorable offset for London volatility
            md = market_data.get(sig.instrument)
            if not md:
                continue
            mid = (md.bid + md.ask) / 2
            # For BUY, below mid; for SELL, above mid (0.15%)
            if sig.side == OrderSide.BUY:
                limit_price = mid * (1 - 0.0015)
            else:
                limit_price = mid * (1 + 0.0015)
            om.execute_limit_trade(sig, limit_price)

    feed.add_data_callback(on_data)

    print('✅ Alpha strategy started (demo). Press Ctrl+C to stop.')
    try:
        feed.start()
        # Run indefinitely; user can stop manually
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print('\n🛑 Alpha strategy stopped by user')
    finally:
        feed.stop()


if __name__ == '__main__':
    main()


