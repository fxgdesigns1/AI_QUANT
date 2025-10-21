#!/usr/bin/env python3
"""
Cloud Run Server with Background Auto-Trading Scanner
Runs web server for Cloud Run health checks + background trading scanner
"""

import sys
import os
import threading
import time
from flask import Flask, jsonify
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, 'src')
load_dotenv('oanda_config.env')

from src.core.oanda_client import OandaClient
from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3

app = Flask(__name__)

# Global scanner state
scanner_status = {
    "running": False,
    "last_scan": None,
    "scan_count": 0,
    "accounts": []
}

class BackgroundScanner(threading.Thread):
    """Background thread for auto-trading scanner"""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.accounts = [
            {
                "id": "101-004-30719775-008",
                "name": "Strategy #1",
                "strategy": get_strategy_rank_1(),
                "max_positions": 5,
                "position_size": 2000
            },
            {
                "id": "101-004-30719775-007",
                "name": "Strategy #2",
                "strategy": get_strategy_rank_2(),
                "max_positions": 5,
                "position_size": 2000
            },
            {
                "id": "101-004-30719775-006",
                "name": "Strategy #3",
                "strategy": get_strategy_rank_3(),
                "max_positions": 5,
                "position_size": 2000
            }
        ]
        
        self.clients = {}
        for acc in self.accounts:
            self.clients[acc['id']] = OandaClient(account_id=acc['id'])
        
        print("✅ Background scanner initialized")
    
    def scan_and_trade(self):
        """Scan and trade"""
        global scanner_status
        
        scanner_status["scan_count"] += 1
        scanner_status["last_scan"] = datetime.now().isoformat()
        
        for account in self.accounts:
            try:
                client = self.clients[account['id']]
                account_info = client.get_account_info()
                current_trades = account_info.open_trade_count
                
                if current_trades >= account['max_positions']:
                    continue
                
                prices = client.get_current_prices(["GBP_USD"])
                gbp_price = prices["GBP_USD"]
                
                candles_data = client.get_candles("GBP_USD", "M5", 50)
                if not candles_data:
                    continue
                
                signal = account['strategy'].scan_for_signal(candles_data, gbp_price)
                
                if signal and hasattr(signal, 'signal') and signal.signal in ['BUY', 'SELL']:
                    units = account['position_size'] if signal.signal == 'BUY' else -account['position_size']
                    
                    if signal.signal == 'BUY':
                        sl = gbp_price.ask - 0.0050
                        tp = gbp_price.ask + 0.0100
                    else:
                        sl = gbp_price.bid + 0.0050
                        tp = gbp_price.bid - 0.0100
                    
                    order = client.place_market_order(
                        instrument="GBP_USD",
                        units=units,
                        stop_loss=sl,
                        take_profit=tp
                    )
                    
                    print(f"✅ Trade placed on {account['name']}: {signal.signal}")
                    
            except Exception as e:
                print(f"❌ Error on {account['name']}: {e}")
    
    def run(self):
        """Run scanner continuously"""
        global scanner_status
        scanner_status["running"] = True
        
        print("🚀 Background scanner started (24/7 mode)")
        
        while True:
            try:
                self.scan_and_trade()
                time.sleep(300)  # 5 minutes
            except Exception as e:
                print(f"Scanner error: {e}")
                time.sleep(60)

# Web routes for Cloud Run
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Auto-Trading GBP Strategies",
        "scanner": scanner_status
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/status')
def status():
    return jsonify(scanner_status)

if __name__ == "__main__":
    # Start background scanner
    scanner = BackgroundScanner()
    scanner.start()
    
    # Start web server for Cloud Run
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
