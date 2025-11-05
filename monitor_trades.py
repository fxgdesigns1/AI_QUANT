#!/usr/bin/env python3
"""
Monitor and track all trading activity
Sends updates to Telegram and logs metrics
"""
import os
import sys
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables
os.environ['OANDA_API_KEY'] = "REMOVED_SECRET"
os.environ['OANDA_ACCOUNT_ID'] = "101-004-30719775-008"
os.environ['TELEGRAM_TOKEN'] = "7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"

class TradeMonitor:
    def __init__(self):
        self.api_key = os.getenv('OANDA_API_KEY')
        self.account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.last_trade_count = 0
        self.last_balance = 0
        self.trade_history = []
        
    def get_account_info(self):
        """Get account information"""
        try:
            url = f"https://api-fxpractice.oanda.com/v3/accounts/{self.account_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()['account']
            return None
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_trades(self):
        """Get all open trades"""
        try:
            url = f"https://api-fxpractice.oanda.com/v3/accounts/{self.account_id}/trades"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('trades', [])
            return []
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_recent_transactions(self, hours=1):
        """Get recent transactions"""
        try:
            url = f"https://api-fxpractice.oanda.com/v3/accounts/{self.account_id}/transactions"
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + 'Z'
            params = {'since': since}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('transactions', [])
            return []
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def send_telegram(self, message):
        """Send message to Telegram"""
        try:
            token = os.getenv('TELEGRAM_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send Telegram: {e}")
    
    def generate_report(self):
        """Generate trading report"""
        account = self.get_account_info()
        trades = self.get_trades()
        transactions = self.get_recent_transactions(24)
        
        if not account:
            return None
        
        # Calculate metrics
        total_trades = len(trades)
        total_pl = sum(float(t.get('unrealizedPL', 0)) for t in trades)
        recent_fills = [t for t in transactions if t.get('type') == 'ORDER_FILL']
        
        # Group by instrument
        by_instrument = {}
        for trade in trades:
            inst = trade['instrument']
            if inst not in by_instrument:
                by_instrument[inst] = {'count': 0, 'pl': 0, 'units': 0}
            by_instrument[inst]['count'] += 1
            by_instrument[inst]['pl'] += float(trade.get('unrealizedPL', 0))
            by_instrument[inst]['units'] += int(trade.get('currentUnits', 0))
        
        report = f"""📊 TRADING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 Account Status:
   Balance: ${float(account.get('balance', 0)):,.2f}
   Unrealized P&L: ${float(account.get('unrealizedPL', 0)):,.2f}
   NAV: ${float(account.get('NAV', 0)):,.2f}

📈 Trading Activity:
   Open Trades: {total_trades}
   Total Unrealized P&L: ${total_pl:,.2f}
   Recent Fills (24h): {len(recent_fills)}

📊 Positions by Instrument:"""
        
        for inst, data in sorted(by_instrument.items()):
            report += f"\n   • {inst}: {data['count']} trades, {data['units']} units, P&L: ${data['pl']:,.2f}"
        
        # Check for new trades
        if total_trades != self.last_trade_count:
            change = total_trades - self.last_trade_count
            report += f"\n\n🆕 Trade Count Change: {change:+d} ({self.last_trade_count} → {total_trades})"
            self.last_trade_count = total_trades
        
        # Check balance change
        current_balance = float(account.get('balance', 0))
        if abs(current_balance - self.last_balance) > 1:
            change = current_balance - self.last_balance
            report += f"\n💰 Balance Change: ${change:+,.2f} (${self.last_balance:,.2f} → ${current_balance:,.2f})"
            self.last_balance = current_balance
        
        return report
    
    def run(self):
        """Run monitoring loop"""
        logger.info("📊 Starting trade monitor...")
        
        # Send initial report
        report = self.generate_report()
        if report:
            logger.info(report)
            self.send_telegram(report)
        
        # Monitor every 5 minutes
        while True:
            try:
                time.sleep(300)  # 5 minutes
                report = self.generate_report()
                if report:
                    logger.info(report)
                    # Only send to Telegram if significant changes
                    if abs(self.last_trade_count - len(self.get_trades())) > 0 or \
                       abs(self.last_balance - float(self.get_account_info().get('balance', 0))) > 10:
                        self.send_telegram(report)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = TradeMonitor()
    monitor.run()
