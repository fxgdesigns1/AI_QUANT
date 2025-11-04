#!/usr/bin/env python3
import os, sys, asyncio, textwrap
sys.path.insert(0, '.')
from datetime import datetime

# Load envs
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Also load dedicated news env if present
    news_env = os.path.join(os.getcwd(), 'news_api_config.env')
    if os.path.exists(news_env):
        load_dotenv(dotenv_path=news_env, override=False)
except Exception:
    pass

from src.core.news_integration import SafeNewsIntegration
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def fetch_news():
    ni = SafeNewsIntegration()
    data = await ni.get_news_data(['EUR_USD','GBP_USD','USD_JPY','XAU_USD'])
    return data or []

def send_telegram(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram env not set")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        print("Telegram status:", r.status_code, r.text[:120])
        return r.status_code == 200
    except Exception as e:
        print("Telegram error:", e)
        return False

async def main():
    items = await fetch_news()
    # Build concise digest from freshest items
    now = datetime.utcnow().strftime('%H:%M UTC')
    # Sort by published_at if provided
    def _ts(x):
        try:
            return x.get('published_at') or x.get('publishedAt') or x.get('time') or ''
        except Exception:
            return ''
    # Keep top 6 items
    top = items[:6]

    # Extract highlights
    lines = [f"📰 Live Market News ({now})"]
    added = 0
    trump_lines = []
    for it in top:
        title = it.get('title') or ''
        source = it.get('source') or it.get('site') or ''
        impact = (it.get('impact') or '').upper()
        summary = it.get('summary') or it.get('description') or ''
        if not title:
            continue
        bullet = f"- {title.strip()}"
        if source:
            bullet += f" ({source})"
        if impact:
            bullet += f" [{impact}]"
        lines.append(bullet)
        added += 1
        text_all = f"{title} {summary}".lower()
        if 'trump' in text_all:
            trump_lines.append(bullet)
        if added >= 5:
            break

    if not added:
        lines.append("- No high-confidence news returned by APIs just now.")

    # Trump section
    if trump_lines:
        lines.append("\n🇺🇸 Trump Watch:")
        lines.extend(trump_lines[:3])
    else:
        lines.append("\n🇺🇸 Trump Watch: No credible headlines in the last batch.")

    msg = "\n".join(lines)
    # Trim if too long
    if len(msg) > 3500:
        msg = msg[:3490] + "…"

    print("\n=== MESSAGE PREVIEW ===\n", msg)
    ok = send_telegram(msg)
    if not ok:
        print("Failed to deliver Telegram message.")

if __name__ == '__main__':
    asyncio.run(main())
