#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse


def send_message(text: str) -> bool:
    token = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN') or '${TELEGRAM_TOKEN}'
    chat_id = os.getenv('TELEGRAM_CHAT_ID') or '${TELEGRAM_CHAT_ID}'
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True,
    }
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            _ = resp.read()
        return True
    except Exception:
        return False



