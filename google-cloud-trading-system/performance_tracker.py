#!/usr/bin/env python3
"""
Performance Tracker - Analyzes trading improvements
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient

class PerformanceTracker:
    def __init__(self):
        load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
        
        self.accounts = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD': os.getenv('GOLD_SCALP_ACCOUNT'),
            'ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        self.clients = {
            name: OandaClient(os.getenv('OANDA_API_KEY'), account_id, os.getenv('OANDA_ENVIRONMENT', 'practice'))
            for name, account_id in self.accounts.items()
        }
        
    def analyze_account(self, name: str, client: OandaClient):
        print(f"\n{'='*60}")
        print(f"📊 {name} ACCOUNT ANALYSIS")
        print(f"{'='*60}")
        
        try:
            account_info = client.get_account_info()
            positions = client.get_positions()
            open_trades = client.get_open_trades()
            
            print(f"💰 Balance: {account_info.balance} {account_info.currency}")
            print(f"📈 Unrealized P&L: {account_info.unrealized_pl}")
            print(f"💵 Realized P&L: {account_info.realized_pl}")
            print(f"📊 Open Trades: {len(open_trades)}")
            print(f"📊 Open Positions: {account_info.open_position_count}")
            
            if open_trades:
                print(f"\n🔍 OPEN TRADES:")
                total_pl = 0
                for trade in open_trades:
                    instrument = trade['instrument']
                    units = float(trade['currentUnits'])
                    price = float(trade['price'])
                    unrealized_pl = float(trade['unrealizedPL'])
                    total_pl += unrealized_pl
                    
                    side = 'LONG' if units > 0 else 'SHORT'
                    pl_str = f"+{unrealized_pl:.2f}" if unrealized_pl >= 0 else f"{unrealized_pl:.2f}"
                    emoji = "🟢" if unrealized_pl >= 0 else "🔴"
                    
                    print(f"   {emoji} {instrument}: {side} {abs(units):,.0f} @ {price:.5f} | P&L: {pl_str}")
                
                print(f"\n   Total Unrealized P&L: {total_pl:+.2f}")
                
            else:
                print("\n✅ No open trades")
                
        except Exception as e:
            print(f"❌ Error analyzing {name}: {e}")
    
    def run_analysis(self):
        print("\n🚀 PERFORMANCE TRACKER")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for name, client in self.clients.items():
            self.analyze_account(name, client)
        
        print(f"\n{'='*60}")
        print("✅ Analysis Complete")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    tracker = PerformanceTracker()
    tracker.run_analysis()
