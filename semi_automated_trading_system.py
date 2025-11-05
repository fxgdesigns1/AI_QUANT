#!/usr/bin/env python3
"""
SEMI-AUTOMATED TRADING SYSTEM
Scans markets, generates signals, but requires manual approval via Telegram
"""
import os
import sys
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Fix Python path
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.12/site-packages')

# OANDA Configuration
OANDA_API_KEY = "REMOVED_SECRET"
OANDA_ACCOUNT_ID = "101-004-30719775-008"  # Demo account
OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemiAutomatedTradingSystem:
    def __init__(self):
        self.account_id = OANDA_ACCOUNT_ID
        self.headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
        self.pending_opportunities = []
        self.approved_trades = []
        self.scan_interval = 300  # 5 minutes
        
        logger.info(f"🤖 Semi-Automated Trading System initialized")
        logger.info(f"📊 Demo Account: {self.account_id}")
        
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured - skipping notification")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def get_account_info(self):
        """Get account information"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()['account']
            return None
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_current_prices(self):
        """Get current prices for all instruments"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pricing"
            params = {'instruments': ','.join(self.instruments)}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                for price_data in data.get('prices', []):
                    instrument = price_data.get('instrument')
                    if instrument:
                        bids = price_data.get('bids', [])
                        asks = price_data.get('asks', [])
                        if bids and asks:
                            bid = float(bids[0].get('price', 0))
                            ask = float(asks[0].get('price', 0))
                            prices[instrument] = {
                                'bid': bid,
                                'ask': ask,
                                'mid': (bid + ask) / 2,
                                'spread': ask - bid
                            }
                return prices
            return {}
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return {}
    
    def analyze_opportunities(self, prices):
        """Analyze market and generate trading opportunities"""
        opportunities = []
        
        for instrument, price_data in prices.items():
            try:
                mid_price = price_data['mid']
                spread = price_data['spread']
                
                # Simple momentum-based signals
                if instrument in ['EUR_USD', 'GBP_USD']:
                    # Check for breakout opportunities
                    if mid_price > 1.0500:  # EUR/USD above key level
                        opportunities.append({
                            'instrument': instrument,
                            'side': 'BUY',
                            'entry_price': price_data['ask'],
                            'stop_loss': mid_price - 0.0020,
                            'take_profit': mid_price + 0.0040,
                            'confidence': 70,
                            'strategy': 'momentum_breakout',
                            'reason': f'Price above key level: {mid_price:.5f}'
                        })
                elif instrument == 'XAU_USD':
                    # Gold swing trading
                    if mid_price > 2000:
                        opportunities.append({
                            'instrument': instrument,
                            'side': 'BUY',
                            'entry_price': price_data['ask'],
                            'stop_loss': mid_price - 10.0,
                            'take_profit': mid_price + 20.0,
                            'confidence': 75,
                            'strategy': 'swing_trading',
                            'reason': f'Gold above $2000: ${mid_price:.2f}'
                        })
            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")
        
        return opportunities
    
    def send_opportunity_alert(self, opportunity):
        """Send opportunity alert to Telegram for approval"""
        message = f"""📊 TRADING OPPORTUNITY

📈 Instrument: {opportunity['instrument']}
📊 Side: {opportunity['side']}
💰 Entry: {opportunity['entry_price']:.5f}
🛡️ Stop Loss: {opportunity['stop_loss']:.5f}
🎯 Take Profit: {opportunity['take_profit']:.5f}
📈 Confidence: {opportunity['confidence']}%
📋 Strategy: {opportunity['strategy']}
💡 Reason: {opportunity['reason']}

⏰ This opportunity will expire in 5 minutes.
Reply with /approve_{opportunity['instrument']}_{opportunity['side']} to execute."""
        
        self.send_telegram_message(message)
        self.pending_opportunities.append({
            **opportunity,
            'timestamp': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=5)
        })
    
    def scan_and_alert(self):
        """Scan markets and send alerts"""
        logger.info("🔍 Scanning markets for opportunities...")
        
        prices = self.get_current_prices()
        if not prices:
            logger.warning("No price data available")
            return
        
        opportunities = self.analyze_opportunities(prices)
        
        if opportunities:
            logger.info(f"📊 Found {len(opportunities)} opportunities")
            for opp in opportunities[:3]:  # Limit to 3 per scan
                self.send_opportunity_alert(opp)
        else:
            logger.info("No opportunities found")
    
    def run(self):
        """Main loop"""
        logger.info("🚀 Starting Semi-Automated Trading System")
        self.send_telegram_message("🤖 Semi-Automated Trading System Started\n\nI will scan markets every 5 minutes and send you trading opportunities for approval.")
        
        while True:
            try:
                self.scan_and_alert()
                logger.info(f"⏰ Next scan in {self.scan_interval} seconds...")
                time.sleep(self.scan_interval)
            except KeyboardInterrupt:
                logger.info("🛑 System stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ System error: {e}")
                time.sleep(60)

def main():
    system = SemiAutomatedTradingSystem()
    system.run()

if __name__ == "__main__":
    main()
