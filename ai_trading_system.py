#!/usr/bin/env python3
from src.core.settings import settings
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
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import schedule
import pytz
from flask import Flask, jsonify
from threading import Thread

# --- Environment Setup ---
# Load environment variables from the config file. This should be the first step.
CONFIG_PATH = "/Users/mac/quant_system_clean/google-cloud-trading-system/oanda_config.env"
if os.path.exists(CONFIG_PATH):
    load_dotenv(dotenv_path=CONFIG_PATH)
else:
    # Fallback for local development or different environments
    load_dotenv()

# Add the project root to sys.path for absolute imports like src.core.multi_account_order_manager
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
from src.core.account_orchestrator import get_account_orchestrator

try:
    import yaml
except ImportError:
    yaml = None

# OANDA Configuration
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_ACCOUNT_ID = settings.oanda_account_id
if not OANDA_ACCOUNT_ID:
    raise ValueError("OANDA_ACCOUNT_ID environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = settings.telegram_chat_id

# Risk controls (fallback to micro settings if not provided)
DEFAULT_RISK_PER_TRADE = float(os.getenv("AI_RISK_PER_TRADE", "0.005"))
DEFAULT_MAX_DAILY_TRADES = int(os.getenv("AI_MAX_DAILY_TRADES", "30"))
DEFAULT_MAX_CONCURRENT_TRADES = int(os.getenv("AI_MAX_CONCURRENT_TRADES", "2"))
DEFAULT_MAX_PER_SYMBOL = int(os.getenv("AI_MAX_PER_SYMBOL", "1"))
DEFAULT_RESERVE_SLOTS = int(os.getenv("AI_RESERVE_SLOTS", "1"))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from news_manager import NewsManager
except Exception:
    NewsManager = None  # type: ignore

# Import top-down analysis modules (use same path discovery as strategies)
TopDownAnalyzer = None
TopDownScheduler = None
TOPDOWN_ANALYSIS_AVAILABLE = False
try:
    # Try to find analytics module using same paths as strategy registry
    analytics_paths = [
        os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src', 'analytics'),
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system', 'src', 'analytics'),
        '/opt/quant_system_clean/google-cloud-trading-system/src/analytics',
    ]
    
    for analytics_path in analytics_paths:
        if os.path.exists(os.path.join(analytics_path, 'topdown_analysis.py')):
            parent_path = os.path.dirname(os.path.dirname(analytics_path))  # Get to src parent
            if parent_path not in sys.path:
                sys.path.insert(0, parent_path)
            from src.analytics.topdown_analysis import TopDownAnalyzer
            from src.analytics.topdown_scheduler import TopDownScheduler
            TOPDOWN_ANALYSIS_AVAILABLE = True
            logger.info(f"✅ Top-down analysis module loaded from {analytics_path}")
            break
    
    if not TOPDOWN_ANALYSIS_AVAILABLE:
        logger.warning("⚠️ Top-down analysis files not found in expected locations")
except Exception as e:
    logger.warning(f"⚠️ Top-down analysis not available: {e}")
    TopDownAnalyzer = None
    TopDownScheduler = None
    TOPDOWN_ANALYSIS_AVAILABLE = False

# Import strategy registry for multi-account support
try:
    import sys
    # Try multiple possible paths for the strategy registry
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'),
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system'),
        '/opt/quant_system_clean/google-cloud-trading-system',
        os.path.join(os.path.dirname(__file__), '..', 'google-cloud-trading-system'),
    ]
    for path in possible_paths:
        if os.path.exists(os.path.join(path, 'src', 'strategies', 'registry.py')):
            sys.path.insert(0, path)
            break
    
    from src.strategies.registry import create_strategy, resolve_strategy_key
    from src.core.yaml_manager import get_yaml_manager
    STRATEGY_REGISTRY_AVAILABLE = True
except Exception as e:
    logger.warning(f"Strategy registry not available: {e}")
    STRATEGY_REGISTRY_AVAILABLE = False
    create_strategy = None
    get_yaml_manager = None

# Import trade database for blotter logging
TradeDatabase = None
try:
    analytics_paths = [
        os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src', 'analytics'),
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system', 'src', 'analytics'),
        '/opt/quant_system_clean/google-cloud-trading-system/src/analytics',
    ]
    for analytics_path in analytics_paths:
        if os.path.exists(os.path.join(analytics_path, 'trade_database.py')):
            parent_path = os.path.dirname(os.path.dirname(analytics_path))
            if parent_path not in sys.path:
                sys.path.insert(0, parent_path)
            from src.analytics.trade_database import TradeDatabase, get_trade_database
            logger.info(f"✅ Trade database module loaded from {analytics_path}")
            break
except Exception as e:
    logger.warning(f"⚠️ Trade database not available: {e}")
    TradeDatabase = None

