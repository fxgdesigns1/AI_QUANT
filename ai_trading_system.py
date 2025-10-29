#!/usr/bin/env python3
"""
AI-POWERED TRADING SYSTEM WITH TELEGRAM COMMAND INTERFACE
This system can read Telegram messages and execute commands
"""
import os
import sys
import time
import logging
import requests
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any

# OANDA Configuration
OANDA_API_KEY = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
OANDA_ACCOUNT_ID = "101-004-30719775-008"  # Demo account
OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
TELEGRAM_CHAT_ID = "6100678501"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from news_manager import NewsManager
except Exception:
    NewsManager = None  # type: ignore

class AITradingSystem:
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
        self.max_per_symbol = 2  # diversification cap per instrument
        self.reserve_slots_for_diversification = 2  # keep slots for other symbols
        self.prev_mid: Dict[str, float] = {}
        self.per_symbol_cap = {'XAU_USD': 1}
        self.instrument_spread_limits = {
            'EUR_USD': 0.00025,
            'GBP_USD': 0.00030,
            'AUD_USD': 0.00030,
            'USD_JPY': 0.025,
            'XAU_USD': 1.00
        }
        self.last_update_id = 0
        self.trading_enabled = True
        self.command_history = []
        self.news_halt_until = None  # UTC timestamp until which new entries are halted
        self.news = NewsManager() if NewsManager else None
        self.news_mode = 'normal'  # off|lite|normal|strict
        self.sentiment_threshold = -0.4
        self.surprise_threshold = 0.5
        self.throttle_until = None
        self.base_risk = self.risk_per_trade
        
        logger.info(f"🤖 AI Trading System initialized")
        logger.info(f"📊 Demo Account: {self.account_id}")
        logger.info(f"💰 Risk per trade: {self.risk_per_trade*100}%")
        logger.info(f"📱 Telegram commands: ENABLED")
        
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def get_telegram_updates(self):
        """Get new messages from Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {'offset': self.last_update_id + 1, 'timeout': 10}
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data['ok'] and data['result']:
                    return data['result']
            return []
        except Exception as e:
            logger.error(f"Error getting Telegram updates: {e}")
            return []
    
    def process_telegram_command(self, message_text, user_name):
        """Process commands from Telegram"""
        command = message_text.lower().strip()
        self.command_history.append({
            'command': command,
            'user': user_name,
            'timestamp': datetime.now()
        })
        
        logger.info(f"📱 Received command from {user_name}: {command}")
        
        if command == '/status':
            return self.get_system_status()
        
        elif command == '/balance':
            return self.get_account_balance()
        
        elif command == '/positions':
            return self.get_open_positions()
        
        elif command == '/trades':
            return self.get_recent_trades()
        
        elif command == '/start_trading':
            self.trading_enabled = True
            return "✅ Trading ENABLED - System will scan and execute trades"
        
        elif command == '/stop_trading':
            self.trading_enabled = False
            return "🛑 Trading DISABLED - System will monitor only"
        
        elif command == '/help':
            return self.get_help_menu()
        
        elif command.startswith('/risk '):
            try:
                risk_value = float(command.split()[1])
                if 0.001 <= risk_value <= 0.05:  # 0.1% to 5%
                    self.risk_per_trade = risk_value
                    return f"✅ Risk per trade updated to {risk_value*100:.1f}%"
                else:
                    return "❌ Risk must be between 0.1% and 5%"
            except:
                return "❌ Invalid risk value. Use: /risk 0.01 (for 1%)"
        
        elif command.startswith('/trade '):
            try:
                parts = command.split()
                if len(parts) >= 3:
                    instrument = parts[1].upper()
                    side = parts[2].upper()
                    return self.execute_manual_trade(instrument, side)
                else:
                    return "❌ Use: /trade EUR_USD BUY"
            except Exception as e:
                return f"❌ Trade command error: {e}"
        
        elif command == '/market':
            return self.get_market_analysis()
        
        elif command == '/performance':
            return self.get_performance_summary()
        
        elif command == '/emergency_stop':
            self.trading_enabled = False
            return "🚨 EMERGENCY STOP ACTIVATED - All trading disabled"
        
        elif command.startswith('/halt '):
            # Halt new entries for N minutes (news buffer)
            try:
                mins = int(command.split()[1])
                self.news_halt_until = datetime.utcnow() + timedelta(minutes=mins)
                return f"🛑 News halt enabled for {mins} minutes (no new entries)"
            except Exception:
                return "❌ Invalid command. Use: /halt 30"

        elif command.startswith('/news_mode '):
            mode = command.split()[1].lower()
            if mode in ('off','lite','normal','strict'):
                self.news_mode = mode
                return f"✅ news_mode set to {mode}"
            return "❌ Use: /news_mode off|lite|normal|strict"

        elif command.startswith('/sentiment_threshold '):
            try:
                v = float(command.split()[1])
                self.sentiment_threshold = v
                return f"✅ sentiment_threshold set to {v:.2f}"
            except Exception:
                return "❌ Use: /sentiment_threshold -0.40"

        elif command.startswith('/surprise_threshold '):
            try:
                v = float(command.split()[1])
                self.surprise_threshold = v
                return f"✅ surprise_threshold set to {v:.2f}"
            except Exception:
                return "❌ Use: /surprise_threshold 0.50"

        elif command in ('/news','/brief','/today'):
            return self.get_detailed_news_summary()
        
        else:
            return f"❓ Unknown command: {command}\nType /help for available commands"
    
    def get_system_status(self):
        """Get current system status"""
        try:
            account_info = self.get_account_info()
            balance = float(account_info['balance']) if account_info else 0
            
            status = f"""🤖 AI TRADING SYSTEM STATUS

