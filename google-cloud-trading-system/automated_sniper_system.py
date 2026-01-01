#!/usr/bin/env python3
from src.core.settings import settings
"""
Automated Sniper System - Auto-Entry on Economic Events
=====================================================

Real-time monitoring system that automatically enters trades when:
1. Economic events occur
2. Market conditions are optimal
3. Quality thresholds are met
4. Minimum $1,000 profit potential
"""

import os
import requests
import numpy as np
import time
import threading
from datetime import datetime, timedelta
import pytz
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OANDA config - from environment variables
OANDA_API_KEY = settings.oanda_api_key
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_BASE_URL = f"https://api-fx{OANDA_ENV}.oanda.com" if OANDA_ENV == "practice" else "https://api-fxtrade.oanda.com"

# Fail-closed: require API key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable is required")

headers = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

BOT_TOKEN = settings.telegram_bot_token
CHAT_ID = settings.telegram_chat_id

# Fail-closed: require Telegram credentials
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

class AutomatedSniperSystem:
    """Automated sniper system for real-time trade execution"""
    
    def __init__(self):
        self.running = False
        self.account_id = '101-004-30719775-008'
        self.min_profit_target = 1000  # $1,000 minimum profit
        self.quality_threshold = 70  # Minimum quality score
        self.max_positions = 3  # Maximum concurrent positions
        
        # Economic events schedule (London time)
        self.events = [
            {"time": "09:30", "currency": "GBP", "event": "UK CPI", "impact": "HIGH"},
            {"time": "10:00", "currency": "EUR", "event": "German ZEW", "impact": "MEDIUM"},
            {"time": "13:30", "currency": "USD", "event": "Building Permits", "impact": "MEDIUM"},
            {"time": "14:00", "currency": "USD", "event": "Housing Starts", "impact": "MEDIUM"},
            {"time": "15:00", "currency": "USD", "event": "Consumer Confidence", "impact": "HIGH"},
            {"time": "16:00", "currency": "USD", "event": "Fed Speech", "impact": "HIGH"},
        ]
        
        # Target instruments
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD']
        
    def send_telegram(self, message):
        """Send Telegram alert"""
        try:
            url = f'https://api.telegram.org/bot{self.BOT_TOKEN}/sendMessage'
            data = {'chat_id': self.CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.error(f"Telegram error: {e}")
    
    def get_current_price(self, instrument):
        """Get current price"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pricing"
            params = {'instruments': instrument}
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'prices' in data and len(data['prices']) > 0:
                    price_data = data['prices'][0]
                    return {
                        'bid': float(price_data['bids'][0]['price']),
                        'ask': float(price_data['asks'][0]['price']),
                        'mid': (float(price_data['bids'][0]['price']) + float(price_data['asks'][0]['price'])) / 2,
                        'spread': float(price_data['asks'][0]['price']) - float(price_data['bids'][0]['price'])
                    }
        except Exception as e:
            logger.error(f"Price error for {instrument}: {e}")
        return None
    
    def get_candles(self, instrument, count=20):
        """Get recent candles"""
        try:
            url = f"{OANDA_BASE_URL}/v3/instruments/{instrument}/candles"
            params = {'count': count, 'granularity': 'M5', 'price': 'M'}
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                candles = data.get('candles', [])
                return [float(c['mid']['c']) for c in candles if c.get('complete')]
        except Exception as e:
            logger.error(f"Candles error for {instrument}: {e}")
        return None
    
    def analyze_opportunity(self, instrument):
        """Analyze sniper opportunity"""
        try:
            price_data = self.get_current_prices([instrument]).get(instrument)
            candles = self.get_candles(instrument, 20)
            
            if not price_data or not candles or len(candles) < 10:
                return None
            
            # Calculate quality score
            quality_score = 0
            reasons = []
            
            # Spread analysis
            spread = price_data['spread']
            if spread < 0.0001:
                quality_score += 25
                reasons.append("Tight spread")
            elif spread < 0.0002:
                quality_score += 15
                reasons.append("Good spread")
            
            # Trend analysis
            if len(candles) >= 10:
                recent_prices = candles[-10:]
                trend_direction = 1 if recent_prices[-1] > recent_prices[0] else -1
                trend_strength = abs(recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
                
                if trend_strength > 0.3:
                    quality_score += 20
                    reasons.append(f"Strong trend ({trend_strength:.2f}%)")
                elif trend_strength > 0.1:
                    quality_score += 10
                    reasons.append(f"Moderate trend ({trend_strength:.2f}%)")
                
                # Volatility analysis
                volatility = np.std(recent_prices) / np.mean(recent_prices) * 100
                if volatility > 0.5:
                    quality_score += 15
                    reasons.append("High volatility")
                elif volatility > 0.3:
                    quality_score += 10
                    reasons.append("Moderate volatility")
            
            # Event proximity bonus
            london_time = datetime.now(pytz.timezone('Europe/London'))
            current_hour = london_time.hour
            current_minute = london_time.minute
            
            # Check for event proximity
            for event in self.events:
                event_hour = int(event['time'].split(':')[0])
                event_minute = int(event['time'].split(':')[1])
                
                # Within 30 minutes of event
                if (current_hour == event_hour and abs(current_minute - event_minute) <= 30) or \
                   (current_hour == event_hour + 1 and current_minute <= 30):
                    
                    if event['currency'] in instrument:
                        quality_score += 30
                        reasons.append(f"{event['event']} proximity")
                    elif event['impact'] == 'HIGH':
                        quality_score += 15
                        reasons.append("High impact event")
            
            return {
                'instrument': instrument,
                'quality': quality_score,
                'price': price_data['mid'],
                'spread': spread,
                'reasons': reasons,
                'trend_direction': trend_direction if 'trend_direction' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"Analysis error for {instrument}: {e}")
            return None
    
    def calculate_trade_size(self, instrument, quality_score):
        """Calculate optimal trade size for $1,000+ profit"""
        # Base size calculation for $1,000 profit
        # For EUR/USD: 1 pip = $1 per 10,000 units
        # Need 100 pips for $1,000 profit with 100,000 units
        
        if quality_score >= 90:
            return 200000  # 20 standard lots - $2,000+ profit potential
        elif quality_score >= 80:
            return 150000  # 15 standard lots - $1,500+ profit potential
        elif quality_score >= 70:
            return 100000  # 10 standard lots - $1,000+ profit potential
        else:
            return 0  # Below threshold
    
    def execute_sniper_trade(self, opportunity):
        """Execute sniper trade automatically"""
        try:
            instrument = opportunity['instrument']
            quality = opportunity['quality']
            price = opportunity['price']
            trend_direction = opportunity['trend_direction']
            
            # Calculate trade size
            units = self.calculate_trade_size(instrument, quality)
            if units == 0:
                return False
            
            # Determine trade direction
            side = "BUY" if trend_direction > 0 else "SELL"
            units = units if side == "BUY" else -units
            
            # Calculate stop loss and take profit
            pip_value = 0.0001
            stop_loss_pips = 50
            take_profit_pips = 100  # 2:1 R:R
            
            if side == "BUY":
                stop_loss = price - (stop_loss_pips * pip_value)
                take_profit = price + (take_profit_pips * pip_value)
            else:
                stop_loss = price + (stop_loss_pips * pip_value)
                take_profit = price - (take_profit_pips * pip_value)
            
            # Execute trade
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "stopLossOnFill": {"price": str(stop_loss)},
                    "takeProfitOnFill": {"price": str(take_profit)}
                }
            }
            
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/orders"
            response = requests.post(url, headers=headers, json=order_data, timeout=10)
            
            if response.status_code == 201:
                order = response.json().get('orderCreateTransaction', {})
                
                # Send success alert
                message = f"""🎯 **SNIPER TRADE EXECUTED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💱 **Instrument:** {instrument}
📊 **Units:** {abs(units):,} ({side})
💰 **Entry:** {price:.5f}
🛡️ **Stop Loss:** {stop_loss:.5f}
🎯 **Take Profit:** {take_profit:.5f}
📈 **Quality Score:** {quality}/100
💵 **Profit Potential:** ${(abs(units)/10000)*take_profit_pips:,.0f}

**Reasons:** {', '.join(opportunity['reasons'])}

**AUTOMATED ENTRY SUCCESSFUL!** ✅"""
                
                self.send_telegram(message)
                logger.info(f"SNIPER TRADE EXECUTED: {instrument} {side} {abs(units)} units")
                return True
            else:
                logger.error(f"Trade execution failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return False
    
    def check_existing_positions(self):
        """Check current positions"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/openTrades"
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return len(data.get('trades', []))
        except Exception as e:
            logger.error(f"Position check error: {e}")
        return 0
    
    def run_sniper_scan(self):
        """Run one sniper scan cycle"""
        try:
            # Check position limit
            current_positions = self.check_existing_positions()
            if current_positions >= self.max_positions:
                logger.info(f"Position limit reached: {current_positions}/{self.max_positions}")
                return
            
            # Scan for opportunities
            opportunities = []
            for instrument in self.instruments:
                opportunity = self.analyze_opportunity(instrument)
                if opportunity and opportunity['quality'] >= self.quality_threshold:
                    opportunities.append(opportunity)
            
            # Sort by quality and execute best opportunity
            if opportunities:
                opportunities.sort(key=lambda x: x['quality'], reverse=True)
                best_opportunity = opportunities[0]
                
                logger.info(f"SNIPER OPPORTUNITY: {best_opportunity['instrument']} Quality: {best_opportunity['quality']}")
                
                # Execute trade
                success = self.execute_sniper_trade(best_opportunity)
                if success:
                    logger.info("SNIPER TRADE EXECUTED SUCCESSFULLY!")
                else:
                    logger.error("SNIPER TRADE EXECUTION FAILED!")
            else:
                logger.info("No sniper opportunities found")
                
        except Exception as e:
            logger.error(f"Sniper scan error: {e}")
    
    def start_sniper_system(self):
        """Start automated sniper system"""
        self.running = True
        logger.info("🎯 AUTOMATED SNIPER SYSTEM STARTED")
        
        # Send startup message
        self.send_telegram("""🎯 **AUTOMATED SNIPER SYSTEM ACTIVATED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **System Status:** ACTIVE
🎯 **Quality Threshold:** 70/100
💰 **Min Profit:** $1,000+
📊 **Max Positions:** 3
🔄 **Scan Frequency:** 30 seconds

**MONITORING FOR OPPORTUNITIES...**""")
        
        while self.running:
            try:
                self.run_sniper_scan()
                time.sleep(30)  # Scan every 30 seconds
            except KeyboardInterrupt:
                logger.info("Sniper system stopped by user")
                break
            except Exception as e:
                logger.error(f"Sniper system error: {e}")
                time.sleep(60)  # Wait 1 minute on error
        
        logger.info("🎯 AUTOMATED SNIPER SYSTEM STOPPED")
    
    def stop_sniper_system(self):
        """Stop automated sniper system"""
        self.running = False
        self.send_telegram("🎯 **SNIPER SYSTEM STOPPED**")

if __name__ == "__main__":
    sniper = AutomatedSniperSystem()
    try:
        sniper.start_sniper_system()
    except KeyboardInterrupt:
        sniper.stop_sniper_system()