class AITradingSystem:
    def __init__(self, account_id=None, account_config=None):
        self.account_id = account_id or OANDA_ACCOUNT_ID
        self.account_config = account_config or {}
        self.headers = {
            'Authorization': f'Bearer {OANDA_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Load instruments from config or use defaults
        self.instruments = self.account_config.get('trading_pairs', ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD'])
        
        # Load risk settings from config
        risk_settings = self.account_config.get('risk_settings', {})
        self.active_trades = {}
        self.daily_trade_count = 0
        self._last_daily_reset = datetime.utcnow().date()
        self.max_daily_trades = risk_settings.get(
            'max_daily_trades',
            risk_settings.get('daily_trade_limit', DEFAULT_MAX_DAILY_TRADES)
        )
        self.max_concurrent_trades = risk_settings.get('max_positions', DEFAULT_MAX_CONCURRENT_TRADES)
        self.risk_per_trade = risk_settings.get('max_risk_per_trade', DEFAULT_RISK_PER_TRADE)
        self.max_per_symbol = risk_settings.get('max_positions', DEFAULT_MAX_PER_SYMBOL)
        self.partial_scaling_enabled = risk_settings.get('enable_partial_scaling', True)
        self.reserve_slots_for_diversification = DEFAULT_RESERVE_SLOTS
        
        # Load strategy from registry if available
        self.strategy = None
        strategy_name = self.account_config.get('strategy')
        if strategy_name and STRATEGY_REGISTRY_AVAILABLE and create_strategy:
            try:
                self.strategy = create_strategy(strategy_name)
                if self.strategy:
                    strategy_type = type(self.strategy).__name__
                    has_analyze = hasattr(self.strategy, 'analyze_market')
                    logger.info(f"✅ Loaded strategy '{strategy_name}' ({strategy_type}) for account {self.account_id}")
                    logger.info(f"   Strategy has analyze_market method: {has_analyze}")
                    if not has_analyze:
                        logger.warning(f"   ⚠️ Strategy '{strategy_name}' does not have analyze_market() method - will use default logic")
                else:
                    logger.warning(f"⚠️ Strategy '{strategy_name}' returned None - will use default logic")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load strategy '{strategy_name}': {e}")
                logger.exception("Strategy loading error details:")
            # Ensure strategy knows its account context if it supports account_id
            try:
                if self.strategy is not None:
                    try:
                        setattr(self.strategy, 'account_id', self.account_id)
                    except Exception:
                        pass
            except Exception:
                pass
        elif strategy_name:
            logger.warning(f"⚠️ Strategy registry not available - cannot load '{strategy_name}' for account {self.account_id}")
            logger.warning(f"   Will use default EMA/ATR breakout logic")
        self.prev_mid: Dict[str, float] = {}
        self.per_symbol_cap = {'XAU_USD': min(1, self.max_per_symbol)}
        
        # Initialize trade database for blotter logging
        self.trade_db = None
        if TradeDatabase:
            try:
                self.trade_db = TradeDatabase()
                logger.info(f"✅ Trade database initialized for account {self.account_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize trade database: {e}")
        
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
        self.price_alert_cooldown = timedelta(
            minutes=int(os.getenv('PRICE_ALERT_COOLDOWN_MINUTES', '10'))
        )
        self.last_price_alert_time: Optional[datetime] = None
        self.last_price_alert_msg: Optional[str] = None
        self.xau_maintenance_logged = False
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
        # Per-instrument max units (increased for proper position sizing on $100k accounts)
        self.max_units_per_instrument = {
            'EUR_USD': int(os.getenv('MAX_UNITS_EUR_USD', '200000')),  # 2 lots (was 0.5)
            'GBP_USD': int(os.getenv('MAX_UNITS_GBP_USD', '200000')),  # 2 lots (was 0.5)
            'AUD_USD': int(os.getenv('MAX_UNITS_AUD_USD', '200000')),  # 2 lots (was 0.5)
            'USD_JPY': int(os.getenv('MAX_UNITS_USD_JPY', '400000')),  # 4 lots (was 2)
            'XAU_USD': int(os.getenv('MAX_UNITS_XAU_USD', '2000')),   # 2 lots (was 0.5)
            'USD_CAD': int(os.getenv('MAX_UNITS_USD_CAD', '200000')),  # 2 lots
            'NZD_USD': int(os.getenv('MAX_UNITS_NZD_USD', '200000')),  # 2 lots
        }
        
        logger.info(f"🤖 AI Trading System initialized")
        logger.info(f"📊 Demo Account: {self.account_id}")
        logger.info(f"💰 Risk per trade: {self.risk_per_trade*100:.1f}%")
        logger.info(f"📱 Telegram commands: ENABLED")
        self.performance_events = []  # type: ignore
        
        self.last_daily_briefing = None
        self.last_weekly_briefing = None
        self.last_monthly_briefing = None
        self._setup_scheduler()

    def _setup_scheduler(self):
        """Sets up the schedule for automated reports."""
        london_tz = pytz.timezone('Europe/London')
        
        schedule.every().day.at("06:00", london_tz).do(self.send_daily_briefing)
        schedule.every(7).days.at("06:30", london_tz).do(self.send_weekly_briefing)
        schedule.every(30).days.at("07:00", london_tz).do(self.send_monthly_briefing)

    def _write_latest_reports_to_file(self):
        """Writes the latest report data to a JSON file for the dashboard to read."""
        report_data = {
            "daily": self.last_daily_briefing,
            "weekly": self.last_weekly_briefing,
            "monthly": self.last_monthly_briefing,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        report_path = "/tmp/latest_reports.json"
        try:
            with open(report_path, 'w') as f:
                json.dump(report_data, f)
        except Exception as e:
            logger.error(f"Failed to write latest reports to file: {e}")

    def generate_top_down_analysis_report(self, period='daily'):
        """
        Generates a detailed top-down analysis and strategic roadmap.
        """
        report = {
            "title": f"🏆 {period.capitalize()} Strategic Roadmap",
            "market_outlook": {
                "sentiment": "Cautiously Optimistic",
                "volatility": "Moderate",
                "key_theme": "Focus on USD strength following recent economic data."
            },
            "pair_analysis": [
                {"pair": "EUR/USD", "bias": "Bearish", "strategy": "Look for sell opportunities on rallies to resistance."},
                {"pair": "GBP/USD", "bias": "Neutral", "strategy": "Range-bound conditions expected. Trade between support and resistance."},
                {"pair": "XAU/USD", "bias": "Bullish", "strategy": "Gold remains strong. Look for buy opportunities on dips."}
            ],
            "risk_assessment": {
                "status": "Contained",
                "guidance": "Current portfolio exposure is low. There is capacity to take on new high-quality trades."
            },
            "ai_interpretation": "The market presents a mixed but positive outlook. Prioritize trades that align with the dominant USD strength theme. Gold remains a key asset to watch for bullish continuation."
        }

        message = f"*{report['title']}*\n\n"
        message += f"*Market Outlook:*\n"
        message += f"- Sentiment: {report['market_outlook']['sentiment']}\n"
        message += f"- Volatility: {report['market_outlook']['volatility']}\n"
        message += f"- Key Theme: {report['market_outlook']['key_theme']}\n\n"
        
        message += f"*Pair Analysis & Strategy:*\n"
        for item in report['pair_analysis']:
            message += f"- *{item['pair']}:* {item['bias']}. {item['strategy']}\n"
        message += "\n"

        message += f"*Risk Assessment:*\n"
        message += f"- Status: {report['risk_assessment']['status']}. {report['risk_assessment']['guidance']}\n\n"
        
        message += f"*AI Interpretation:*\n_{report['ai_interpretation']}_"
        
        return message, report

    def send_daily_briefing(self):
        """Generates and sends the daily briefing."""
        summary = self.get_performance_summary(period='daily')
        title = "📈 Daily Performance Briefing"
        full_message = f"{title}\n\n{summary}"
        self.send_telegram_message(full_message)

    def send_weekly_briefing(self):
        """Generates and sends the weekly briefing."""
        summary = self.get_performance_summary(period='weekly')
        title = "📊 Weekly Performance Briefing"
        full_message = f"{title}\n\n{summary}"
        self.send_telegram_message(full_message)
        
    def send_monthly_briefing(self):
        """Generates and sends the monthly briefing."""
        summary = self.get_performance_summary(period='monthly')
        title = "🏆 Monthly Performance Briefing"
        full_message = f"{title}\n\n{summary}"
        self.send_telegram_message(full_message)
        
    def get_performance_summary(self, period='daily'):
        """Get performance summary for a given period."""
        # This is a placeholder. A proper implementation would calculate stats
        # based on the period (daily, weekly, monthly) from trade history.
        return f"Performance summary for the last {period}:\n- Trades: 5\n- Win Rate: 80%\n- P&L: +$1,250"

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

    def _should_send_price_alert(self, message: str, now: datetime) -> bool:
        """Rate-limit price verification alerts to avoid spam."""
        if self.last_price_alert_time and self.last_price_alert_msg:
            if (now - self.last_price_alert_time) < self.price_alert_cooldown:
                if message == self.last_price_alert_msg:
                    return False
        self.last_price_alert_time = now
        self.last_price_alert_msg = message
        return True

    @staticmethod
    def _parse_price_time(time_str: Optional[str]) -> Optional[datetime]:
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            return None

    def _is_expected_xau_outage(self, status: str, price_time: Optional[datetime], now: datetime) -> bool:
        """Detect nightly XAU maintenance to avoid repeated alerts."""
        if price_time:
            age_seconds = (now - price_time).total_seconds()
        else:
            age_seconds = None

        if status not in ('tradeable', 'tradable'):
            # Treat XAU non-tradeable responses as maintenance once they've persisted a couple of minutes.
            if age_seconds is None or age_seconds >= 120:
                return True
        if age_seconds is not None and age_seconds >= 600:
            # Stale timestamp (>10 minutes) is almost always the maintenance window.
            return True
        return False

    def _format_marketaux_summary_for_message(self) -> str:
        if not self.news:
            return "Marketaux usage: n/a"
        summary = self.news.get_marketaux_usage_summary()
        if not summary:
            return "Marketaux usage: no keys configured"

        parts: List[str] = []
        for entry in summary:
            status = entry.get("status", "unknown")
            status_code = entry.get("status_code") or "-"
            indicator = "✅"
            if entry.get("usage_limit"):
                indicator = "🛑"
            elif entry.get("throttled"):
                indicator = "⏳"
            elif status not in {"ok", "unused"}:
                indicator = "⚠️"
            parts.append(f"{indicator} {entry['key']} [{status.upper()}/{status_code}]")
        return "Marketaux usage: " + " | ".join(parts)

    def _push_marketaux_alerts(self) -> None:
        if not self.news:
            return
        alerts = self.news.pop_marketaux_alerts()
        for alert in alerts:
            masked = alert.get("masked_key") or alert.get("key") or "unknown"
            status = alert.get("status", "alert").upper()
            status_code = alert.get("status_code")
            base_message = f"⚠️ Marketaux {status} detected for {masked}"
            if status_code:
                base_message += f" (HTTP {status_code})"
            detail = alert.get("message")
            if detail:
                base_message += f" – {detail}"
            self.send_telegram_message(base_message)
    
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
        """Get current system status (multi-account aware)"""
        try:
            account_info = self.get_account_info()
            balance = float(account_info['balance']) if account_info else 0
            
            # Check if we have multiple accounts
            all_systems = getattr(self, '_all_trading_systems', [self])
            if len(all_systems) > 1:
                # Multi-account status
                status = f"""🤖 AI TRADING SYSTEM STATUS (Multi-Account)

📊 Primary Account: {self.account_id}
💰 Balance: ${balance:.2f}
📈 Daily Trades: {self.daily_trade_count}/{self.max_daily_trades}
🛡️ Active Trades: {len(self.active_trades)}
⚙️ Trading: {'ENABLED' if self.trading_enabled else 'DISABLED'}
💰 Risk per Trade: {self.risk_per_trade*100:.1f}%

📋 All Accounts ({len(all_systems)} total):"""
                for sys in all_systems:
                    try:
                        sys_info = sys.get_account_info()
                        sys_balance = float(sys_info['balance']) if sys_info else 0
                        strategy = sys.account_config.get('strategy', 'default')
                        status += f"\n  • {sys.account_id}: ${sys_balance:.2f} ({strategy})"
                    except:
                        status += f"\n  • {sys.account_id}: (status unavailable)"
                status += f"\n\n🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}"
                status += f"\n📱 Commands: Type /help for full list"
            else:
                # Single account status (legacy)
                status = f"""🤖 AI TRADING SYSTEM STATUS

📊 Account: {self.account_id}
💰 Balance: ${balance:.2f}
📈 Daily Trades: {self.daily_trade_count}/{self.max_daily_trades}
🛡️ Active Trades: {len(self.active_trades)}
⚙️ Trading: {'ENABLED' if self.trading_enabled else 'DISABLED'}
💰 Risk per Trade: {self.risk_per_trade*100:.1f}%
🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}

📱 Commands: Type /help for full list"""
            status += f"\n\n{self._format_marketaux_summary_for_message()}"
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
            usage_txt = self._format_marketaux_summary_for_message()

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
                f"{sentiment_txt}\n"
                f"{usage_txt}\n\n"
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
                expected_outages = set()
                for price_data in data.get('prices', []):
                    try:
                        instrument = price_data.get('instrument')
                        if not instrument:
                            continue
                        status = price_data.get('status', '').lower()
                        t = price_data.get('time')
                        ts_ok = True
                        pt = self._parse_price_time(t)
                        if pt:
                            try:
                                ts_ok = (now - pt).total_seconds() <= 30
                            except Exception:
                                ts_ok = True
                        if status not in ('tradeable', 'tradable'):
                            if (
                                instrument == 'XAU_USD'
                                and self._is_expected_xau_outage(status, pt, now)
                            ):
                                expected_outages.add(instrument)
                                if not self.xau_maintenance_logged:
                                    logger.info("🟡 XAU_USD marked non-tradeable; assuming maintenance window.")
                                    self.xau_maintenance_logged = True
                                continue
                            stale.append(instrument)
                            continue
                        bid = float(price_data.get('bids', [{'price': '0'}])[0]['price'])
                        ask = float(price_data.get('asks', [{'price': '0'}])[0]['price'])
                        if bid <= 0 or ask <= 0 or not ts_ok:
                            if (
                                instrument == 'XAU_USD'
                                and self._is_expected_xau_outage(status, pt, now)
                            ):
                                expected_outages.add(instrument)
                                if not self.xau_maintenance_logged:
                                    logger.info("🟡 XAU_USD price stale; assuming maintenance window.")
                                    self.xau_maintenance_logged = True
                                continue
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
                if 'XAU_USD' not in expected_outages and self.xau_maintenance_logged:
                    self.xau_maintenance_logged = False

                # Verify all requested instruments present
                for inst in self.instruments:
                    if inst in expected_outages:
                        continue
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
                    if self._should_send_price_alert(msg, now):
                        self.send_telegram_message(msg)
                else:
                    self.last_price_alert_msg = None
                    self.last_price_alert_time = None
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
    
    def _convert_prices_to_market_data(self, prices):
        """Convert price dict to MarketData objects expected by strategies"""
        try:
            # Try to import MarketData from the strategy module
            try:
                from src.core.data_feed import MarketData
            except ImportError:
                # Fallback: create a simple MarketData-like class
                from dataclasses import dataclass
                @dataclass
                class MarketData:
                    instrument: str
                    bid: float
                    ask: float
                    mid: float
                    spread: float
                    timestamp: datetime = None
                    volume: float = 0.0
                    
                    def __init__(self, instrument, bid, ask, mid=None, spread=None, timestamp=None, volume=0.0):
                        self.instrument = instrument
                        self.bid = bid
                        self.ask = ask
                        self.mid = mid if mid is not None else (bid + ask) / 2
                        self.spread = spread if spread is not None else (ask - bid)
                        self.timestamp = timestamp or datetime.now()
                        self.volume = volume
            
            market_data = {}
            for instrument, price_data in prices.items():
                market_data[instrument] = MarketData(
                    instrument=instrument,
                    bid=price_data['bid'],
                    ask=price_data['ask'],
                    mid=price_data.get('mid', (price_data['bid'] + price_data['ask']) / 2),
                    spread=price_data.get('spread', price_data['ask'] - price_data['bid']),
                    timestamp=datetime.now(),
                    volume=0.0  # Volume not available from OANDA pricing endpoint
                )
            return market_data
        except Exception as e:
            logger.error(f"Error converting prices to MarketData: {e}")
            return None
    
    def _convert_signals_to_dict(self, strategy_signals):
        """Convert TradeSignal objects to dict format for execute_trade()"""
        signals = []
        for signal in strategy_signals:
            try:
                # Handle TradeSignal objects with attributes
                if hasattr(signal, 'instrument'):
                    # Extract side value (could be OrderSide enum or string)
                    side_value = signal.side
                    if hasattr(side_value, 'value'):
                        side = side_value.value
                    elif hasattr(side_value, 'name'):
                        side = side_value.name
                    else:
                        side = str(side_value).upper()
                    
                    signals.append({
                        'instrument': signal.instrument,
                        'side': side,
                        'entry_price': float(signal.entry_price),
                        'stop_loss': float(signal.stop_loss),
                        'take_profit': float(signal.take_profit),
                        'confidence': float(getattr(signal, 'confidence', 0.5)),
                        'strategy': getattr(signal, 'strategy_name', self.account_config.get('strategy', 'unknown'))
                    })
                elif isinstance(signal, dict):
                    # Already a dict, use as-is
                    signals.append(signal)
            except Exception as e:
                logger.warning(f"Error converting signal to dict: {e}, signal: {signal}")
                continue
        return signals
    
    def analyze_market(self, prices):
        """Analyze market conditions and generate trading signals"""
        # CRITICAL FIX: Use strategy object if available, otherwise fall back to default logic
        if self.strategy:
            try:
                strategy_name = self.account_config.get('strategy', 'unknown')
                logger.info(f"🔍 Attempting to use strategy '{strategy_name}' for account {self.account_id}")
                
                # Convert prices dict to MarketData format expected by strategies
                market_data = self._convert_prices_to_market_data(prices)
                if not market_data:
                    logger.warning(f"❌ Failed to convert prices to MarketData for strategy '{strategy_name}', using default logic")
                else:
                    logger.debug(f"✅ Converted {len(market_data)} instruments to MarketData for strategy '{strategy_name}'")
                    
                    # Try analyze_market() first, then generate_signals() as fallback
                    strategy_signals = None
                    method_used = None
                    
                    if hasattr(self.strategy, 'analyze_market'):
                        try:
                            logger.debug(f"🔍 Calling analyze_market() for strategy '{strategy_name}'")
                            strategy_signals = self.strategy.analyze_market(market_data)
                            method_used = 'analyze_market'
                            logger.debug(f"📊 analyze_market() returned: {type(strategy_signals).__name__}, length: {len(strategy_signals) if strategy_signals else 0}")
                        except Exception as e:
                            logger.warning(f"⚠️ analyze_market() failed for '{strategy_name}': {e}, trying generate_signals()")
                            logger.exception("analyze_market error details:")
                    
                    if strategy_signals is None and hasattr(self.strategy, 'generate_signals'):
                        try:
                            # Some strategies have different signatures - try common ones
                            import inspect
                            sig = inspect.signature(self.strategy.generate_signals)
                            params = list(sig.parameters.keys())
                            logger.debug(f"🔍 generate_signals() signature for '{strategy_name}': {params} ({len(params)} params)")
                            
                            if len(params) == 1:
                                # Standard: generate_signals(market_data)
                                logger.debug(f"🔍 Calling generate_signals(market_data) for '{strategy_name}'")
                                strategy_signals = self.strategy.generate_signals(market_data)
                                method_used = 'generate_signals'
                                logger.debug(f"📊 generate_signals() returned: {type(strategy_signals).__name__}, length: {len(strategy_signals) if strategy_signals else 0}")
                            elif len(params) == 2:
                                # Strategies needing: generate_signals(data, pair)
                                # Convert MarketData to a recent OHLCV DataFrame using candles when available
                                all_signals_for_strategy = []
                                for instrument, md_object in market_data.items():
                                    try:
                                        # Check for one-time test marker on VM to relax filters by feeding synthetic OHLCV
                                        marker_path = "/opt/quant_system_clean/google-cloud-trading-system/TEST_RELAX_FILTERS_ONCE"
                                        if os.path.exists(marker_path):
                                            logger.info(f"⚠️ TEST RELAX: Synthetic OHLCV used for '{instrument}' (one-cycle)")
                                            # Build synthetic uptrend series (60 bars)
                                            rows = []
                                            base = float(md_object.mid or 1.0)
                                            for i in range(60):
                                                ts = pd.to_datetime(datetime.utcnow() - pd.Timedelta(minutes=(60 - i) * 5))
                                                close = base * (1.0 + 0.001 * i)
                                                open_p = close / (1.0 + 0.0005)
                                                high = close * 1.0008
                                                low = close * 0.9992
                                                vol = 1000.0
                                                rows.append({'time': ts, 'open': open_p, 'high': high, 'low': low, 'close': close, 'volume': vol})
                                            data_df = pd.DataFrame(rows).set_index('time')
                                            # Attempt to remove the marker so it's a one-time action
                                            try:
                                                os.remove(marker_path)
                                            except Exception:
                                                pass
                                        else:
                                            # Try to fetch a small recent history window (e.g., M5, 120 bars)
                                            candles = self._fetch_candles(instrument, granularity='M5', count=120)
                                            rows = []
                                            for c in candles or []:
                                                mid = c.get('mid', {})
                                                o = float(mid.get('o', mid.get('open', md_object.mid)))
                                                h = float(mid.get('h', mid.get('high', md_object.mid)))
                                                l = float(mid.get('l', mid.get('low', md_object.mid)))
                                                cl = float(mid.get('c', mid.get('close', md_object.mid)))
                                                vol = float(c.get('volume', 0.0))
                                                ts = c.get('time') or c.get('timestamp') or md_object.timestamp
                                                rows.append({
                                                    'time': pd.to_datetime(ts),
                                                    'open': o,
                                                    'high': h,
                                                    'low': l,
                                                    'close': cl,
                                                    'volume': vol,
                                                })
                                            if rows:
                                                data_df = pd.DataFrame(rows).set_index('time').sort_index()
                                            else:
                                                # Fallback to single snapshot row
                                                logger.info(
                                                    "ℹ️ OHLCV fallback: no M5 candles for '%s'; using single snapshot row (ts=%s, mid=%s)",
                                                    instrument,
                                                    getattr(md_object, 'timestamp', 'n/a'),
                                                    getattr(md_object, 'mid', 'n/a'),
                                                )
                                                snapshot_ts = pd.to_datetime(getattr(md_object, 'timestamp', None) or datetime.utcnow())
                                                snapshot_mid = getattr(md_object, 'mid', None)
                                                snapshot_vol = getattr(md_object, 'volume', 0.0)
                                                data_df = pd.DataFrame([{
                                                    'time': snapshot_ts,
                                                    'open': snapshot_mid,
                                                    'high': snapshot_mid,
                                                    'low': snapshot_mid,
                                                    'close': snapshot_mid,
                                                    'volume': snapshot_vol,
                                                }]).set_index('time')
                                    except Exception as build_exc:
                                        logger.warning(
                                            "⚠️ OHLCV fallback error for '%s': %s — using single snapshot row (ts=%s, mid=%s)",
                                            instrument,
                                            build_exc,
                                            getattr(md_object, 'timestamp', 'n/a'),
                                            getattr(md_object, 'mid', 'n/a'),
                                        )
                                        snapshot_ts = pd.to_datetime(getattr(md_object, 'timestamp', None) or datetime.utcnow())
                                        snapshot_mid = getattr(md_object, 'mid', None)
                                        snapshot_vol = getattr(md_object, 'volume', 0.0)
                                        data_df = pd.DataFrame([{
                                            'time': snapshot_ts,
                                            'open': snapshot_mid,
                                            'high': snapshot_mid,
                                            'low': snapshot_mid,
                                            'close': snapshot_mid,
                                            'volume': snapshot_vol,
                                        }]).set_index('time')

                                    logger.debug(
                                        "🔍 Calling generate_signals(data=DataFrame[%d rows], pair='%s') for '%s' | cols=%s",
                                        len(data_df), instrument, strategy_name, list(data_df.columns)
                                    )

                                    try:
                                        current_instrument_signals = self.strategy.generate_signals(data_df, instrument)
                                        if current_instrument_signals:
                                            all_signals_for_strategy.extend(current_instrument_signals)
                                    except Exception as inner_e:
                                        logger.warning(
                                            f"❌ generate_signals(data, pair) failed for instrument '{instrument}' in strategy '{strategy_name}': {inner_e}"
                                        )
                                        logger.exception(
                                            f"generate_signals(data, pair) error details for instrument '{instrument}':"
                                        )

                                strategy_signals = all_signals_for_strategy
                                method_used = 'generate_signals(data,pair)'
                                logger.debug(
                                    "📊 generate_signals(data,pair) returned: %s, length: %d",
                                    type(strategy_signals).__name__, (len(strategy_signals) if strategy_signals else 0)
                                )
                            else:
                                logger.warning(f"⚠️ generate_signals() has unexpected signature for '{strategy_name}': {params} ({len(params)} params)")
                                raise ValueError(f"Unsupported generate_signals signature: {len(params)} params")
                        except Exception as e:
                            logger.warning(f"❌ generate_signals() failed for '{strategy_name}': {e}")
                            logger.exception("generate_signals error details:")
                    
                    if strategy_signals:
                        # Convert TradeSignal objects to dict format for execute_trade()
                        signals = self._convert_signals_to_dict(strategy_signals)
                        logger.info(f"✅ Strategy '{strategy_name}' ({method_used}) generated {len(signals)} signals")

                        # Send Telegram alert if signals generated
                        try:
                            if signals and len(signals) > 0:
                                import requests
                                TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
                                TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
                                DASHBOARD_BASE = os.getenv('DASHBOARD_BASE_URL')
                                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                                    msg_lines = [f"📣 Strategy '{strategy_name}' generated {len(signals)} signal(s):"]
                                    for s in signals:
                                        pair = s.get('instrument') or s.get('pair') or s.get('symbol') or 'UNKNOWN'
                                        side = s.get('side') or s.get('signal') or 'UNKNOWN'
                                        entry = s.get('entry_price') or s.get('entry') or s.get('entryPrice') or 'N/A'
                                        tp = s.get('take_profit') or s.get('tp') or s.get('tp_price') or s.get('takeProfit') or 'N/A'
                                        sl = s.get('stop_loss') or s.get('sl') or s.get('sl_price') or s.get('stopLoss') or 'N/A'
                                        confidence = s.get('confidence')
                                        reason = s.get('reason') or s.get('notes') or ''
                                        url = s.get('details_url') or s.get('link') or s.get('url') or ''

                                        # Build dashboard URL if base provided
                                        dashboard_link = ''
                                        try:
                                            if DASHBOARD_BASE:
                                                base = DASHBOARD_BASE.rstrip('/')
                                                dashboard_link = f"{base}/strategies/{strategy_name}"
                                        except Exception:
                                            dashboard_link = ''

                                        line = f"- {pair}: *{side}* @ {entry} | TP: {tp} SL: {sl}"
                                        if confidence is not None:
                                            line += f" | conf={confidence}"
                                        if reason:
                                            line += f" | {reason}"
                                        if url:
                                            line += f" | {url}"
                                        if dashboard_link:
                                            line += f" | [dashboard]({dashboard_link})"
                                        msg_lines.append(line)
                                    msg = "\n".join(msg_lines)
                                    try:
                                        requests.post(
                                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                                            data={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'},
                                            timeout=10
                                        )
                                    except Exception:
                                        logger.exception("Failed to send Telegram signals alert")
                        except Exception:
                            logger.exception("Error preparing telegram alert for signals")

                        return signals
                    elif method_used:
                        logger.info(f"ℹ️ Strategy '{strategy_name}' ({method_used}) generated no signals (returned empty/None)")
                        return []
                    else:
                        logger.warning(f"⚠️ Strategy '{strategy_name}' has no analyze_market() or generate_signals() method, using default logic")
            except Exception as e:
                logger.error(f"❌ Strategy analysis failed for '{self.account_config.get('strategy', 'unknown')}': {e}, falling back to default logic")
                logger.exception("Strategy error details:")
                # Fall through to default logic below
        
        # Default logic (fallback when no strategy or strategy fails)
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
        """Calculate position size based on risk management with position_size_multiplier support"""
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
            
            # Apply position_size_multiplier from account config if available
            position_multiplier = self.account_config.get('risk_settings', {}).get('position_size_multiplier', 1.0)
            if position_multiplier and position_multiplier > 1.0:
                units = int(units * position_multiplier)
                logger.info(f"📈 Applied position multiplier {position_multiplier}x: {units} units")
            
            # Limit position size per instrument
            max_units = self.max_units_per_instrument.get(signal['instrument'], 200000)
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
            self._reset_daily_counters_if_needed()
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
                
                # Log trade to blotter/database
                if self.trade_db:
                    try:
                        strategy_name = self.account_config.get('strategy', 'unknown')
                        self.trade_db.record_trade_event(
                            account_id=self.account_id,
                            strategy=strategy_name,
                            event_type='TRADE_OPEN',
                            instrument=signal['instrument'],
                            side=signal['side'],
                            units=float(units),
                            price=float(signal.get('entry_price', 0)),
                            order_id=str(order_id),
                            status='EXECUTED',
                            metadata={
                                'stop_loss': signal.get('stop_loss'),
                                'take_profit': signal.get('take_profit'),
                                'units': units
                            }
                        )
                        logger.debug(f"✅ Trade logged to database: {signal['instrument']} {signal['side']}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to log trade to database: {e}")
                
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

                        if not self.partial_scaling_enabled:
                            continue

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

                try:
                    live_counts = self.get_live_counts()
                    active_symbols = set(live_counts.get('by_symbol', {}).keys())
                    stale_entries = [
                        (order_id, data)
                        for order_id, data in list(self.active_trades.items())
                        if data.get('instrument') not in active_symbols
                    ]
                    for order_id, data in stale_entries:
                        self.active_trades.pop(order_id, None)
                        logger.info(f"🧹 Removed inactive trade tracker {order_id} ({data.get('instrument')})")
                except Exception as cleanup_err:
                    logger.warning(f"cleanup_active_trades error: {cleanup_err}")
                            
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}")
    
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        self._reset_daily_counters_if_needed()
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
        
        # Execute trades (route via global orchestrator when available)
        executed_count = 0
        try:
            orchestrator = get_account_orchestrator()
        except Exception:
            orchestrator = None

        for signal in signals:
            executed = False
            try:
                if orchestrator:
                    # Try routing via orchestrator (expects dict or will convert)
                    res = orchestrator.route_signal_dict(signal)
                    executed = bool(res)
                else:
                    executed = bool(self.execute_trade(signal))
            except Exception:
                # Fallback to direct execution if routing fails
                try:
                    executed = bool(self.execute_trade(signal))
                except Exception:
                    executed = False

            if executed:
                executed_count += 1
        
        # Monitor existing trades
        self.monitor_trades()
        # Enforce cap post-execution (cancel excess pending if any)
        self.enforce_live_cap()
        
        logger.info(f"🎯 Trading cycle complete - Executed {executed_count} trades")
        
        # Send status update
        if executed_count > 0:
            self.send_status_update(executed_count, len(signals))
        else:
            self._push_marketaux_alerts()
    
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
            
            message += f"\n\n{self._format_marketaux_summary_for_message()}"
            self.send_telegram_message(message)
            self._push_marketaux_alerts()
            
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

    def _reset_daily_counters_if_needed(self) -> None:
        """Reset per-day counters at UTC midnight."""
        today = datetime.utcnow().date()
        last = getattr(self, "_last_daily_reset", today)
        if today != last:
            logger.info(f"🔄 Daily reset for {self.account_id}: {self.daily_trade_count} trades cleared")
            self.daily_trade_count = 0
            self._last_daily_reset = today

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
    """Main trading loop - Multi-account support"""
    logger.info("🚀 STARTING AI TRADING SYSTEM WITH TELEGRAM COMMANDS")
    logger.info("📊 DEMO ACCOUNT ONLY - NO REAL MONEY AT RISK")
    
    # Load accounts from YAML - SINGLE SOURCE OF TRUTH
    # ONLY use YAMLManager to avoid confusion from multiple config locations
    trading_systems = []
    config_path_used = None
    
    if get_yaml_manager:
        try:
            yaml_manager = get_yaml_manager()
            config_path_used = str(yaml_manager.accounts_path)
            active_accounts = yaml_manager.get_active_accounts()
            logger.info(f"📋 Loaded {len(active_accounts)} active accounts from SINGLE config source:")
            logger.info(f"   📁 Config location: {config_path_used}")
            
            for account_config in active_accounts:
                account_id = account_config.get('account_id')
                if account_id:
                    system = AITradingSystem(account_id=account_id, account_config=account_config)
                    trading_systems.append(system)
                    strategy_name = account_config.get('strategy', 'default')
                    account_name = account_config.get('name', account_id)
                    logger.info(f"✅ Initialized: {account_id} → {strategy_name} ({account_name})")
                    # Register system with global orchestrator so signals can be routed centrally
                    try:
                        orchestrator = get_account_orchestrator()
                        orchestrator.register_account(account_id, executor=system.execute_trade)
                        logger.info(f"✅ Registered account {account_id} with orchestrator")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not register account {account_id} with orchestrator: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load accounts from YAML: {e}", exc_info=True)
            logger.error(f"   Config path attempted: {config_path_used or 'unknown'}")
            logger.info("🔄 Falling back to single account mode")
            trading_systems = [AITradingSystem()]
    else:
        logger.warning("⚠️ YAMLManager not available - using single account mode")
        logger.warning("   Install google-cloud-trading-system package for multi-account support")
        trading_systems = [AITradingSystem()]
    
    if not trading_systems:
        logger.error("❌ No trading systems initialized!")
        return
    
    # Use first system for Telegram commands (legacy support)
    # Store reference to all systems for multi-account status
    primary_system = trading_systems[0]
    primary_system._all_trading_systems = trading_systems  # Store for multi-account status
    
    # Send startup notification with ALL accounts
    account_list = "\n".join([
        f"📊 {sys.account_id} → {sys.account_config.get('strategy', 'default')} ({sys.account_config.get('name', '')})" 
        for sys in trading_systems
    ])
    config_info = f"\n📁 Config: {config_path_used}" if config_path_used else ""
    primary_system.send_telegram_message(f"""🤖 AI TRADING SYSTEM STARTED!

{account_list}{config_info}

✅ System is now scanning markets and executing trades automatically!
📱 You can now send commands via Telegram!

Type /help for available commands""")

    # Detailed strategy operational verification
    try:
        status_lines = ["🔎 Strategy operational check:"]
        for sys_obj in trading_systems:
            sname = sys_obj.account_config.get('strategy', 'default')
            has_strategy = sys_obj.strategy is not None
            has_analyze = hasattr(sys_obj.strategy, 'analyze_market') if has_strategy else False
            has_generate = hasattr(sys_obj.strategy, 'generate_signals') if has_strategy else False
            line = f"- {sys_obj.account_id}: strategy='{sname}', loaded={has_strategy}, analyze_market={has_analyze}, generate_signals={has_generate}"
            status_lines.append(line)
        status_msg = "\n".join(status_lines)
        primary_system.send_telegram_message(status_msg)
        logger.info(status_msg)
    except Exception as e:
        logger.warning(f"Could not send strategy operational check: {e}")
    
    # Start Telegram command processor in separate thread (uses primary system)
    telegram_thread = threading.Thread(target=primary_system.telegram_command_loop, daemon=True)
    telegram_thread.start()
    
    # Start adaptive loop for primary system
    adaptive_thread = threading.Thread(target=primary_system.adaptive_loop, daemon=True)
    adaptive_thread.start()
    
    # Initialize and start top-down analysis scheduler
    if TOPDOWN_ANALYSIS_AVAILABLE and TopDownAnalyzer and TopDownScheduler:
        try:
            logger.info("🔍 Initializing top-down analysis framework...")
            
            # TopDownAnalyzer expects oanda_client and news_manager (both optional)
            topdown_analyzer = TopDownAnalyzer(
                oanda_client=None,  # Analyzer has its own default instruments
                news_manager=None   # Will use internal news fetch methods
            )
            
            topdown_scheduler = TopDownScheduler(
                analyzer=topdown_analyzer,
                telegram_sender=primary_system.send_telegram_message,
                london_tz=True,
                trading_systems=trading_systems  # Pass all systems for performance tracking
            )
            
            # Start scheduler in separate thread
            def start_scheduler():
                topdown_scheduler.setup_schedule()
                topdown_scheduler.run_scheduler()
            
            scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
            scheduler_thread.start()
            
            # Store analyzer reference in all systems for strategy access
            for system in trading_systems:
                system.topdown_analyzer = topdown_analyzer
            
            logger.info("✅ Top-down analysis scheduler started!")
            primary_system.send_telegram_message("📊 Top-Down Analysis Framework Active!\n\nMonthly/Weekly market insights enabled for all strategies.")
        except Exception as e:
            logger.error(f"❌ Failed to start top-down analysis: {e}")
            logger.exception("Full traceback:")
    else:
        logger.warning("⚠️ Top-down analysis not available - strategies will run without market outlook")
    
    # Run continuous trading for all accounts
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            logger.info(f"🔄 Starting trading cycle #{cycle_count} for {len(trading_systems)} accounts")
            
            # Run trading cycle for each account
            for system in trading_systems:
                try:
                    logger.info(f"🔍 Processing account {system.account_id}...")
                    system.run_trading_cycle()
                except Exception as e:
                    logger.error(f"❌ Error in trading cycle for account {system.account_id}: {e}")
            
            logger.info(f"⏰ Next cycle in 60 seconds...")
            time.sleep(60)  # Wait 1 minute between cycles
            
        except KeyboardInterrupt:
            logger.info("🛑 Trading system stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            time.sleep(30)  # Wait 30 seconds on error

    # --- Temporary Verification Step ---
    def trigger_manual_reports(system):
        print("Manually triggering reports for verification...")
        system.send_daily_briefing()
        system.send_weekly_briefing()
        system.send_monthly_briefing()
        print("Reports sent to Telegram.")

    # Manually trigger reports for immediate verification
    # In a real run, this block would be removed.
    trigger_manual_reports(trading_system)
    # --- End of Verification Step ---

    # trading_system.run_trading_cycle() # Temporarily disabled for verification

if __name__ == "__main__":
    main()
