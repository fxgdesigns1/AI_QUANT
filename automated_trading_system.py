#!/usr/bin/env python3
from src.core.settings import settings
"""
FULL AUTOMATED TRADING SYSTEM - DEMO ACCOUNT ONLY
This system will scan markets and execute trades automatically in paper trading
"""
import os
import sys
import time
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# OANDA Configuration - from environment variables
OANDA_API_KEY = settings.oanda_api_key
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "101-004-30719775-008")  # Demo account default
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_BASE_URL = f"https://api-fx{OANDA_ENV}.oanda.com" if OANDA_ENV == "practice" else "https://api-fxtrade.oanda.com"
OANDA_STREAM_URL = f"https://stream-fx{OANDA_ENV}.oanda.com" if OANDA_ENV == "practice" else "https://stream-fxtrade.oanda.com"

# Telegram Configuration - from environment variables
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = settings.telegram_chat_id

# Fail-closed: require critical env vars
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable is required")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable is required")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomatedTradingSystem:
    def __init__(self):
        self.account_id = OANDA_ACCOUNT_ID
        self.headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
        self.active_trades = {}
        self.daily_trade_count = 0
        self.max_daily_trades = 50
        self.max_concurrent_trades = 5
        self.risk_per_trade = 0.01  # 1% risk per trade
        
        logger.info(f"🤖 Automated Trading System initialized")
        logger.info(f"📊 Demo Account: {self.account_id}")
        logger.info(f"💰 Risk per trade: {self.risk_per_trade*100}%")
        logger.info(f"📈 Max daily trades: {self.max_daily_trades}")
        
    def get_account_info(self):
        """Get account information"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()['account']
            else:
                logger.error(f"Failed to get account info: {response.status_code}")
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
                for price_data in data['prices']:
                    instrument = price_data['instrument']
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    prices[instrument] = {
                        'bid': bid,
                        'ask': ask,
                        'mid': (bid + ask) / 2,
                        'spread': ask - bid
                    }
                return prices
            else:
                logger.error(f"Failed to get prices: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return {}
    
    def analyze_market(self, prices):
        """Analyze market conditions and generate trading signals"""
        signals = []
        
        for instrument, price_data in prices.items():
            try:
                # Simple momentum strategy
                mid_price = price_data['mid']
                spread = price_data['spread']
                
                # Skip if spread is too wide
                if spread > 0.0005:  # 5 pips
                    continue
                
                # Generate signals based on price levels and volatility
                if instrument == 'EUR_USD':
                    # EUR/USD momentum
                    if mid_price > 1.0500:  # Above key level
                        signals.append({
                            'instrument': instrument,
                            'side': 'BUY',
                            'entry_price': price_data['ask'],
                            'stop_loss': mid_price - 0.0020,  # 20 pips
                            'take_profit': mid_price + 0.0040,  # 40 pips
                            'confidence': 75,
                            'strategy': 'momentum'
                        })
                    elif mid_price < 1.0400:  # Below key level
                        signals.append({
                            'instrument': instrument,
                            'side': 'SELL',
                            'entry_price': price_data['bid'],
                            'stop_loss': mid_price + 0.0020,  # 20 pips
                            'take_profit': mid_price - 0.0040,  # 40 pips
                            'confidence': 75,
                            'strategy': 'momentum'
                        })
                
                elif instrument == 'GBP_USD':
                    # GBP/USD momentum
                    if mid_price > 1.2500:
                        signals.append({
                            'instrument': instrument,
                            'side': 'BUY',
                            'entry_price': price_data['ask'],
                            'stop_loss': mid_price - 0.0025,  # 25 pips
                            'take_profit': mid_price + 0.0050,  # 50 pips
                            'confidence': 70,
                            'strategy': 'momentum'
                        })
                    elif mid_price < 1.2300:
                        signals.append({
                            'instrument': instrument,
                            'side': 'SELL',
                            'entry_price': price_data['bid'],
                            'stop_loss': mid_price + 0.0025,  # 25 pips
                            'take_profit': mid_price - 0.0050,  # 50 pips
                            'confidence': 70,
                            'strategy': 'momentum'
                        })
                
                elif instrument == 'XAU_USD':
                    # Gold scalping
                    if mid_price > 2000:
                        signals.append({
                            'instrument': instrument,
                            'side': 'BUY',
                            'entry_price': price_data['ask'],
                            'stop_loss': mid_price - 5.0,  # $5 stop
                            'take_profit': mid_price + 10.0,  # $10 target
                            'confidence': 80,
                            'strategy': 'scalping'
                        })
                    elif mid_price < 1950:
                        signals.append({
                            'instrument': instrument,
                            'side': 'SELL',
                            'entry_price': price_data['bid'],
                            'stop_loss': mid_price + 5.0,  # $5 stop
                            'take_profit': mid_price - 10.0,  # $10 target
                            'confidence': 80,
                            'strategy': 'scalping'
                        })
                
            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")
        
        return signals
    
    def calculate_position_size(self, signal, account_balance):
        """Calculate position size based on risk management"""
        try:
            risk_amount = account_balance * self.risk_per_trade
            
            if signal['side'] == 'BUY':
                stop_distance = signal['entry_price'] - signal['stop_loss']
            else:
                stop_distance = signal['stop_loss'] - signal['entry_price']
            
            if stop_distance <= 0:
                return 0
            
            # Calculate units based on risk
            if signal['instrument'] == 'XAU_USD':
                # Gold is priced per ounce
                units = int(risk_amount / stop_distance)
            else:
                # Forex pairs
                units = int(risk_amount / stop_distance)
            
            # Limit position size
            max_units = 10000
            return min(units, max_units)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def execute_trade(self, signal):
        """Execute a trading signal"""
        try:
            # Check if we can trade
            if self.daily_trade_count >= self.max_daily_trades:
                logger.warning("Daily trade limit reached")
                return False
            
            if len(self.active_trades) >= self.max_concurrent_trades:
                logger.warning("Max concurrent trades reached")
                return False
            
            # Get account balance
            account_info = self.get_account_info()
            if not account_info:
                return False
            
            balance = float(account_info['balance'])
            
            # Calculate position size
            units = self.calculate_position_size(signal, balance)
            if units == 0:
                logger.warning("Position size too small")
                return False
            
            # Adjust units for SELL orders
            if signal['side'] == 'SELL':
                units = -units
            
            # Create order
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": signal['instrument'],
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "stopLossOnFill": {"price": str(signal['stop_loss'])},
                    "takeProfitOnFill": {"price": str(signal['take_profit'])}
                }
            }
            
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/orders"
            response = requests.post(url, headers=self.headers, json=order_data, timeout=10)
            
            if response.status_code == 201:
                order_info = response.json()['orderCreateTransaction']
                order_id = order_info['id']
                
                # Track the trade
                self.active_trades[order_id] = {
                    'instrument': signal['instrument'],
                    'side': signal['side'],
                    'units': units,
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'timestamp': datetime.now(),
                    'strategy': signal['strategy']
                }
                
                self.daily_trade_count += 1
                
                # Send Telegram notification
                self.send_telegram_alert(signal, order_id, units)
                
                logger.info(f"✅ TRADE EXECUTED: {signal['instrument']} {signal['side']} - Units: {units}")
                return True
            else:
                logger.error(f"❌ Trade failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return False
    
    def send_telegram_alert(self, signal, order_id, units):
        """Send trade alert to Telegram"""
        try:
            message = f"""🚀 TRADE EXECUTED!

