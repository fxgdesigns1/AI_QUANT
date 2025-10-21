#!/usr/bin/env python3
"""
Premium Telegram Notifier - Sends premium signals with approve/reject buttons
"""

import logging
import requests
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PremiumTelegramNotifier:
    """
    Sends premium signals to Telegram with inline approve/reject buttons
    """
    
    def __init__(self, bot_token: str, chat_id: str, webhook_url: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.webhook_url = webhook_url
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        logger.info("✅ Premium Telegram Notifier initialized")
    
    def send_premium_signal(self, signal) -> bool:
        """
        Send premium signal with approve/reject buttons
        """
        try:
            # Format the signal message
            stars = "⭐" * min(int(signal.score / 20), 5)
            
            # Calculate pips/points
            if 'XAU' in signal.instrument:
                tp_distance = abs(signal.tp_price - signal.entry_price)
                sl_distance = abs(signal.entry_price - signal.sl_price)
                unit = "$"
            elif 'JPY' in signal.instrument:
                tp_distance = abs(signal.tp_price - signal.entry_price) * 100
                sl_distance = abs(signal.entry_price - signal.sl_price) * 100
                unit = " pips"
            else:
                tp_distance = abs(signal.tp_price - signal.entry_price) * 10000
                sl_distance = abs(signal.entry_price - signal.sl_price) * 10000
                unit = " pips"
            
            message = f"""🎯 PREMIUM SIGNAL #{signal.id.split('_')[-1]}
━━━━━━━━━━━━━━━━━━━━━━━

📊 {signal.instrument} {signal.direction}
Quality Score: {signal.score}/100 {stars}

💰 Entry: {signal.entry_price:.5f}
🎯 Take Profit: {signal.tp_price:.5f} (+{tp_distance:.1f}{unit})
🛑 Stop Loss: {signal.sl_price:.5f} (-{sl_distance:.1f}{unit})
📈 Risk/Reward: {signal.r_r_ratio:.1f}:1

🧠 REASONING:
{signal.reasoning}

⏰ Time: {signal.timestamp.strftime('%H:%M:%S')} London
━━━━━━━━━━━━━━━━━━━━━━━

⬇️ YOUR DECISION:"""
            
            # Create inline keyboard with approve/reject buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ APPROVE & EXECUTE", "callback_data": f"approve_{signal.id}"},
                        {"text": "❌ REJECT", "callback_data": f"reject_{signal.id}"}
                    ]
                ]
            }
            
            # Send message
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "reply_markup": keyboard,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Premium signal sent to Telegram: {signal.instrument}")
                return True
            else:
                logger.error(f"❌ Telegram send failed: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error sending premium signal: {e}")
            return False
    
    def send_execution_confirmation(self, signal, order_result) -> bool:
        """
        Send confirmation that trade was executed
        """
        try:
            message = f"""✅ TRADE EXECUTED
━━━━━━━━━━━━━━━━━━━━━━━

📊 {signal.instrument} {signal.direction}
💰 Entry: {signal.entry_price:.5f}
🎯 TP: {signal.tp_price:.5f}
🛑 SL: {signal.sl_price:.5f}

Trade ID: {order_result.get('id', 'N/A')}
Units: {order_result.get('units', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━
Good luck! 🍀"""
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"❌ Error sending execution confirmation: {e}")
            return False
    
    def send_rejection_confirmation(self, signal) -> bool:
        """
        Send confirmation that signal was rejected
        """
        try:
            message = f"""❌ SIGNAL REJECTED

📊 {signal.instrument} {signal.direction}
Score: {signal.score}/100

Not executed. Looking for next opportunity...
━━━━━━━━━━━━━━━━━━━━━━━"""
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"❌ Error sending rejection confirmation: {e}")
            return False
    
    def send_daily_summary(self, signals_found: int, signals_approved: int, signals_rejected: int) -> bool:
        """
        Send end-of-day summary
        """
        try:
            message = f"""📊 DAILY PREMIUM SIGNALS SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━

🔍 Signals Found: {signals_found}
✅ Approved & Executed: {signals_approved}
❌ Rejected: {signals_rejected}

Approval Rate: {(signals_approved/signals_found*100) if signals_found > 0 else 0:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━
See you tomorrow! 👋"""
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"❌ Error sending daily summary: {e}")
            return False


# Global instance
_premium_notifier = None

def get_premium_notifier(bot_token=None, chat_id=None, webhook_url=None):
    """Get or create premium notifier instance"""
    global _premium_notifier
    if _premium_notifier is None and bot_token and chat_id:
        _premium_notifier = PremiumTelegramNotifier(bot_token, chat_id, webhook_url)
    return _premium_notifier


if __name__ == '__main__':
    print("Premium Telegram Notifier - Ready")



