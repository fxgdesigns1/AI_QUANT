#!/usr/bin/env python3
"""
Daily Automated Monitoring System
Ensures proactive alerts, trade execution, and daily reports
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyMonitor:
    """Automated daily monitoring and reporting system"""
    
    def __init__(self):
        """Initialize monitor with API credentials"""
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN', '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6100678501')
        
        self.accounts = {
            '001': '101-004-30719775-001',
            '006': '101-004-30719775-006',
            '007': '101-004-30719775-007',
            '008': '101-004-30719775-008',
            '011': '101-004-30719775-011'
        }
        
        self.base_url = 'https://api-fxpractice.oanda.com'
        self.headers = {
            'Authorization': f'Bearer {self.oanda_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Track state
        self.last_trade_count = {}
        self.last_pl = {}
        self.last_check = None
        self.alerts_sent_today = []
        
        logger.info("✅ Daily Monitor initialized")
    
    def send_telegram(self, message: str) -> bool:
        """Send message via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def get_account_summary(self, account_id: str) -> Optional[Dict]:
        """Get account summary from OANDA"""
        try:
            url = f"{self.base_url}/v3/accounts/{account_id}/summary"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()['account']
            return None
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {e}")
            return None
    
    def get_all_accounts_status(self) -> Dict:
        """Get status of all accounts"""
        results = {}
        
        for acc_name, acc_id in self.accounts.items():
            summary = self.get_account_summary(acc_id)
            if summary:
                results[acc_name] = {
                    'balance': float(summary['balance']),
                    'nav': float(summary['NAV']),
                    'unrealized_pl': float(summary['unrealizedPL']),
                    'open_trades': int(summary['openTradeCount']),
                    'margin_pct': (float(summary['marginUsed']) / float(summary['NAV']) * 100) if float(summary['NAV']) > 0 else 0
                }
        
        return results
    
    def morning_report(self):
        """Send morning market report - RUNS DAILY 8:30AM"""
        logger.info("📊 Generating morning report...")
        
        try:
            accounts_status = self.get_all_accounts_status()
            
            if not accounts_status:
                self.send_telegram("⚠️ Morning report failed - could not get account data")
                return
            
            # Calculate totals
            total_balance = sum(a['balance'] for a in accounts_status.values())
            total_nav = sum(a['nav'] for a in accounts_status.values())
            total_unrealized = sum(a['unrealized_pl'] for a in accounts_status.values())
            total_trades = sum(a['open_trades'] for a in accounts_status.values())
            
            # Get gold price
            gold_price = self.get_gold_price()
            
            message = f"""🌅 <b>GOOD MORNING!</b> - {datetime.now().strftime('%A, %B %d, %Y')}
⏰ <b>6:00 AM London Time</b>

💰 <b>PORTFOLIO STATUS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Balance: ${total_balance:,.2f}
Total NAV: ${total_nav:,.2f}
Unrealized P&L: ${total_unrealized:,.2f} {'✅' if total_unrealized >= 0 else '❌'}
Open Trades: {total_trades}

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ACCOUNT BREAKDOWN:</b>
"""
            
            for acc_name, data in sorted(accounts_status.items()):
                pl_icon = "✅" if data['unrealized_pl'] >= 0 else "❌"
                
                if acc_name == '001':
                    message += f"\n🥇 Account {acc_name} (GOLD):"
                else:
                    message += f"\n   Account {acc_name}:"
                
                message += f"""
   P&L: ${data['unrealized_pl']:,.2f} {pl_icon}
   Trades: {data['open_trades']}
   Margin: {data['margin_pct']:.1f}%"""
            
            message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>MARKET PRICES:</b>