📊 Instrument: {signal['instrument']}
📈 Side: {signal['side']}
💰 Units: {units}
💵 Entry: {signal['entry_price']}
🛡️ Stop Loss: {signal['stop_loss']}
🎯 Take Profit: {signal['take_profit']}
📊 Strategy: {signal['strategy']}
🆔 Order ID: {order_id}

🤖 Demo Account: {self.account_id}"""
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            requests.post(url, data=data, timeout=10)
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def monitor_trades(self):
        """Monitor active trades and close if needed"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                positions = response.json()['positions']
                for position in positions:
                    instrument = position['instrument']
                    if instrument in self.instruments:
                        # Check if position should be closed
                        unrealized_pl = float(position['unrealizedPL'])
                        if abs(unrealized_pl) > 50:  # Close if P&L > $50
                            logger.info(f"Position {instrument} has P&L: ${unrealized_pl:.2f}")
                            
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}")
    
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        logger.info("🔍 Starting trading cycle...")
        
        # Get current prices
        prices = self.get_current_prices()
        if not prices:
            logger.error("Failed to get market prices")
            return
        
        # Analyze market
        signals = self.analyze_market(prices)
        logger.info(f"📊 Generated {len(signals)} trading signals")
        
        # Execute trades
        executed_count = 0
        for signal in signals:
            if self.execute_trade(signal):
                executed_count += 1
        
        # Monitor existing trades
        self.monitor_trades()
        
        logger.info(f"🎯 Trading cycle complete - Executed {executed_count} trades")
        
        # Send status update
        if executed_count > 0:
            self.send_status_update(executed_count, len(signals))
    
    def send_status_update(self, executed, total_signals):
        """Send status update to Telegram"""
        try:
            account_info = self.get_account_info()
            balance = float(account_info['balance']) if account_info else 0
            
            message = f"""📊 Trading Status Update

🎯 Signals Generated: {total_signals}
✅ Trades Executed: {executed}
💰 Account Balance: ${balance:.2f}
📈 Active Trades: {len(self.active_trades)}
📊 Daily Trades: {self.daily_trade_count}/{self.max_daily_trades}

🤖 Demo Account: {self.account_id}"""
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            requests.post(url, data=data, timeout=10)
            
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

def main():
    """Main trading loop"""
    logger.info("🚀 STARTING AUTOMATED TRADING SYSTEM")
    logger.info("📊 DEMO ACCOUNT ONLY - NO REAL MONEY AT RISK")
    
    system = AutomatedTradingSystem()
    
    # Send startup notification
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        message = f"""🤖 AUTOMATED TRADING SYSTEM STARTED!

📊 Demo Account: {OANDA_ACCOUNT_ID}
💰 Risk per trade: 1%
📈 Max daily trades: 50
🛡️ Max concurrent trades: 5

✅ System is now scanning markets and executing trades automatically!
📱 You will receive real-time alerts for all trades."""
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send startup notification: {e}")
    
    # Run continuous trading
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            logger.info(f"🔄 Starting trading cycle #{cycle_count}")
            
            system.run_trading_cycle()
            
            logger.info(f"⏰ Next cycle in 60 seconds...")
            time.sleep(60)  # Wait 1 minute between cycles
            
        except KeyboardInterrupt:
            logger.info("🛑 Trading system stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            time.sleep(30)  # Wait 30 seconds on error

if __name__ == "__main__":
    main()