📊 Account: {self.account_id}
💰 Balance: ${balance:.2f}
📈 Daily Trades: {self.daily_trade_count}/{self.max_daily_trades}
🛡️ Active Trades: {len(self.active_trades)}
⚙️ Trading: {'ENABLED' if self.trading_enabled else 'DISABLED'}
💰 Risk per Trade: {self.risk_per_trade*100:.1f}%
🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}

📱 Commands: Type /help for full list"""
            
            return status
        except Exception as e:
            return f"❌ Error getting status: {e}"
    
    def get_account_balance(self):
        """Get account balance"""
        try:
            account_info = self.get_account_info()
            if account_info:
                balance = float(account_info['balance'])
                unrealized_pl = float(account_info['unrealizedPL'])
                return f"""💰 ACCOUNT BALANCE

💵 Balance: ${balance:.2f}
📈 Unrealized P&L: ${unrealized_pl:.2f}
📊 Total Equity: ${balance + unrealized_pl:.2f}
🏦 Currency: {account_info['currency']}"""
            else:
                return "❌ Failed to get account balance"
        except Exception as e:
            return f"❌ Error getting balance: {e}"
    
    def get_open_positions(self):
        """Get open positions"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                positions = data['positions']
                
                if not positions:
                    return "📊 No open positions"
                
                result = "📊 OPEN POSITIONS\n\n"
                for pos in positions:
                    if float(pos['long']['units']) != 0 or float(pos['short']['units']) != 0:
                        instrument = pos['instrument']
                        long_units = float(pos['long']['units'])
                        short_units = float(pos['short']['units'])
                        unrealized_pl = float(pos['unrealizedPL'])
                        
                        if long_units > 0:
                            result += f"📈 {instrument} LONG: {long_units} units\n"
                        if short_units > 0:
                            result += f"📉 {instrument} SHORT: {short_units} units\n"
                        result += f"💰 P&L: ${unrealized_pl:.2f}\n\n"
                
                return result
            else:
                return "❌ Failed to get positions"
        except Exception as e:
            return f"❌ Error getting positions: {e}"
    
    def get_recent_trades(self):
        """Get recent trades"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/transactions"
            params = {'count': 10}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                transactions = data['transactions']
                
                if not transactions:
                    return "📊 No recent trades"
                
                result = "📊 RECENT TRADES\n\n"
                for tx in transactions[:5]:  # Show last 5
                    if tx['type'] == 'ORDER_FILL':
                        instrument = tx['instrument']
                        units = tx['units']
                        price = tx['price']
                        pl = tx.get('pl', '0')
                        result += f"📈 {instrument}: {units} units @ {price}\n"
                        result += f"💰 P&L: ${pl}\n\n"
                
                return result
            else:
                return "❌ Failed to get trades"
        except Exception as e:
            return f"❌ Error getting trades: {e}"
    
    def get_help_menu(self):
        """Get help menu"""
        return """🤖 AI TRADING SYSTEM COMMANDS

