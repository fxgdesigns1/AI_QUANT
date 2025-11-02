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
OANDA_API_KEY = "REMOVED_SECRET"
OANDA_ACCOUNT_ID = "101-004-30719775-008"  # Demo account
OANDA_BASE_URL = "https://api-fxpractice.oanda.com"

# Telegram Configuration (env-driven)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

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
        
        # Rate limiting for bracket notifications
        self.last_bracket_notification = {}
        self.bracket_notification_cooldown = 300  # 5 minutes between notifications per trade
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
        # Adaptive store (online learning of parameters)
        try:
            from adaptive_store import AdaptiveStore
            self.adaptive_store = AdaptiveStore()
        except Exception:
            self.adaptive_store = None  # type: ignore

        # Dynamic signal parameters (env-configurable)
        self.xau_ema_period = int(os.getenv('XAU_EMA_PERIOD', '50'))
        self.xau_atr_period = int(os.getenv('XAU_ATR_PERIOD', '14'))
        self.xau_k_atr = float(os.getenv('XAU_K_ATR', '1.5'))  # stricter distance from EMA in ATRs
        # Generic defaults for all pairs
        self.ema_period_default = int(os.getenv('EMA_PERIOD_DEFAULT', '50'))
        self.atr_period_default = int(os.getenv('ATR_PERIOD_DEFAULT', '14'))
        self.k_atr_default = float(os.getenv('K_ATR_DEFAULT', '1.0'))
        # Per-instrument max units (prevents tiny P&L from low cap)
        self.max_units_per_instrument = {
            'EUR_USD': int(os.getenv('MAX_UNITS_EUR_USD', '50000')),
            'GBP_USD': int(os.getenv('MAX_UNITS_GBP_USD', '50000')),
            'AUD_USD': int(os.getenv('MAX_UNITS_AUD_USD', '50000')),
            'USD_JPY': int(os.getenv('MAX_UNITS_USD_JPY', '200000')),
            'XAU_USD': int(os.getenv('MAX_UNITS_XAU_USD', '500')),
        }
        
        logger.info(f"🤖 AI Trading System initialized")
        logger.info(f"📊 Demo Account: {self.account_id}")
        logger.info(f"💰 Risk per trade: {self.risk_per_trade*100}%")
        logger.info(f"📱 Telegram commands: ENABLED")
        self.performance_events = []  # type: ignore
        
    def should_send_bracket_notification(self, trade_id):
        """Check if we should send a bracket notification (rate limited)"""
        now = datetime.now()
        last_notification = self.last_bracket_notification.get(trade_id)
        
        if last_notification is None:
            return True
            
        time_since_last = (now - last_notification).total_seconds()
        return time_since_last >= self.bracket_notification_cooldown
        
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

    def list_open_trades(self) -> List[Dict[str, Any]]:
        try:
            r = requests.get(f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/trades",
                             headers=self.headers, timeout=10)
            if r.status_code == 200:
                return r.json().get('trades', [])
        except Exception as e:
            logger.warning(f"list_open_trades error: {e}")
        return []

    def _round_price(self, inst: str, px: float) -> str:
        if inst in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
            return f"{px:.5f}"
        if inst == 'USD_JPY':
            return f"{px:.3f}"
        if inst == 'XAU_USD':
            return f"{px:.2f}"
        return f"{px:.5f}"

    def attach_brackets(self, trade_id: str, instrument: str, side: str, entry_price: float) -> bool:
        """Ensure SL/TP exist on a live trade by attaching dependent orders server-side."""
        try:
            # Conservative defaults if we lack original SL/TP: FX 20/40 pips, XAU $5/$10
            if instrument == 'XAU_USD':
                sl_dist = 5.0
                tp_dist = 10.0
            elif instrument == 'USD_JPY':
                sl_dist = 0.20  # 20 pips ~ 0.20 JPY
                tp_dist = 0.40
            else:
                sl_dist = 0.0020
                tp_dist = 0.0040

            if side == 'BUY':
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
            else:
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist

            payload = {
                "takeProfit": {"price": self._round_price(instrument, tp)},
                "stopLoss": {"price": self._round_price(instrument, sl)}
            }
            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/trades/{trade_id}/orders"
            r = requests.put(url, headers=self.headers, json=payload, timeout=10)
            ok = r.status_code in (200, 201)
            if not ok:
                logger.warning(f"attach_brackets failed {r.status_code}: {r.text[:120]}")
            return ok
        except Exception as e:
            logger.warning(f"attach_brackets error: {e}")
            return False

    def trade_has_brackets(self, trade: Dict[str, Any]) -> bool:
        # OANDA v3 returns dependent order summaries when present
        return bool(trade.get('takeProfitOrder') or trade.get('stopLossOrder'))

    def get_live_counts(self) -> Dict[str, int]:
        counts: Dict[str, Any] = {"positions": 0, "pending": 0, "by_symbol": {}}
        try:
            # Open positions (net by instrument)
            r = requests.get(f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/openPositions",
                             headers=self.headers, timeout=10)
            if r.status_code == 200:
                for p in r.json().get('positions', []):
                    long_u = float(p['long']['units']); short_u = float(p['short']['units'])
                    if long_u != 0 or short_u != 0:
                        counts['positions'] += 1
                        sym = p['instrument']
                        counts['by_symbol'][sym] = counts['by_symbol'].get(sym, 0) + 1
            # Pending orders (exclude dependent SL/TP orders)
            r2 = requests.get(
                f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pendingOrders",
                headers=self.headers,
                timeout=10,
            )
            if r2.status_code == 200:
                orders = r2.json().get('orders', [])
                for o in orders:
                    otype = o.get('type', '').upper()
                    # Only count entry orders towards caps; exclude dependent SL/TP orders
                    is_entry_order = otype in ('LIMIT', 'STOP', 'MARKET_IF_TOUCHED')
                    if not is_entry_order:
                        continue
                    counts['pending'] += 1
                    sym = o.get('instrument')
                    if sym:
                        counts['by_symbol'][sym] = counts['by_symbol'].get(sym, 0) + 1
        except Exception as e:
            logger.warning(f"get_live_counts error: {e}")
        return counts  # type: ignore

    def enforce_live_cap(self) -> None:
        """Ensure positions+pending <= max_concurrent_trades; cancel excess entry orders by age.
        Only entry orders (LIMIT/STOP/MARKET_IF_TOUCHED) are considered and cancelled. Dependent
        bracket orders (TAKE_PROFIT/STOP_LOSS/TRAILING_STOP_LOSS) are ignored.
        """
        try:
            counts = self.get_live_counts()
            total_live = counts['positions'] + counts['pending']
            if total_live <= self.max_concurrent_trades:
                return
            to_cancel = total_live - self.max_concurrent_trades
            r = requests.get(
                f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pendingOrders",
                headers=self.headers,
                timeout=10,
            )
            if r.status_code != 200:
                return
            orders = r.json().get('orders', [])
            # Consider only entry orders for cancellation; cancel oldest first
            orders_sorted = sorted(orders, key=lambda o: o.get('createTime',''))
            for o in orders_sorted:
                otype = o.get('type', '').upper()
                if otype not in ('LIMIT', 'STOP', 'MARKET_IF_TOUCHED'):
                    continue
                if to_cancel <= 0:
                    break
                oid = o.get('id')
                if not oid:
                    continue
                try:
                    requests.put(f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/orders/{oid}/cancel",
                                 headers=self.headers, timeout=10)
                    logger.info(f"🗑️ Cancelled pending order {oid} to enforce cap")
                    to_cancel -= 1
                except Exception:
                    continue
            if to_cancel > 0:
                logger.warning("Unable to cancel enough pending orders to meet cap")
        except Exception as e:
            logger.warning(f"enforce_live_cap error: {e}")
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
                missing = []
                stale = []
                now = datetime.utcnow()
                for price_data in data.get('prices', []):
                    try:
                        instrument = price_data.get('instrument')
                        if not instrument:
                            continue
                        status = price_data.get('status', '').lower()
                        t = price_data.get('time')
                        ts_ok = True
                        if t:
                            try:
                                # OANDA time is RFC3339; compare staleness > 30s
                                pt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                                ts_ok = (now - pt).total_seconds() <= 30
                            except Exception:
                                ts_ok = True
                        if status not in ('tradeable', 'tradable'):
                            stale.append(instrument)
                            continue
                        bid = float(price_data.get('bids', [{'price': '0'}])[0]['price'])
                        ask = float(price_data.get('asks', [{'price': '0'}])[0]['price'])
                        if bid <= 0 or ask <= 0 or not ts_ok:
                            stale.append(instrument)
                            continue
                        prices[instrument] = {
                            'bid': bid,
                            'ask': ask,
                            'mid': (bid + ask) / 2,
                            'spread': ask - bid
                        }
                    except Exception:
                        continue

                # Verify all requested instruments present
                for inst in self.instruments:
                    if inst not in prices:
                        missing.append(inst)

                if missing or stale:
                    warn = []
                    if missing:
                        warn.append(f"missing={','.join(missing)}")
                    if stale:
                        warn.append(f"stale={','.join(stale)}")
                    msg = f"⚠️ Live price verification issue: {'; '.join(warn)}. New entries temporarily halted."
                    logger.warning(msg)
                    self.news_halt_until = datetime.utcnow() + timedelta(minutes=5)
                    self.send_telegram_message(msg)
                return prices
            else:
                logger.error(f"Failed to get prices: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return {}

    def _fetch_candles(self, instrument: str, granularity: str = 'M5', count: int = 200):
        try:
            url = f"{OANDA_BASE_URL}/v3/instruments/{instrument}/candles"
            params = {
                'granularity': granularity,
                'count': count,
                'price': 'M'  # mid prices
            }
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            if r.status_code != 200:
                return []
            return r.json().get('candles', [])
        except Exception as e:
            logger.warning(f"fetch_candles error for {instrument}: {e}")
            return []

    def _compute_ema(self, values, period: int) -> float:
        if not values or period <= 0 or len(values) < period:
            return 0.0
        k = 2 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return float(ema)

    def _compute_atr_from_mid(self, mids, period: int) -> float:
        # For simplicity with mid-only candles, approximate TR with absolute diff between consecutive mids
        if not mids or period <= 0 or len(mids) <= period:
            return 0.0
        trs = [abs(mids[i] - mids[i-1]) for i in range(1, len(mids))]
        # Wilder's smoothing approximation
        atr = sum(trs[:period]) / period
        for tr in trs[period:]:
            atr = (atr * (period - 1) + tr) / period
        return float(atr)

    def _get_xau_indicators(self) -> dict:
        # Use adaptive params if available
        ap = (self.adaptive_store.get('XAU_USD') if getattr(self, 'adaptive_store', None) else {})
        ema_p = int(ap.get('ema', self.xau_ema_period)) if isinstance(ap, dict) else self.xau_ema_period
        atr_p = int(ap.get('atr', self.xau_atr_period)) if isinstance(ap, dict) else self.xau_atr_period
        kx = float(ap.get('k_atr', self.xau_k_atr)) if isinstance(ap, dict) else self.xau_k_atr
        candles = self._fetch_candles('XAU_USD', granularity='M5', count=max(200, ema_p + atr_p + 20))
        mids = []
        for c in candles:
            try:
                m = float(c['mid']['c'])
                mids.append(m)
            except Exception:
                continue
        if not mids:
            return {'ema': 0.0, 'atr': 0.0, 'upper': 0.0, 'lower': 0.0, 'slope_up': False, 'confirm_above': 0, 'confirm_below': 0, 'high_vol_spike': False}
        ema = self._compute_ema(mids, ema_p)
        atr = self._compute_atr_from_mid(mids, atr_p)
        upper = ema + kx * atr
        lower = ema - kx * atr
        slope_up = len(mids) >= 4 and (mids[-1] > mids[-2] >= mids[-3])
        last3 = mids[-3:]
        confirm_above = sum(1 for v in last3 if v > upper)
        confirm_below = sum(1 for v in last3 if v < lower)
        if len(mids) >= 14:
            recent_trs = [abs(mids[i] - mids[i-1]) for i in range(len(mids)-6, len(mids))]
            prev_trs = [abs(mids[i] - mids[i-1]) for i in range(len(mids)-12, len(mids)-6)]
            atr_recent = sum(recent_trs) / len(recent_trs) if recent_trs else 0.0
            atr_prev = sum(prev_trs) / len(prev_trs) if prev_trs else 0.0
            high_vol_spike = atr_prev > 0 and atr_recent > 1.5 * atr_prev
        else:
            high_vol_spike = False
        return {'ema': ema, 'atr': atr, 'upper': upper, 'lower': lower, 'slope_up': slope_up, 'confirm_above': confirm_above, 'confirm_below': confirm_below, 'high_vol_spike': high_vol_spike}

    def in_london_session(self) -> bool:
        # Approximate London session 08:00–17:00 (UTC proxy)
        h = datetime.utcnow().hour
        return 8 <= h <= 17

    def _get_indicators(self, instrument: str) -> dict:
        # Prefer adaptive store; fallback to env defaults
        ap = (self.adaptive_store.get(instrument) if getattr(self, 'adaptive_store', None) else {})
        key = instrument.replace('/', '_')
        ema_period = int(ap.get('ema', int(os.getenv(f'EMA_PERIOD_{key}', str(self.ema_period_default))))) if isinstance(ap, dict) else int(os.getenv(f'EMA_PERIOD_{key}', str(self.ema_period_default)))
        atr_period = int(ap.get('atr', int(os.getenv(f'ATR_PERIOD_{key}', str(self.atr_period_default))))) if isinstance(ap, dict) else int(os.getenv(f'ATR_PERIOD_{key}', str(self.atr_period_default)))
        k_atr = float(ap.get('k_atr', float(os.getenv(f'K_ATR_{key}', str(self.k_atr_default))))) if isinstance(ap, dict) else float(os.getenv(f'K_ATR_{key}', str(self.k_atr_default)))
        candles = self._fetch_candles(instrument, granularity='M5', count=max(200, ema_period + atr_period + 5))
        mids = []
        for c in candles:
            try:
                mids.append(float(c['mid']['c']))
            except Exception:
                continue
        if not mids:
            return {'ema': 0.0, 'atr': 0.0, 'k': k_atr, 'slope_up': False, 'confirm_above': 0, 'confirm_below': 0, 'm15_ema': 0.0}
        ema = self._compute_ema(mids, ema_period)
        atr = self._compute_atr_from_mid(mids, atr_period)
        slope_up = len(mids) >= 4 and (mids[-1] > mids[-2] >= mids[-3])
        last3 = mids[-3:]
        confirm_above = sum(1 for v in last3 if v > ema + k_atr * atr)
        confirm_below = sum(1 for v in last3 if v < ema - k_atr * atr)
        # M15 alignment
        m15_candles = self._fetch_candles(instrument, granularity='M15', count=max(60, ema_period + 5))
        m15_mids = []
        for c in m15_candles:
            try:
                m15_mids.append(float(c['mid']['c']))
            except Exception:
                continue
        m15_ema = self._compute_ema(m15_mids, ema_period) if m15_mids else 0.0
        return {'ema': ema, 'atr': atr, 'k': k_atr, 'slope_up': slope_up, 'confirm_above': confirm_above, 'confirm_below': confirm_below, 'm15_ema': m15_ema}

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
                if instrument in ('EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'):
                    ind = self._get_indicators(instrument)
                    ema = ind.get('ema', 0.0); atr = ind.get('atr', 0.0); k = ind.get('k', self.k_atr_default)
                    slope_up = ind.get('slope_up', False)
                    confirm_above = ind.get('confirm_above', 0)
                    confirm_below = ind.get('confirm_below', 0)
                    m15_ema = ind.get('m15_ema', 0.0)
                    if instrument in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
                        k = max(k, 1.25)
                    if ema > 0 and atr > 0:
                        upper = ema + k * atr
                        lower = ema - k * atr
                        # adaptive SL/TP multipliers with spread-aware TP boost
                        ap2 = (self.adaptive_store.get(instrument) if getattr(self, 'adaptive_store', None) else {})
                        sl_mult_cfg = float(ap2.get('sl_mult', 0.5)) if isinstance(ap2, dict) else 0.5
                        tp_mult_cfg = float(ap2.get('tp_mult', 1.0)) if isinstance(ap2, dict) else 1.0
                        tp_mult = max(tp_mult_cfg, 1.0 if atr <= 0 else (1.5 if spread <= max(1e-9, 0.25 * atr) else tp_mult_cfg))
                        sl = max(0.0005, sl_mult_cfg * atr)
                        tp = max(0.0010, tp_mult * atr)
                        if mid_price > upper and confirm_above >= 2 and slope_up and (m15_ema == 0.0 or mid_price > m15_ema):
                            signals.append({
                                'instrument': instrument,
                                'side': 'BUY',
                                'entry_price': price_data['ask'],
                                'stop_loss': mid_price - sl,
                                'take_profit': mid_price + tp,
                                'confidence': 75,
                                'strategy': 'ema_atr_breakout_confirmed'
                            })
                        elif mid_price < lower and confirm_below >= 2 and (m15_ema == 0.0 or mid_price < m15_ema):
                            signals.append({
                                'instrument': instrument,
                                'side': 'SELL',
                                'entry_price': price_data['bid'],
                                'stop_loss': mid_price + sl,
                                'take_profit': mid_price - tp,
                                'confidence': 75,
                                'strategy': 'ema_atr_breakout_confirmed'
                            })
                
                elif instrument == 'XAU_USD':
                    ind = self._get_xau_indicators()
                    ema = ind.get('ema', 0.0)
                    atr = ind.get('atr', 0.0)
                    upper = ind.get('upper', 0.0)
                    lower = ind.get('lower', 0.0)
                    slope_up = ind.get('slope_up', False)
                    confirm_above = ind.get('confirm_above', 0)
                    confirm_below = ind.get('confirm_below', 0)
                    high_vol_spike = ind.get('high_vol_spike', False)
                    if ema > 0 and atr > 0:
                        if high_vol_spike:
                            self.news_halt_until = datetime.utcnow() + timedelta(minutes=15)
                            logger.info("XAU volatility spike; pausing new entries 15m")
                            continue
                        if not self.in_london_session():
                            logger.info("XAU entry blocked: outside London session")
                            continue
                        if mid_price > upper and slope_up and confirm_above >= 2:
                            signals.append({
                                'instrument': instrument,
                                'side': 'BUY',
                                'entry_price': price_data['ask'],
                                'stop_loss': mid_price - max(10.0, 0.5 * atr),
                                'take_profit': mid_price + max(15.0, 1.0 * atr),
                                'confidence': 80,
                                'strategy': 'ema_atr_breakout_confirmed'
                            })
                        elif mid_price < lower and confirm_below >= 2:
                            signals.append({
                                'instrument': instrument,
                                'side': 'SELL',
                                'entry_price': price_data['bid'],
                                'stop_loss': mid_price + max(10.0, 0.5 * atr),
                                'take_profit': mid_price - max(15.0, 1.0 * atr),
                                'confidence': 80,
                                'strategy': 'ema_atr_breakout_confirmed'
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
            
            # Limit position size per instrument
            max_units = self.max_units_per_instrument.get(signal['instrument'], 10000)
            # XAU additional high-vol size cut
            if signal['instrument'] == 'XAU_USD':
                ind = self._get_xau_indicators()
                if ind.get('high_vol_spike', False):
                    units = max(1, int(units * 0.5))
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
            
            # Broker-aware cap: positions + pending must be below cap
            live = self.get_live_counts()
            total_live = live['positions'] + live['pending']
            if total_live >= self.max_concurrent_trades:
                logger.info("Global cap reached (positions+pending); skipping new entry")
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
            # Per-symbol live count (positions + pending)
            sym_live = live['by_symbol'].get(current_symbol, 0)
            current_symbol_count = symbol_counts.get(current_symbol, 0)

            if sym_live >= current_symbol_cap or current_symbol_count >= current_symbol_cap:
                logger.info(f"Skipping trade: per-symbol cap reached for {current_symbol}")
                return False

            # Keep some slots for diversification if this symbol already occupies slots
            open_slots = self.max_concurrent_trades - len(self.active_trades)
            distinct_symbols = len(symbols_set)
            # If we are low on slots, ensure at least diversification across symbols
            if current_symbol in symbols_set and open_slots <= self.reserve_slots_for_diversification and distinct_symbols < 2:
                logger.info("Reserving slots for diversification; skipping additional entries on same symbol")
                return False

            # Allow 2nd position in same symbol only if an existing one is at least 0.5R in profit
            if current_symbol_count >= 1:
                prices_now = self.get_current_prices() or {}
                cur_mid = prices_now.get(current_symbol, {}).get('mid') if current_symbol in prices_now else None
                r_ok = False
                if cur_mid is not None:
                    for _, t in self.active_trades.items():
                        if t['instrument'] != current_symbol:
                            continue
                        entry = float(t['entry_price']); stop = float(t['stop_loss']); side = t['side']
                        r_dist = max(1e-9, (entry - stop) if side == 'BUY' else (stop - entry))
                        r_multiple = (cur_mid - entry) / r_dist if side == 'BUY' else (entry - cur_mid) / r_dist
                        if r_multiple >= 0.5:
                            r_ok = True
                            break
                if current_symbol_count >= 1 and not r_ok:
                    logger.info("Second position blocked: no existing trade >= 0.5R")
                    return False
            
            # Get account balance
            account_info = self.get_account_info()
            if not account_info:
                return False
            
            balance = float(account_info['balance'])
            
            # Calculate position size
            units = self.calculate_position_size(signal, balance)
            # Pre-trade minimum profit checks (0.5R and min absolute $ profit)
            try:
                min_r = float(os.getenv('MIN_EXPECTED_R', '0.5'))
                min_abs = float(os.getenv('MIN_ABS_PROFIT_USD', '0.5'))
                entry = float(signal['entry_price'])
                tpv = float(signal['take_profit'])
                slv = float(signal['stop_loss'])
                sl_dist = abs(entry - slv)
                tp_dist = abs(tpv - entry)
                # Require TP distance >= min_r * SL distance
                if sl_dist <= 0 or tp_dist < (min_r * sl_dist):
                    logger.info("Entry blocked: TP < minimum expected R threshold")
                    return False
                # Estimate absolute profit at TP in USD
                inst = signal['instrument']
                expected_abs = 0.0
                if inst in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
                    expected_abs = abs(units) * tp_dist
                elif inst == 'USD_JPY':
                    # Convert JPY P&L to USD using entry price
                    expected_abs = (abs(units) * tp_dist) / max(1e-9, entry)
                elif inst == 'XAU_USD':
                    # XAU units are in ounces; price in USD
                    expected_abs = abs(units) * tp_dist
                if expected_abs < min_abs:
                    logger.info(f"Entry blocked: expected TP ${expected_abs:.2f} < min ${min_abs:.2f}")
                    return False
            except Exception as e:
                logger.warning(f"min-profit check error: {e}")
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

            order_type = signal.get('order_type', 'MARKET').upper()
            if order_type == 'LIMIT':
                price_str = round_price(current_symbol, float(signal['entry_price']))
                order_data = {
                    "order": {
                        "type": "LIMIT",
                        "instrument": signal['instrument'],
                        "units": str(units),
                        "price": price_str,
                        "timeInForce": "GTC",
                        "positionFill": "DEFAULT",
                        "stopLossOnFill": {"price": sl_str},
                        "takeProfitOnFill": {"price": tp_str}
                    }
                }
            else:
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
                body = response.json()
                order_info = body.get('orderCreateTransaction') or {}
                order_id = order_info.get('id', '')
                
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

                # Post-fill verification (best-effort): ensure brackets present on live trades
                try:
                    if order_type != 'LIMIT':
                        # MARKET orders may immediately create trades; verify and attach if missing
                        trades = self.list_open_trades()
                        for t in trades:
                            if t.get('instrument') == current_symbol:
                                side = 'BUY' if float(t.get('currentUnits','0')) > 0 else 'SELL'
                                entry = float(t.get('price', signal['entry_price']))
                                if not self.trade_has_brackets(t):
                                    if self.attach_brackets(t['id'], current_symbol, side, entry):
                                        trade_id = str(t['id']).replace('[', '').replace(']', '')
                                        if self.should_send_bracket_notification(trade_id):
                                            self.send_telegram_message(f"🔒 Brackets attached for {current_symbol} trade {trade_id}")
                                            self.last_bracket_notification[trade_id] = datetime.now()
                    # LIMIT orders get brackets on fill; the post-cycle audit will catch any missing
                except Exception as e:
                    logger.warning(f"post-fill bracket attach error: {e}")
                
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
            # Clean and format values to avoid brackets in messages
            instrument = str(signal.get('instrument', 'Unknown')).replace('[', '').replace(']', '')
            side = str(signal.get('side', 'Unknown')).replace('[', '').replace(']', '')
            entry_price = f"{float(signal.get('entry_price', 0)):.5f}"
            stop_loss = f"{float(signal.get('stop_loss', 0)):.5f}"
            take_profit = f"{float(signal.get('take_profit', 0)):.5f}"
            strategy = str(signal.get('strategy', 'Unknown')).replace('[', '').replace(']', '')
            order_id_clean = str(order_id).replace('[', '').replace(']', '')
            
            message = f"""🚀 TRADE EXECUTED!

📊 Instrument: {instrument}
📈 Side: {side}
💰 Units: {units}
💵 Entry: {entry_price}
🛡️ Stop Loss: {stop_loss}
🎯 Take Profit: {take_profit}
📊 Strategy: {strategy}
🆔 Order ID: {order_id_clean}

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

                # Backfill missing brackets on live trades (best-effort)
                try:
                    open_trades = self.list_open_trades()
                    for t in open_trades:
                        if not self.trade_has_brackets(t):
                            inst = t.get('instrument')
                            if not inst or inst not in prices:
                                continue
                            side = 'BUY' if float(t.get('currentUnits','0')) > 0 else 'SELL'
                            entry = float(t.get('price', prices[inst]['mid']))
                            if self.attach_brackets(t['id'], inst, side, entry):
                                trade_id = str(t['id']).replace('[', '').replace(']', '')
                                if self.should_send_bracket_notification(trade_id):
                                    self.send_telegram_message(f"🔒 Brackets attached for {inst} trade {trade_id}")
                                    self.last_bracket_notification[trade_id] = datetime.now()
                except Exception as e:
                    logger.warning(f"backfill brackets error: {e}")
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
                                        try:
                                            self.performance_events.append({'instrument': instrument, 'event': 'tp25', 'time': datetime.utcnow()})
                                        except Exception:
                                            pass
                                        logger.info(f"✅ 0.8R harvest on {instrument}: {payload}")
                                        # Only send harvest notification once per trade
                                        if not t.get('harvest_notified'):
                                            self.send_telegram_message(f"0.8R Harvest: Closed {str(payload).replace('[', '').replace(']', '')} on {instrument} @ ~{cur_mid:.5f}")
                                            t['harvest_notified'] = True
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
                                        try:
                                            self.performance_events.append({'instrument': instrument, 'event': 'tp50', 'time': datetime.utcnow()})
                                        except Exception:
                                            pass
                                        logger.info(f"✅ 1R partial on {instrument}: {payload}")
                                        # Only send partial notification once per trade
                                        if not t.get('partial_notified'):
                                            self.send_telegram_message(f"1R Partial: Closed {str(payload).replace('[', '').replace(']', '')} on {instrument} @ ~{cur_mid:.5f}")
                                            t['partial_notified'] = True
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
                                        try:
                                            self.performance_events.append({'instrument': instrument, 'event': 'full_exit', 'time': datetime.utcnow()})
                                        except Exception:
                                            pass
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
        # Enforce cap post-execution (cancel excess pending if any)
        self.enforce_live_cap()
        
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

    def adaptive_loop(self):
        """Periodically adjust per-instrument parameters based on recent performance events."""
        while True:
            try:
                if not getattr(self, 'adaptive_store', None):
                    time.sleep(1800)
                    continue
                # Look back 6 hours
                cutoff = datetime.utcnow() - timedelta(hours=6)
                recent = [e for e in self.performance_events if e.get('time') and e['time'] >= cutoff]
                by_inst: Dict[str, List[Dict[str, Any]]] = {}
                for e in recent:
                    by_inst.setdefault(e['instrument'], []).append(e)
                changed = []
                for inst, evs in by_inst.items():
                    # proxy reward: tp25=0.25R, tp50=0.5R, full_exit=1.0R
                    score = 0.0
                    for e in evs:
                        if e['event'] == 'tp25':
                            score += 0.25
                        elif e['event'] == 'tp50':
                            score += 0.50
                        elif e['event'] == 'full_exit':
                            score += 1.00
                    avg_r = score / max(1, len(evs))
                    ap = self.adaptive_store.get(inst)
                    k = float(ap.get('k_atr', 1.0))
                    tp_mult = float(ap.get('tp_mult', 1.0))
                    # Simple bounded adjustments
                    if avg_r > 0.35:
                        nk = max(0.9, round(k - 0.05, 2))
                        ntp = min(2.0, round(tp_mult + 0.1, 2))
                    elif avg_r < 0.1:
                        nk = min(2.0, round(k + 0.1, 2))
                        ntp = max(0.8, round(tp_mult - 0.1, 2))
                    else:
                        continue
                    if abs(nk - k) >= 1e-6 or abs(ntp - tp_mult) >= 1e-6:
                        self.adaptive_store.set_param(inst, 'k_atr', nk)
                        self.adaptive_store.set_param(inst, 'tp_mult', ntp)
                        changed.append((inst, k, nk, tp_mult, ntp))
                if changed:
                    msg = "🤖 Adaptive update:\n" + "\n".join(
                        f"{i}: k_ATR {ok:.2f}->{nk:.2f}, TPx {otp:.2f}->{ntp:.2f}" for i, ok, nk, otp, ntp in changed
                    )
                    self.send_telegram_message(msg)
            except Exception as e:
                logger.warning(f"adaptive_loop error: {e}")
            time.sleep(1800)  # 30 minutes

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
    # Start adaptive loop in separate thread
    adaptive_thread = threading.Thread(target=system.adaptive_loop, daemon=True)
    adaptive_thread.start()
    
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
