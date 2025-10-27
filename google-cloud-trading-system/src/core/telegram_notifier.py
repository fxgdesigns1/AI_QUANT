#!/usr/bin/env python3
"""
Telegram Notification System
Production-ready Telegram notifications for trading alerts
"""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TelegramMessage:
    """Telegram message structure"""
    text: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class TelegramNotifier:
    """Production Telegram notification system with rate limiting"""
    
    def __init__(self):
        """Initialize Telegram notifier"""
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.token and self.chat_id and 
                          self.token != 'your_telegram_bot_token_here' and
                          self.chat_id != 'your_telegram_chat_id_here')
        
        # Rate limiting to prevent spam
        self.last_message_time = {}
        self.min_interval_seconds = 300  # 5 minutes between similar messages
        self.daily_message_count = 0
        self.max_daily_messages = 20  # Max 20 messages per day
        
        if self.enabled:
            self.base_url = f"https://api.telegram.org/bot{self.token}"
            logger.info("✅ Telegram notifier initialized with rate limiting")
            logger.info(f"📱 Chat ID: {self.chat_id}")
            logger.info(f"⏱️ Rate limit: {self.min_interval_seconds}s between similar messages")
            logger.info(f"📊 Daily limit: {self.max_daily_messages} messages")
        else:
            logger.warning("⚠️ Telegram notifier disabled - missing or invalid configuration")
    
    def _should_send_message(self, message_type: str) -> bool:
        """Check if message should be sent based on rate limiting"""
        if not self.enabled:
            return False
        
        # Check daily limit
        if self.daily_message_count >= self.max_daily_messages:
            logger.debug(f"📊 Daily message limit reached ({self.max_daily_messages}), skipping {message_type}")
            return False
        
        # Check rate limiting for similar messages
        now = datetime.now()
        if message_type in self.last_message_time:
            time_since_last = (now - self.last_message_time[message_type]).total_seconds()
            if time_since_last < self.min_interval_seconds:
                logger.debug(f"⏱️ Rate limited: {message_type} (last sent {time_since_last:.0f}s ago)")
                return False
        
        return True
    
    def send_message(self, message, message_type: str = "general") -> bool:
        """Send message to Telegram with rate limiting"""
        if not self._should_send_message(message_type):
            return False
        
        try:
            # Handle both string and TelegramMessage objects
            if isinstance(message, str):
                text = message
                parse_mode = "HTML"
                disable_web_page_preview = True
            else:
                text = message.text
                parse_mode = message.parse_mode
                disable_web_page_preview = message.disable_web_page_preview
            
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            # Update rate limiting
            self.last_message_time[message_type] = datetime.now()
            self.daily_message_count += 1
            
            logger.info(f"✅ Telegram message sent ({self.daily_message_count}/{self.max_daily_messages}): {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def send_trade_alert(self, account_name: str, instrument: str, side: str, 
                        price: float, confidence: float, strategy: str) -> bool:
        """Send trade execution alert"""
        emoji = "🟢" if side.upper() == "BUY" else "🔴"
        side_emoji = "📈" if side.upper() == "BUY" else "📉"
        
        message_text = f"""
{emoji} <b>TRADE EXECUTED</b> {side_emoji}

<b>Account:</b> {account_name}
<b>Strategy:</b> {strategy}
<b>Instrument:</b> {instrument}
<b>Side:</b> {side.upper()}
<b>Price:</b> {price:.5f}
<b>Confidence:</b> {confidence:.2%}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

#TradingAlert #{account_name.replace(' ', '')} #{instrument.replace('_', '')}
        """.strip()
        
        message = TelegramMessage(text=message_text)
        return self.send_message(message, "trade_alert")
    
    def send_daily_summary(self, account_stats: Dict[str, Dict]) -> bool:
        """Send daily trading summary"""
        total_pl = sum(stats.get('realized_pl', 0) for stats in account_stats.values())
        total_trades = sum(stats.get('trades_today', 0) for stats in account_stats.values())
        
        message_text = f"""
📊 <b>DAILY TRADING SUMMARY</b>

<b>Total P&L:</b> {total_pl:+.2f} GBP
<b>Total Trades:</b> {total_trades}
<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}

<b>Account Breakdown:</b>
        """.strip()
        
        for account_name, stats in account_stats.items():
            pl = stats.get('realized_pl', 0)
            trades = stats.get('trades_today', 0)
            balance = stats.get('account_balance', 0)
            
            pl_emoji = "🟢" if pl >= 0 else "🔴"
            message_text += f"\n{pl_emoji} <b>{account_name}:</b> {pl:+.2f} GBP ({trades} trades)"
        
        message_text += f"\n\n#DailySummary #{datetime.now().strftime('%Y%m%d')}"
        
        message = TelegramMessage(text=message_text)
        return self.send_message(message, "daily_summary")
    
    def send_market_alert(self, alert_type: str, instrument: str, message: str) -> bool:
        """Send market alert"""
        emoji_map = {
            'opportunity': '🎯',
            'warning': '⚠️',
            'info': 'ℹ️',
            'error': '❌'
        }
        
        emoji = emoji_map.get(alert_type, '📢')
        
        message_text = f"""
{emoji} <b>MARKET ALERT</b>

<b>Type:</b> {alert_type.upper()}
<b>Instrument:</b> {instrument}
<b>Message:</b> {message}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

#MarketAlert #{instrument.replace('_', '')}
        """.strip()
        
        telegram_message = TelegramMessage(text=message_text)
        return self.send_message(telegram_message, "market_alert")
    
    def send_system_status(self, status: str, details: str = "") -> bool:
        """Send system status update"""
        emoji_map = {
            'online': '✅',
            'offline': '❌',
            'error': '⚠️',
            'warning': '🔶'
        }
        
        emoji = emoji_map.get(status, '📊')
        
        message_text = f"""
{emoji} <b>SYSTEM STATUS</b>

<b>Status:</b> {status.upper()}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        if details:
            message_text += f"\n<b>Details:</b> {details}"
        
        message_text += f"\n\n#SystemStatus"
        
        message = TelegramMessage(text=message_text)
        return self.send_message(message, "system_status")
    
    def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            bot_info = response.json()
            logger.info(f"✅ Telegram bot connected: @{bot_info['result']['username']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram connection test failed: {e}")
            return False
    
    def reset_daily_counter(self):
        """Reset daily message counter (call at midnight)"""
        self.daily_message_count = 0
        logger.info("🔄 Daily Telegram message counter reset")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        return {
            'daily_messages': self.daily_message_count,
            'max_daily_messages': self.max_daily_messages,
            'remaining_today': self.max_daily_messages - self.daily_message_count,
            'rate_limit_seconds': self.min_interval_seconds
        }
    
    def send_metrics_update(self, account_name: str, win_rate: float, profit_factor: float, success_rate: float) -> bool:
        """Send trading metrics update"""
        message_text = f"""