📊 STATUS & INFO:
/status - System status
/balance - Account balance
/positions - Open positions
/trades - Recent trades
/performance - Performance summary
/market - Market analysis

⚙️ TRADING CONTROL:
/start_trading - Enable trading
/stop_trading - Disable trading
/emergency_stop - Emergency stop all trading

💰 RISK MANAGEMENT:
/risk 0.01 - Set risk per trade (1%)

🎯 MANUAL TRADING:
/trade EUR_USD BUY - Execute manual trade
/trade GBP_USD SELL - Execute manual trade

❓ HELP:
/help - Show this menu

💡 The AI will respond to all commands and provide real-time updates!"""
    
    def get_market_analysis(self):
        """Get current market analysis"""
        try:
            prices = self.get_current_prices()
            if not prices:
                return "❌ Failed to get market data"
            
            analysis = "📊 MARKET ANALYSIS\n\n"
            for instrument, price_data in prices.items():
                mid_price = price_data['mid']
                spread = price_data['spread']
                
                # Simple analysis
                if instrument == 'EUR_USD':
                    if mid_price > 1.0500:
                        trend = "📈 BULLISH"
                    elif mid_price < 1.0400:
                        trend = "📉 BEARISH"
                    else:
                        trend = "➡️ NEUTRAL"
                elif instrument == 'GBP_USD':
                    if mid_price > 1.2500:
                        trend = "📈 BULLISH"
                    elif mid_price < 1.2300:
                        trend = "📉 BEARISH"
                    else:
                        trend = "➡️ NEUTRAL"
                else:
                    trend = "📊 MONITORING"
                
                analysis += f"{instrument}: {mid_price:.5f} {trend}\n"
                analysis += f"Spread: {spread:.5f}\n\n"
            
            return analysis
        except Exception as e:
            return f"❌ Error analyzing market: {e}"

    def get_detailed_news_summary(self) -> str:
        try:
            # Prices and positions
            prices = self.get_current_prices()
            account = self.get_account_info() or {}
            balance = float(account.get('balance', 0))
            unreal = float(account.get('unrealizedPL', 0))

            # Upcoming events
            upcoming_txt = "No upcoming high-impact events in the next 60 minutes."
            if self.news and self.news.is_enabled():
                events = self.news.get_upcoming_high_impact(within_minutes=60)
                if events:
                    lines = []
                    for e in events[:5]:
                        t = e.time_utc.strftime('%H:%M:%S')
                        lines.append(f"{t}Z {e.currency} {e.title}")
                    upcoming_txt = "\n".join(lines)

            # Sentiment snapshot
            sentiment_txt = "Sentiment: n/a"
            if self.news:
                s = self.news.fetch_sentiment(window_minutes=10)
                if s:
                    score = s['avg_score']
                    count = s['count']
                    ents = s['entities']
                    top = sorted(ents.items(), key=lambda x: x[1], reverse=True)[:3]
                    top_txt = ", ".join([f"{k}:{v}" for k,v in top if v>0]) or "none"
                    sentiment_txt = f"Sentiment: {score:.2f} (n={count}) | Entities: {top_txt}"

            # Positions snapshot
            positions_txt = ""
            try:
                url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions"
                r = requests.get(url, headers=self.headers, timeout=10)
                if r.status_code == 200:
                    data = r.json().get('positions', [])
                    active = []
                    for p in data:
                        long_u = float(p['long']['units'])
                        short_u = float(p['short']['units'])
                        if long_u != 0 or short_u != 0:
                            active.append(f"{p['instrument']}: LONG {long_u} SHORT {short_u} | uPL {float(p.get('unrealizedPL',0)):.2f}")
                    positions_txt = "\n".join(active) if active else "No open positions"
                else:
                    positions_txt = "Positions: n/a"
            except Exception:
                positions_txt = "Positions: n/a"

            # Mode and guards
            guards = []
            if self.is_news_halt_active():
                guards.append("NewsHalt: ON")
            if self.is_throttle_active():
                guards.append("SentimentThrottle: ON")
            guards.append(f"news_mode={self.news_mode}")
            guards.append(f"risk={self.risk_per_trade*100:.1f}%")

            msg = (
                "📋 NEWS & MARKET BRIEF\n\n"
                f"Balance: ${balance:.2f} | uP&L: ${unreal:.2f}\n"
                f"Guards: {', '.join(guards)}\n\n"
                "Upcoming (60m):\n"
                f"{upcoming_txt}\n\n"
                f"{sentiment_txt}\n\n"
                "Positions:\n"
                f"{positions_txt}"
            )
            return msg
        except Exception as e:
            return f"❌ Error building news summary: {e}"

    def apply_news_halts(self) -> None:
        """Check upcoming high-impact events and set a temporary halt window if needed."""
        try:
            if not self.news or not self.news.is_enabled():
                return
            upcoming = self.news.get_upcoming_high_impact(within_minutes=60)
            if not upcoming:
                return
            soonest = min(upcoming, key=lambda e: e.time_utc)
            # Halt 15 minutes before until 30 minutes after
            now = datetime.utcnow()
            pre_time = soonest.time_utc - timedelta(minutes=15)
            post_time = soonest.time_utc + timedelta(minutes=30)
            if now >= pre_time and now <= post_time:
                self.news_halt_until = max(self.news_halt_until or now, post_time)
                logger.info(f"News halt active around {soonest.title} ({soonest.currency}) until {self.news_halt_until}")
                self.send_telegram_message(f"🛑 News Halt: {soonest.title} ({soonest.currency}) — trading halted until {post_time.strftime('%H:%M:%S')} UTC")
        except Exception as e:
            logger.warning(f"apply_news_halts error: {e}")

    def apply_sentiment_throttle(self) -> None:
        try:
            if self.news_mode == 'off' or not self.news:
                return
            s = self.news.fetch_sentiment(window_minutes=10)
            if not s:
                return
            score = s['avg_score']
            count = s['count']
            ents = s['entities']
            corroboration = count >= (2 if self.news_mode=='lite' else 3)
            threshold = {
                'lite': self.sentiment_threshold - 0.1,
                'normal': self.sentiment_threshold,
                'strict': self.sentiment_threshold + 0.1,
            }.get(self.news_mode, self.sentiment_threshold)

            relevant_hits = sum(ents.get(k,0) for k in ('USD','EUR','GBP','JPY','XAU'))
            if score <= threshold and corroboration and relevant_hits >= 2:
                # activate throttle for 15 minutes; reduce risk to half
                now = datetime.utcnow()
                until = now + timedelta(minutes=15)
                if not self.is_throttle_active():
                    self.base_risk = self.risk_per_trade
                    self.risk_per_trade = max(0.001, self.base_risk * 0.5)
                    self.send_telegram_message(f"⚠️ Sentiment Throttle: score {score:.2f}, halting new entries 15m; risk cut to {self.risk_per_trade*100:.1f}%")
                self.throttle_until = until
                # also block entries via news_halt window but cap total
                cap_until = now + timedelta(minutes=45)
                target = min(until, cap_until)
                self.news_halt_until = max(self.news_halt_until or now, target)
            else:
                # auto-lift if active and conditions improved
                if self.is_throttle_active() and score > (self.sentiment_threshold + 0.2):
                    self.throttle_until = None
                    self.risk_per_trade = self.base_risk
                    self.send_telegram_message("✅ Sentiment normalized — throttle lifted; risk restored")
        except Exception as e:
            logger.warning(f"apply_sentiment_throttle error: {e}")
    
    def get_performance_summary(self):
        """Get performance summary"""
        try:
            account_info = self.get_account_info()
            if not account_info:
                return "❌ Failed to get account info"
            
            balance = float(account_info['balance'])
            unrealized_pl = float(account_info['unrealizedPL'])
            
            return f"""📊 PERFORMANCE SUMMARY

