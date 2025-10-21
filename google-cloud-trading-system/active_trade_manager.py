#!/usr/bin/env python3
"""
Active Trade Manager - PROPERLY FIXED
Closes individual trades using OANDA trade API
"""

import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient

class ActiveTradeManager:
    def __init__(self):
        load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
        
        self.api_key = os.getenv('OANDA_API_KEY')
        self.environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
        
        self.accounts = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD': os.getenv('GOLD_SCALP_ACCOUNT'),
            'ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        self.clients = {
            name: OandaClient(self.api_key, account_id, self.environment)
            for name, account_id in self.accounts.items()
        }
        
        self.early_close_loss_pct = -0.0015
        self.early_close_profit_pct = 0.001
        self.max_hold_time_minutes = 90
        self.max_loss_hold_time = 20
        
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        self.trade_entry_times = {}
        self.actions_taken = 0
        
        print("✅ Active Trade Manager initialized - FIXED VERSION")
    
    def send_telegram(self, message: str):
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            requests.post(url, json={'chat_id': self.telegram_chat_id, 'text': message}, timeout=5)
        except:
            pass
    
    def close_trade_by_id(self, client: OandaClient, trade_id: str) -> bool:
        """Close a specific trade by ID"""
        try:
            url = f"{client.base_url}/v3/accounts/{client.account_id}/trades/{trade_id}/close"
            response = requests.put(url, headers=client.headers, json={})
            
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            return False
    
    def manage_all_positions(self):
        total_actions = 0
        
        for account_name, client in self.clients.items():
            try:
                open_trades = client.get_open_trades()
                
                for trade in open_trades:
                    trade_id = trade['id']
                    instrument = trade['instrument']
                    current_units = float(trade['currentUnits'])
                    price = float(trade['price'])
                    unrealized_pl = float(trade['unrealizedPL'])
                    
                    # Get current price
                    try:
                        prices = client.get_current_prices([instrument])
                        current_price = prices[instrument].bid if current_units > 0 else prices[instrument].ask
                        
                        if current_units > 0:
                            pl_pct = (current_price - price) / price
                        else:
                            pl_pct = (price - current_price) / price
                    except:
                        pl_pct = unrealized_pl / (abs(current_units) * price) if price > 0 else 0
                    
                    if trade_id not in self.trade_entry_times:
                        self.trade_entry_times[trade_id] = datetime.now()
                    
                    time_in_trade = (datetime.now() - self.trade_entry_times[trade_id]).total_seconds() / 60
                    
                    should_close = False
                    reason = ""
                    
                    if pl_pct <= self.early_close_loss_pct:
                        should_close = True
                        reason = f"EARLY LOSS ({pl_pct*100:.2f}%)"
                    elif pl_pct < 0 and time_in_trade >= self.max_loss_hold_time:
                        should_close = True
                        reason = f"MAX LOSS TIME ({time_in_trade:.0f}min, {pl_pct*100:.2f}%)"
                    elif pl_pct >= self.early_close_profit_pct:
                        should_close = True
                        reason = f"QUICK PROFIT ({pl_pct*100:.2f}%)"
                    elif time_in_trade >= self.max_hold_time_minutes:
                        should_close = True
                        reason = f"MAX TIME ({time_in_trade:.0f}min, {pl_pct*100:.2f}%)"
                    
                    if should_close:
                        if self.close_trade_by_id(client, trade_id):
                            message = f"🔴 {account_name} - CLOSED {instrument}\n   {reason}\n   Units: {abs(current_units):,.0f}"
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                            self.send_telegram(message)
                            self.actions_taken += 1
                            total_actions += 1
                            
                            if trade_id in self.trade_entry_times:
                                del self.trade_entry_times[trade_id]
                        
            except Exception as e:
                print(f"Error in {account_name}: {e}")
        
        return total_actions
    
    def run_continuous(self):
        print("\n🚀 Active Trade Manager RUNNING - FIXED VERSION")
        print("   Monitoring every 5 seconds...\n")
        self.send_telegram("🚀 ACTIVE TRADE MANAGER RESTARTED\n✅ Fixed version - closes individual trades\n• Close at -0.15%\n• Take profit at +0.10%\n• Max 20min for losers")
        
        try:
            while True:
                actions = self.manage_all_positions()
                if actions > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Actions: {actions} | Total: {self.actions_taken}")
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Stopped")
            self.send_telegram(f"🛑 Trade Manager STOPPED\nTotal actions: {self.actions_taken}")

if __name__ == '__main__':
    manager = ActiveTradeManager()
    manager.run_continuous()