📊 <b>TRADING METRICS UPDATE</b>

<b>Account:</b> {account_name}
<b>Win Rate:</b> {win_rate:.1%}
<b>Profit Factor:</b> {profit_factor:.2f}
<b>Success Rate:</b> {success_rate:.1%}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

#MetricsUpdate #{account_name.replace(' ', '')}
        """.strip()
        
        message = TelegramMessage(text=message_text)
        return self.send_message(message, "metrics_update")
    
    def send_news_alert(self, title: str, impact: str, time_until: str, pairs: List[str]) -> bool:
        """Send news alert"""
        emoji_map = {
            'high': '🚨',
            'medium': '⚠️',
            'low': 'ℹ️'
        }
        
        emoji = emoji_map.get(impact, '📢')
        
        message_text = f"""
{emoji} <b>NEWS ALERT</b>

<b>Title:</b> {title}
<b>Impact:</b> {impact.upper()}
<b>Time Until:</b> {time_until}
<b>Pairs:</b> {', '.join(pairs)}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

#NewsAlert #{impact.upper()}
        """.strip()
        
        message = TelegramMessage(text=message_text)
        return self.send_message(message, "news_alert")
    
    def send_alert(self, message: str, priority: str = "NORMAL") -> bool:
        """Send a general alert message"""
        if not self.enabled:
            return False
        
        # Map priority to message type
        message_type = "high_priority" if priority.upper() == "HIGH" else "general"
        
        # Add priority indicator to message
        if priority.upper() == "HIGH":
            message = f"🚨 **HIGH PRIORITY** 🚨\n\n{message}"
        elif priority.upper() == "MEDIUM":
            message = f"⚠️ **MEDIUM PRIORITY** ⚠️\n\n{message}"
        
        message_obj = TelegramMessage(text=message)
        return self.send_message(message_obj, message_type)

# Global Telegram notifier instance
telegram_notifier = TelegramNotifier()

def get_telegram_notifier() -> TelegramNotifier:
    """Get the global Telegram notifier instance"""
    return telegram_notifier