💰 Current Balance: ${balance:.2f}
📈 Unrealized P&L: ${unrealized_pl:.2f}
📊 Total Equity: ${balance + unrealized_pl:.2f}
🎯 Daily Trades: {self.daily_trade_count}
🛡️ Active Positions: {len(self.active_trades)}
⚙️ Trading Status: {'ACTIVE' if self.trading_enabled else 'DISABLED'}
💰 Risk per Trade: {self.risk_per_trade*100:.1f}%

🤖 AI System: OPERATIONAL"""
        except Exception as e:
            return f"❌ Error getting performance: {e}"
    
    def execute_manual_trade(self, instrument, side):
        """Execute manual trade command"""
        try:
            if not self.trading_enabled:
                return "❌ Trading is disabled. Use /start_trading first"
            
            if len(self.active_trades) >= self.max_concurrent_trades:
                return "❌ Max concurrent trades reached"
            
            # Get current price
            prices = self.get_current_prices()
            if instrument not in prices:
                return f"❌ Invalid instrument: {instrument}"
            
            price_data = prices[instrument]
            entry_price = price_data['ask'] if side == 'BUY' else price_data['bid']
            
            # Calculate stop loss and take profit
            if side == 'BUY':
                stop_loss = entry_price - 0.0020  # 20 pips
                take_profit = entry_price + 0.0040  # 40 pips
            else:
                stop_loss = entry_price + 0.0020  # 20 pips
                take_profit = entry_price - 0.0040  # 40 pips
            
            # Create signal
            signal = {
                'instrument': instrument,
                'side': side,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': 90,
                'strategy': 'manual'
            }
            
            # Execute trade
            if self.execute_trade(signal):
                return f"✅ MANUAL TRADE EXECUTED: {instrument} {side} @ {entry_price:.5f}"
            else:
                return f"❌ Failed to execute trade: {instrument} {side}"
                
        except Exception as e:
            return f"❌ Manual trade error: {e}"
    
    def telegram_command_loop(self):
        """Main loop for processing Telegram commands"""
        logger.info("📱 Starting Telegram command processor...")
        
        while True:
            try:
                updates = self.get_telegram_updates()
                
                for update in updates:
                    self.last_update_id = update['update_id']
                    
                    if 'message' in update:
                        message = update['message']
                        user_name = message['from'].get('first_name', 'Unknown')
                        message_text = message.get('text', '')
                        
                        if message_text.startswith('/'):
                            response = self.process_telegram_command(message_text, user_name)
                            self.send_telegram_message(response)
                
                time.sleep(2)  # Check for commands every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in Telegram command loop: {e}")
                time.sleep(5)
    
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

    def is_news_halt_active(self) -> bool:
        try:
            if self.news_halt_until is None:
                return False
            return datetime.utcnow() < self.news_halt_until
        except Exception:
            return False

    def is_throttle_active(self) -> bool:
        try:
            if self.throttle_until is None:
                return False
            return datetime.utcnow() < self.throttle_until
        except Exception:
            return False
    
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

    def in_london_overlap(self) -> bool:
        # Approximate London/NY overlap using UTC hour (13:00–17:00 London time)
        h = datetime.utcnow().hour
        return 13 <= h <= 17
    
    def analyze_market(self, prices):
        """Analyze market conditions and generate trading signals"""
        signals = []
        
        for instrument, price_data in prices.items():
            try:
                mid_price = price_data['mid']
                spread = price_data['spread']
                
                # Instrument-specific spread thresholds (session-aware for XAU)
                max_spread = self.instrument_spread_limits.get(instrument, 0.00030)
                if instrument == 'XAU_USD' and not self.in_london_overlap():
                    max_spread = min(max_spread, 0.60)

                if spread > max_spread:
                    self.prev_mid[instrument] = mid_price
                    continue

                # Anti-chasing for gold after vertical pumps
                prev = self.prev_mid.get(instrument)
                if instrument == 'XAU_USD' and prev is not None:
                    jump_pct = (mid_price / prev) - 1.0
                    # If price jumped >0.6% and is still printing higher, skip to avoid chasing
                    if jump_pct > 0.006 and mid_price >= prev:
                        self.prev_mid[instrument] = mid_price
                        continue
                    # Require micro pullback before re-allowing longs after a jump
                    if jump_pct > 0 and mid_price > prev:
                        self.prev_mid[instrument] = mid_price
                        continue
                
                # Generate signals based on price levels and volatility
                if instrument == 'EUR_USD':
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
                
                # Track last mid for anti-chasing checks
                self.prev_mid[instrument] = mid_price

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
                units = int(risk_amount / stop_distance)
            else:
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
            if not self.trading_enabled:
                return False

            # Respect temporary news halt window
            if self.is_news_halt_active():
                logger.info("News halt active; skipping new entry")
                return False
                
            if self.daily_trade_count >= self.max_daily_trades:
                logger.warning("Daily trade limit reached")
                return False
            
            if len(self.active_trades) >= self.max_concurrent_trades:
                logger.warning("Max concurrent trades reached")
                return False

            # Diversification guardrails
            symbol_counts = {}
            symbols_set = set()
            for t in self.active_trades.values():
                sym = t['instrument']
                symbols_set.add(sym)
                symbol_counts[sym] = symbol_counts.get(sym, 0) + 1

            current_symbol = signal['instrument']
            current_symbol_cap = self.per_symbol_cap.get(current_symbol, self.max_per_symbol)
            current_symbol_count = symbol_counts.get(current_symbol, 0)

            if current_symbol_count >= current_symbol_cap:
                logger.info(f"Skipping trade: per-symbol cap reached for {current_symbol}")
                return False

            # Keep some slots for diversification if this symbol already occupies slots
            open_slots = self.max_concurrent_trades - len(self.active_trades)
            distinct_symbols = len(symbols_set)
            # If we are low on slots, ensure at least diversification across symbols
            if current_symbol in symbols_set and open_slots <= self.reserve_slots_for_diversification and distinct_symbols < 2:
                logger.info("Reserving slots for diversification; skipping additional entries on same symbol")
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
            
            # Risk throttle for XAU after pump: halve size if last jump >0.6%
            if signal['instrument'] == 'XAU_USD':
                prev = self.prev_mid.get('XAU_USD')
                if prev:
                    jump_pct = (signal['entry_price'] / prev) - 1.0
                    if jump_pct > 0.006:
                        units = max(1, int(units * 0.5))

            # Adjust units for SELL orders
            if signal['side'] == 'SELL':
                units = -units
            
            # Create order with correct price precision per instrument
            def round_price(inst: str, px: float) -> str:
                if inst in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
                    return f"{px:.5f}"
                if inst == 'USD_JPY':
                    return f"{px:.3f}"
                if inst == 'XAU_USD':
                    return f"{px:.2f}"
                return f"{px:.5f}"

            tp = float(signal['take_profit'])
            sl = float(signal['stop_loss'])
            tp_str = round_price(current_symbol, tp)
            sl_str = round_price(current_symbol, sl)

            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": signal['instrument'],
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "stopLossOnFill": {"price": sl_str},
                    "takeProfitOnFill": {"price": tp_str}
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
                self.send_trade_alert(signal, order_id, units)
                
                logger.info(f"✅ TRADE EXECUTED: {signal['instrument']} {signal['side']} - Units: {units}")
                return True
            else:
                logger.error(f"❌ Trade failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return False
    
    def send_trade_alert(self, signal, order_id, units):
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
            
            self.send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")
    
    def monitor_trades(self):
        """Monitor active trades and close if needed"""
        try:
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                positions = response.json()['positions']
                # Refresh prices once per cycle
                prices = self.get_current_prices()
                for position in positions:
                    instrument = position['instrument']
                    if instrument not in self.instruments or instrument not in prices:
                        continue
                    cur_mid = prices[instrument]['mid']

                    # Collect tracked orders for this instrument
                    tracked_items = [(oid, t) for oid, t in self.active_trades.items() if t['instrument'] == instrument]
                    if not tracked_items:
                        continue

                    long_units = float(position['long']['units'])
                    short_units = float(position['short']['units'])

                    for order_id, t in tracked_items:
                        entry = float(t['entry_price'])
                        stop = float(t['stop_loss'])
                        side = t['side']
                        r_dist = max(1e-9, (entry - stop) if side == 'BUY' else (stop - entry))
                        r_multiple = (cur_mid - entry) / r_dist if side == 'BUY' else (entry - cur_mid) / r_dist

                        # 0.8R: take 25% to simulate BE+ (lock some gains)
                        if r_multiple >= 0.8 and not t.get('tp25_done'):
                            try:
                                payload = {}
                                if long_units > 0:
                                    qty = max(1, int(long_units * 0.25))
                                    payload = {"longUnits": str(qty)}
                                elif short_units > 0:
                                    qty = max(1, int(abs(short_units) * 0.25))
                                    payload = {"shortUnits": str(qty)}
                                if payload:
                                    close_url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions/{instrument}/close"
                                    r = requests.post(close_url, headers=self.headers, json=payload, timeout=10)
                                    if r.status_code in (200, 201):
                                        t['tp25_done'] = True
                                        logger.info(f"✅ 0.8R harvest on {instrument}: {payload}")
                                        self.send_telegram_message(f"0.8R Harvest: Closed {payload} on {instrument} @ ~{cur_mid:.5f}")
                            except Exception as e:
                                logger.warning(f"0.8R harvest failed for {instrument}: {e}")

                        # 1.0R: take 50% of remaining
                        if r_multiple >= 1.0 and not t.get('tp50_done'):
                            try:
                                payload = {}
                                if long_units > 0:
                                    qty = max(1, int(long_units * 0.50))
                                    payload = {"longUnits": str(qty)}
                                elif short_units > 0:
                                    qty = max(1, int(abs(short_units) * 0.50))
                                    payload = {"shortUnits": str(qty)}
                                if payload:
                                    close_url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions/{instrument}/close"
                                    r = requests.post(close_url, headers=self.headers, json=payload, timeout=10)
                                    if r.status_code in (200, 201):
                                        t['tp50_done'] = True
                                        logger.info(f"✅ 1R partial on {instrument}: {payload}")
                                        self.send_telegram_message(f"1R Partial: Closed {payload} on {instrument} @ ~{cur_mid:.5f}")
                            except Exception as e:
                                logger.warning(f"1R partial failed for {instrument}: {e}")

                        # 1.5R: close all remaining
                        if r_multiple >= 1.5 and not t.get('full_exit_done'):
                            try:
                                payload = {}
                                if long_units > 0:
                                    payload = {"longUnits": "ALL"}
                                elif short_units > 0:
                                    payload = {"shortUnits": "ALL"}
                                if payload:
                                    close_url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions/{instrument}/close"
                                    r = requests.post(close_url, headers=self.headers, json=payload, timeout=10)
                                    if r.status_code in (200, 201):
                                        t['full_exit_done'] = True
                                        logger.info(f"✅ 1.5R full exit on {instrument}")
                                        self.send_telegram_message(f"Full Exit: Closed {instrument} @ ~{cur_mid:.5f} (>=1.5R)")
                            except Exception as e:
                                logger.warning(f"Full exit failed for {instrument}: {e}")
                            
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}")
    
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        if not self.trading_enabled:
            return
            
        logger.info("🔍 Starting trading cycle...")
        # Update news halts if calendar enabled
        self.apply_news_halts()
        # Apply sentiment throttle if enabled
        self.apply_sentiment_throttle()
        
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
            
            self.send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

def main():
    """Main trading loop"""
    logger.info("🚀 STARTING AI TRADING SYSTEM WITH TELEGRAM COMMANDS")
    logger.info("📊 DEMO ACCOUNT ONLY - NO REAL MONEY AT RISK")
    
    system = AITradingSystem()
    
    # Send startup notification
    system.send_telegram_message("""🤖 AI TRADING SYSTEM STARTED!

📊 Demo Account: 101-004-30719775-008
💰 Risk per trade: 1%
📈 Max daily trades: 50
🛡️ Max concurrent trades: 5

✅ System is now scanning markets and executing trades automatically!
📱 You can now send commands via Telegram!

Type /help for available commands""")
    
    # Start Telegram command processor in separate thread
    telegram_thread = threading.Thread(target=system.telegram_command_loop, daemon=True)
    telegram_thread.start()
    
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
