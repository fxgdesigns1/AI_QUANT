from __future__ import annotations

import os
from typing import Optional

import requests


class TelegramError(RuntimeError):
    pass


def _env(name: str) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else None


def send_telegram_message(text: str, *, timeout_s: float = 10.0) -> dict:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not token:
        raise TelegramError("Missing required env var: TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise TelegramError("Missing required env var: TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=timeout_s)
    if r.status_code != 200:
        raise TelegramError(f"Telegram error {r.status_code}: {r.text[:200]}")
    data = r.json() if r.text else {}
    if not data.get("ok"):
        raise TelegramError(f"Telegram response not ok: {str(data)[:200]}")
    return data
