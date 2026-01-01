"""
Minimal Telegram notifier shim.
Provides the interface expected by core modules without external dependencies.
"""
from typing import Optional
import logging
import os
import requests
import re


logger = logging.getLogger(__name__)


def _escape_telegram_text(text: str) -> str:
    """Escapes special characters in text for Telegram MarkdownV2 parse mode."""
    # Telegram's MarkdownV2 requires escaping of specific characters outside of formatting
    # See: https://core.telegram.org/bots/api#markdownv2-style
    # Note: Only characters relevant for plain text, not for inside links/code blocks.
    # Using a slightly more aggressive escape for robustness given past issues.
    # Characters to escape: _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
    # For simplicity, we'll focus on the most common problematic ones for now.
    # If further issues arise, a more comprehensive escaping regex can be used.
    escaped_text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
    return escaped_text


class TelegramNotifier:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        logger.debug(f"[TelegramNotifier Init] Received token: {token}, chat_id: {chat_id}")

        env_token = os.getenv('TELEGRAM_BOT_TOKEN')
        env_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        logger.debug(f"[TelegramNotifier Init] Env token: {env_token}, Env chat_id: {env_chat_id}")

        self.token = token or env_token
        self.chat_id = chat_id or env_chat_id

        logger.debug(f"[TelegramNotifier Init] Final token: {self.token}, Final chat_id: {self.chat_id}")

        if not self.token:
            logger.warning("⚠️ Telegram BOT_TOKEN not found in config or environment. Telegram alerts will be disabled.")
        if not self.chat_id:
            logger.warning("⚠️ Telegram CHAT_ID not found in config or environment. Telegram alerts will be disabled.")

    def send_message(self, text: str) -> None:
        if not self.token or not self.chat_id:
            logger.warning(f"Telegram credentials missing. Cannot send message: {text}")
            return

        logger.info(f"[TelegramNotifier Send] Attempting to send message with token: {self.token} and chat_id: {self.chat_id[:5]}...{self.chat_id[-5:]}")

        try:
            telegram_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': _escape_telegram_text(text), # Apply escaping here
                'parse_mode': 'MarkdownV2' # Re-enable MarkdownV2 with escaping
            }
            
            response = requests.post(telegram_url, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors
            
            logger.info(f"✅ Telegram message sent successfully to chat ID {self.chat_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while sending Telegram message: {e}")


_singleton: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    global _singleton
    if _singleton is None:
        # Pass environment variables directly upon singleton creation
        # This is primarily for consistency, as TelegramNotifier's __init__ also checks os.getenv
        _singleton = TelegramNotifier(
            token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID')
        )
    return _singleton


__all__ = ["TelegramNotifier", "get_telegram_notifier"]







