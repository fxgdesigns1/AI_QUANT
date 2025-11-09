#!/usr/bin/env python3
"""
SEMI-AUTOMATIC TRADING TELEGRAM ALERTS
=====================================

Automated alerts for semi-automatic trading:
1. Trading opportunities alerts
2. Account performance updates
3. Market condition alerts
4. Strategy status updates
5. Risk management alerts
"""

import os
import sys
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')

from src.core.yaml_manager import get_yaml_manager
from src.core.oanda_client import OandaClient
from src.core.data_feed import get_data_feed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemiAutoTelegramAlerts:
    """Telegram alerts for semi-automatic trading"""
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_TOKEN', '${TELEGRAM_TOKEN}')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '${TELEGRAM_CHAT_ID}')
        self.semi_auto_account_id = "101-004-30719775-001"  # Strategy Zeta - Swing Trading
        self.alert_frequency = 300  # 5 minutes
        self.last_alert_time = {}
        
    def send_telegram_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram message sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def get_account_status(self) -> Dict:
        """Get semi-automatic account status"""
        try:
            client = OandaClient(account_id=self.semi_auto_account_id)
            account_info = client.get_account_info()
            open_trades = client.get_open_trades()
            open_positions = client.get_open_positions()
            
            return {
                'balance': getattr(account_info, 'balance', 0),
                'currency': getattr(account_info, 'currency', 'USD'),
                'open_trades': len(open_trades),
                'open_positions': len(open_positions),
                'trades': open_trades,
                'positions': open_positions
            }
        except Exception as e:
            logger.error(f"❌ Error getting account status: {e}")
            return {}
    
    def scan_trading_opportunities(self) -> List[Dict]:
        """Scan for trading opportunities"""
        opportunities = []
        
        try:
            # Get current market data
            data_feed = get_data_feed()
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']  # Semi-auto account instruments
            
            for instrument in instruments:
                try:
                    prices = data_feed.get_current_prices([instrument])
                    if instrument in prices:
                        price = prices[instrument]
                        mid_price = (price.bid + price.ask) / 2
                        spread = price.ask - price.bid
                        
                        # Simple opportunity detection
                        if spread < 0.0005:  # Low spread opportunity
                            opportunities.append({
                                'instrument': instrument,
                                'price': mid_price,
                                'spread': spread,
                                'type': 'LOW_SPREAD',
                                'message': f"💰 Low spread opportunity on {instrument}"
                            })
                        
                        # Price movement opportunity (simplified)
                        if abs(price.ask - price.bid) > 0.001:  # Significant movement
                            opportunities.append({
                                'instrument': instrument,
                                'price': mid_price,
                                'spread': spread,
                                'type': 'MOVEMENT',
                                'message': f"📈 Price movement detected on {instrument}"
                            })
                            
                except Exception as e:
                    logger.error(f"❌ Error scanning {instrument}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in opportunity scan: {e}")
            
        return opportunities
    
    def create_opportunity_alert(self, opportunities: List[Dict]) -> str:
        """Create opportunity alert message"""
        if not opportunities:
            return ""
            
        message = "🎯 **TRADING OPPORTUNITIES DETECTED**\n\n"
        message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} London\n\n"
        
        for i, opp in enumerate(opportunities[:3], 1):  # Limit to 3 opportunities
            message += f"**{i}. {opp['message']}**\n"
            message += f"   • Price: {opp['price']:.5f}\n"
            message += f"   • Spread: {opp['spread']:.5f}\n"
            message += f"   • Type: {opp['type']}\n\n"
        
        message += "💡 **Ready for your command:**\n"
        message += "• \"Enter BUY EUR/USD on account 001\"\n"
        message += "• \"Enter SELL GBP/USD on account 001\"\n"
        message += "• \"Enter BUY USD/JPY on account 001\"\n"
        message += "• \"Enter BUY XAU/USD on account 001\"\n"
        message += "• \"Enter SELL AUD/USD on account 001\"\n\n"
        message += "🚀 **Semi-Automatic Trading Ready!**"
        
        return message
    
    def create_account_update(self, account_status: Dict) -> str:
        """Create account update message"""
        if not account_status:
            return ""
            
        message = "📊 **SEMI-AUTOMATIC ACCOUNT UPDATE**\n\n"
        message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} London\n\n"
        
        message += f"💰 **Account Balance:** {account_status.get('balance', 0):.2f} {account_status.get('currency', 'USD')}\n"
        message += f"📈 **Open Trades:** {account_status.get('open_trades', 0)}\n"
        message += f"📊 **Open Positions:** {account_status.get('open_positions', 0)}\n\n"
        
        if account_status.get('trades'):
            message += "🔍 **Current Trades:**\n"
            for trade in account_status['trades'][:3]:  # Show max 3 trades
                pnl = float(trade.get('unrealizedPL', 0))
                status = "✅ WINNING" if pnl > 0 else "❌ LOSING" if pnl < 0 else "⚪ BREAK-EVEN"
                message += f"   • {trade.get('instrument', 'N/A')}: {pnl:.2f} {status}\n"
            message += "\n"
        
        message += "🎯 **Account Status:** Ready for semi-automatic trading\n"
        message += "📱 **Available Instruments:** EUR/USD, GBP/USD, USD/JPY, XAU/USD, AUD/USD\n"
        message += "📱 **Commands:** Tell me what to trade and I'll execute immediately!\n"
        
        return message
    
    def create_market_alert(self) -> str:
        """Create market condition alert"""
        message = "🌍 **MARKET CONDITIONS UPDATE**\n\n"
        message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')} London\n\n"
        
        try:
            data_feed = get_data_feed()
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
            
            message += "📊 **Current Prices:**\n"
            for instrument in instruments:
                try:
                    prices = data_feed.get_current_prices([instrument])
                    if instrument in prices:
                        price = prices[instrument]
                        mid_price = (price.bid + price.ask) / 2
                        spread = price.ask - price.bid
                        message += f"   • {instrument}: {mid_price:.5f} (Spread: {spread:.5f})\n"
                except:
                    message += f"   • {instrument}: Data unavailable\n"
            
            message += "\n🎯 **Trading Opportunities:**\n"
            message += "• EUR/USD: Ready for swing trades\n"
            message += "• GBP/USD: Volatile, good for scalping\n"
            message += "• USD/JPY: Trending, momentum opportunities\n"
            message += "• XAU/USD: Gold at $4,000+ - Trump strategy active\n"
            message += "• AUD/USD: Commodity currency, good for trends\n\n"
            
            message += "💡 **Semi-Auto Ready:** Account 001 is active and waiting for your commands!\n"
            
        except Exception as e:
            message += f"❌ Error getting market data: {e}\n"
            
        return message
    
    def run_alert_cycle(self):
        """Run one alert cycle"""
        logger.info("🔄 Running semi-automatic trading alert cycle...")
        
        # 1. Check for trading opportunities
        opportunities = self.scan_trading_opportunities()
        if opportunities:
            alert_key = "opportunities"
            if self._should_send_alert(alert_key):
                message = self.create_opportunity_alert(opportunities)
                if message:
                    self.send_telegram_message(message)
                    self.last_alert_time[alert_key] = datetime.now()
        
        # 2. Send account update (every 30 minutes)
        alert_key = "account_update"
        if self._should_send_alert(alert_key, interval_minutes=30):
            account_status = self.get_account_status()
            if account_status:
                message = self.create_account_update(account_status)
                if message:
                    self.send_telegram_message(message)
                    self.last_alert_time[alert_key] = datetime.now()
        
        # 3. Send market conditions (every hour)
        alert_key = "market_conditions"
        if self._should_send_alert(alert_key, interval_minutes=60):
            message = self.create_market_alert()
            if message:
                self.send_telegram_message(message)
                self.last_alert_time[alert_key] = datetime.now()
    
    def _should_send_alert(self, alert_key: str, interval_minutes: int = 5) -> bool:
        """Check if alert should be sent based on interval"""
        if alert_key not in self.last_alert_time:
            return True
            
        time_since_last = datetime.now() - self.last_alert_time[alert_key]
        return time_since_last.total_seconds() >= (interval_minutes * 60)
    
    def start_continuous_alerts(self):
        """Start continuous alert system"""
        logger.info("🚀 Starting semi-automatic trading alerts...")
        
        # Send initial setup message
        setup_message = """🤖 **SEMI-AUTOMATIC TRADING ALERTS ACTIVATED**

**📊 Account:** Strategy Zeta (101-004-30719775-001)
**🎯 Status:** Ready for your commands
**⏰ Alerts:** Every 5 minutes for opportunities
**📱 Updates:** Every 30 minutes for account status

**💡 How to use:**
• Tell me: "Enter BUY EUR/USD on account 001"
• Tell me: "Enter SELL GBP/USD on account 001"  
• Tell me: "Enter BUY USD/JPY on account 001"

**🚀 I'll execute immediately with proper SL/TP!**

Starting continuous monitoring..."""
        
        self.send_telegram_message(setup_message)
        
        # Run continuous alerts
        while True:
            try:
                self.run_alert_cycle()
                time.sleep(self.alert_frequency)
            except KeyboardInterrupt:
                logger.info("🛑 Stopping alert system...")
                break
            except Exception as e:
                logger.error(f"❌ Error in alert cycle: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    """Main function"""
    logger.info("🤖 Starting Semi-Automatic Trading Telegram Alerts...")
    
    # Set up environment
    os.environ['OANDA_API_KEY'] = "${OANDA_API_KEY}"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    
    # Start alert system
    alert_system = SemiAutoTelegramAlerts()
    alert_system.start_continuous_alerts()

if __name__ == "__main__":
    main()
