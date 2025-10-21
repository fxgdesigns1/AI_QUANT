#!/usr/bin/env python3
"""
24/7 Cloud Auto-Trading Scanner with Weekend Pause
Pauses during weekends to save resources
"""

import sys
import os
import threading
import time
import logging
from flask import Flask, jsonify
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, 'src')
load_dotenv('oanda_config.env')

from src.core.oanda_client import OandaClient
from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state
state = {
    "scanner_running": False,
    "last_scan": None,
    "scan_count": 0,
    "last_trade": None,
    "accounts_status": {},
    "market_status": "unknown",
    "paused_for_weekend": False
}

scanner_thread = None

def is_weekend():
    """Check if it's weekend (Saturday/Sunday) in UTC"""
    now = datetime.now(timezone.utc)
    # Forex market closes Friday 5pm EST (22:00 UTC) and opens Sunday 5pm EST (22:00 UTC)
    weekday = now.weekday()  # Monday=0, Sunday=6
    hour = now.hour
    
    # Friday after 22:00 UTC or Saturday all day
    if (weekday == 4 and hour >= 22) or weekday == 5:
        return True
    # Sunday before 22:00 UTC
    if weekday == 6 and hour < 22:
        return True
    
    return False

def is_trading_hours():
    """Check if it's during active trading hours"""
    now = datetime.now(timezone.utc)
    hour = now.hour
    
    # London session: 08:00-17:00 UTC
    # NY session: 13:00-20:00 UTC
    # Combined: 08:00-20:00 UTC on weekdays
    
    if is_weekend():
        return False
    
    # Active hours: 8am to 8pm UTC
    return 8 <= hour < 20

def run_scanner():
    """Background scanner function with weekend pause"""
    global state
    
    logger.info("🚀 Starting 24/7 background scanner with weekend pause...")
    
    # Initialize accounts
    accounts = [
        {"id": "101-004-30719775-008", "name": "Strategy #1", "strategy": get_strategy_rank_1(), "size": 2000, "max": 5},
        {"id": "101-004-30719775-007", "name": "Strategy #2", "strategy": get_strategy_rank_2(), "size": 2000, "max": 5},
        {"id": "101-004-30719775-006", "name": "Strategy #3", "strategy": get_strategy_rank_3(), "size": 2000, "max": 5}
    ]
    
    clients = {acc["id"]: OandaClient(account_id=acc["id"]) for acc in accounts}
    
    state["scanner_running"] = True
    logger.info("✅ Scanner initialized with 3 accounts")
    
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            
            # Check if it's weekend
            if is_weekend():
                if not state["paused_for_weekend"]:
                    logger.info("🛑 WEEKEND DETECTED - Pausing scanner until markets open")
                    logger.info(f"   Current time: {now_utc.strftime('%A %Y-%m-%d %H:%M UTC')}")
                    logger.info("   Markets closed: Friday 5pm EST to Sunday 5pm EST")
                    logger.info("   Will resume: Sunday 5pm EST (Monday 00:00 UTC)")
                    state["paused_for_weekend"] = True
                    state["market_status"] = "closed"
                
                # Check every hour during weekend
                time.sleep(3600)  # 1 hour
                continue
            
            # Market is open
            if state["paused_for_weekend"]:
                logger.info("✅ MARKETS OPEN - Resuming scanner")
                logger.info(f"   Current time: {now_utc.strftime('%A %Y-%m-%d %H:%M UTC')}")
                state["paused_for_weekend"] = False
            
            state["market_status"] = "open"
            
            # Check if we're in active trading hours
            if not is_trading_hours():
                if state["scan_count"] % 12 == 0:  # Log every hour outside trading hours
                    logger.info(f"⏸️ Outside active trading hours ({now_utc.strftime('%H:%M UTC')})")
                    logger.info("   Active hours: 08:00-20:00 UTC (London/NY sessions)")
                time.sleep(300)  # Still check every 5 minutes
                continue
            
            # Active trading - run scan
            state["scan_count"] += 1
            state["last_scan"] = now_utc.isoformat()
            
            if state["scan_count"] % 12 == 0:  # Log every hour during active trading
                logger.info(f"🔍 Scan #{state['scan_count']} - Active Trading")
            
            for acc in accounts:
                try:
                    client = clients[acc["id"]]
                    info = client.get_account_info()
                    
                    state["accounts_status"][acc["id"]] = {
                        "balance": float(info.balance),
                        "trades": info.open_trade_count
                    }
                    
                    if info.open_trade_count >= acc["max"]:
                        continue
                    
                    prices = client.get_current_prices(["GBP_USD"])
                    candles = client.get_candles("GBP_USD", "M5", 50)
                    
                    if not candles:
                        continue
                    
                    signal = acc["strategy"].scan_for_signal(candles, prices["GBP_USD"])
                    
                    if signal and hasattr(signal, 'signal') and signal.signal in ['BUY', 'SELL']:
                        units = acc["size"] if signal.signal == 'BUY' else -acc["size"]
                        
                        if signal.signal == 'BUY':
                            sl = prices["GBP_USD"].ask - 0.0050
                            tp = prices["GBP_USD"].ask + 0.0100
                        else:
                            sl = prices["GBP_USD"].bid + 0.0050
                            tp = prices["GBP_USD"].bid - 0.0100
                        
                        order = client.place_market_order("GBP_USD", units, sl, tp)
                        
                        state["last_trade"] = {
                            "account": acc["name"],
                            "signal": signal.signal,
                            "time": now_utc.isoformat()
                        }
                        
                        logger.info(f"✅ TRADE: {acc['name']} {signal.signal}")
                        
                except Exception as e:
                    logger.error(f"Error on {acc['name']}: {e}")
            
            # Wait 5 minutes between scans during active trading
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"Scanner error: {e}")
            time.sleep(60)

@app.route('/')
def home():
    now_utc = datetime.now(timezone.utc)
    return jsonify({
        "status": "running",
        "service": "24/7 Auto-Trading with Weekend Pause",
        "current_time_utc": now_utc.strftime("%A %Y-%m-%d %H:%M:%S UTC"),
        "market_status": state["market_status"],
        "paused_for_weekend": state["paused_for_weekend"],
        "state": state
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/status')
def status():
    now_utc = datetime.now(timezone.utc)
    return jsonify({
        **state,
        "current_time_utc": now_utc.strftime("%A %Y-%m-%d %H:%M:%S UTC"),
        "is_weekend": is_weekend(),
        "is_trading_hours": is_trading_hours()
    })

# Start scanner when app loads
def start_scanner():
    global scanner_thread
    if scanner_thread is None or not scanner_thread.is_alive():
        scanner_thread = threading.Thread(target=run_scanner, daemon=True)
        scanner_thread.start()
        logger.info("Scanner thread started")

start_scanner()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