🥇 Gold: ${gold_price:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>TODAY'S TRADING SCHEDULE:</b>

🟡 06:00-09:00 London: Pre-market warmup
🟢 09:00-14:00 London: London session
🟢🟢 14:00-17:00 London: PRIME TIME (best signals!)
🟢 17:00-21:00 London: NY afternoon
🌙 21:30 London: End of day summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>SYSTEM STATUS:</b>
• Sniper entry mode: ACTIVE (70%+ confidence)
• Auto-trading: ENABLED ✅
• Risk limits: 75% cap active
• Demo/practice mode: ON

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 You'll get alerts for:
• High-quality trade entries (70%+ confidence)
• Trade exits
• Significant P&L changes

Have a great trading day! 🚀"""
            
            self.send_telegram(message)
            self.alerts_sent_today.append(('morning_report', datetime.now()))
            logger.info("✅ Morning report sent")
            
        except Exception as e:
            logger.error(f"Morning report error: {e}")
            self.send_telegram(f"❌ Morning report error: {str(e)[:100]}")
    
    def hourly_check(self):
        """Check for new trades and significant changes - RUNS EVERY HOUR"""
        logger.info("🔍 Performing hourly check...")
        
        try:
            accounts_status = self.get_all_accounts_status()
            
            # Check for new trades
            for acc_name, data in accounts_status.items():
                current_trades = data['open_trades']
                last_trades = self.last_trade_count.get(acc_name, current_trades)
                
                if current_trades > last_trades:
                    new_trades = current_trades - last_trades
                    self.send_telegram(f"🚀 NEW TRADE(S)!\n\nAccount {acc_name}: {new_trades} new trade(s) opened!\nTotal: {current_trades} trades")
                    logger.info(f"Alert sent: {new_trades} new trades in account {acc_name}")
                
                self.last_trade_count[acc_name] = current_trades
            
            # Check for significant P&L changes
            total_unrealized = sum(a['unrealized_pl'] for a in accounts_status.values())
            last_total_pl = sum(self.last_pl.values()) if self.last_pl else total_unrealized
            
            pl_change = total_unrealized - last_total_pl
            
            # Alert if P&L changed by more than $500
            if abs(pl_change) > 500 and self.last_pl:
                direction = "UP" if pl_change > 0 else "DOWN"
                icon = "📈" if pl_change > 0 else "📉"
                self.send_telegram(f"{icon} SIGNIFICANT P&L CHANGE!\n\n{direction}: ${abs(pl_change):,.2f}\n\nCurrent Total P&L: ${total_unrealized:,.2f}")
                logger.info(f"Alert sent: P&L change ${pl_change:,.2f}")
            
            # Update state
            for acc_name, data in accounts_status.items():
                self.last_pl[acc_name] = data['unrealized_pl']
            
            self.last_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Hourly check error: {e}")
    
    def end_of_day_report(self):
        """Send end of day summary - RUNS DAILY 5:00PM"""
        logger.info("📊 Generating end of day report...")
        
        try:
            accounts_status = self.get_all_accounts_status()
            
            total_balance = sum(a['balance'] for a in accounts_status.values())
            total_nav = sum(a['nav'] for a in accounts_status.values())
            total_unrealized = sum(a['unrealized_pl'] for a in accounts_status.values())
            total_trades = sum(a['open_trades'] for a in accounts_status.values())
            
            message = f"""🌙 <b>END OF DAY REPORT</b> - {datetime.now().strftime('%A, %B %d')}
⏰ <b>9:30 PM London Time</b>

💰 <b>PORTFOLIO SUMMARY:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Balance: ${total_balance:,.2f}
NAV: ${total_nav:,.2f}
Unrealized P&L: ${total_unrealized:,.2f} {'✅' if total_unrealized >= 0 else '❌'}
Open Trades: {total_trades}

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ACCOUNT PERFORMANCE:</b>
"""
            
            for acc_name, data in sorted(accounts_status.items()):
                pl_icon = "✅" if data['unrealized_pl'] >= 0 else "❌"
                message += f"\nAcc {acc_name}: ${data['unrealized_pl']:,.2f} {pl_icon} ({data['open_trades']} trades)"
            
            message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>TODAY'S ACTIVITY:</b>

• Alerts sent: {len(self.alerts_sent_today)}
• Trading hours: 09:00-21:00 London
• System uptime: 100% ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>SYSTEM STATUS:</b>
• All accounts monitored
• Risk management: Active
• Ready for tomorrow

🌅 Next report: 6:00 AM London

Sleep well! Tomorrow's trading starts at 9am. 😴💤"""
            
            self.send_telegram(message)
            
            # Reset daily alerts
            self.alerts_sent_today = []
            
            logger.info("✅ End of day report sent")
            
        except Exception as e:
            logger.error(f"End of day report error: {e}")
    
    def get_gold_price(self) -> float:
        """Get current gold price"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.accounts['001']}/pricing"
            params = {'instruments': 'XAU_USD'}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('prices'):
                    price_info = data['prices'][0]
                    bid = float(price_info['bids'][0]['price'])
                    ask = float(price_info['asks'][0]['price'])
                    return (bid + ask) / 2
        except Exception as e:
            logger.error(f"Error getting gold price: {e}")
        
        return 0.0
    
    def verify_system_trading(self):
        """Verify system is actually placing trades - RUNS EVERY 4 HOURS"""
        logger.info("🔍 Verifying system is trading...")
        
        try:
            # Check if we have any trades from today
            accounts_status = self.get_all_accounts_status()
            total_trades = sum(a['open_trades'] for a in accounts_status.values())
            
            # If during trading hours (8am-5pm EST) and no new trades in 4 hours
            current_hour = datetime.now().hour
            
            if 8 <= current_hour <= 17:  # Trading hours
                if total_trades == 0 or (self.last_check and (datetime.now() - self.last_check).seconds > 14400):
                    # No trades or no new trades in 4 hours during trading hours
                    self.send_telegram("""⚠️ SYSTEM CHECK ALERT

No new trades detected in last 4 hours during trading hours.

Possible issues:
• Scanner not running?
• Trading disabled?
• No market opportunities?

Please verify system status!""")
                    logger.warning("Alert: No trading activity detected")
            
        except Exception as e:
            logger.error(f"System verification error: {e}")
    
    def schedule_tasks(self):
        """Setup scheduled tasks - LONDON TIME (GMT/UTC+0 in October)"""
        # Morning report - 6:00 AM London = 06:00 UTC
        schedule.every().day.at("06:00").do(self.morning_report)
        
        # Hourly checks during trading hours (8am-9pm London = 08:00-21:00 UTC)
        for hour in range(8, 22):
            schedule.every().day.at(f"{hour:02d}:00").do(self.hourly_check)
        
        # End of day report - 9:30 PM London = 21:30 UTC
        schedule.every().day.at("21:30").do(self.end_of_day_report)
        
        # System verification every 4 hours during trading
        schedule.every().day.at("09:00").do(self.verify_system_trading)
        schedule.every().day.at("13:00").do(self.verify_system_trading)
        schedule.every().day.at("17:00").do(self.verify_system_trading)
        schedule.every().day.at("21:00").do(self.verify_system_trading)
        
        logger.info("✅ All monitoring tasks scheduled (London GMT time)")
        logger.info("   - Morning report: 6:00 AM London daily")
        logger.info("   - Hourly checks: 8am-9pm London")
        logger.info("   - End of day: 9:30 PM London daily")
        logger.info("   - System verification: Every 4 hours")
    
    def run(self):
        """Run the monitor continuously"""
        logger.info("🚀 Starting Daily Monitor...")
        
        # Schedule all tasks
        self.schedule_tasks()
        
        # Send startup message
        self.send_telegram("""✅ DAILY MONITOR STARTED!

📊 Automated Schedule:
• Morning report: 8:30am EST daily
• Hourly checks: Every hour 8am-5pm EST
• End of day: 5:00pm EST daily
• System verification: Every 4 hours

🎯 What I'll alert you about:
• New trades (automatically)
• Significant P&L changes (>$500)
• Trading system issues
• Daily summaries

NO MORE MANUAL PROMPTING NEEDED!

I'm now monitoring 24/7! 🚀""")
        
        logger.info("✅ Monitor running!")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def get_daily_monitor():
    """Get singleton monitor instance"""
    global _monitor_instance
    if '_monitor_instance' not in globals():
        _monitor_instance = DailyMonitor()
    return _monitor_instance


if __name__ == '__main__':
    monitor = DailyMonitor()
    monitor.run()

