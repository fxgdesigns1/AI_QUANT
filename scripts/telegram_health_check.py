import os, time, requests

def main() -> int:
    bot = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if not bot or not chat:
        print('missing: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID')
        return 2

    url = f"https://api.telegram.org/bot{bot}/sendMessage"
    text = f"AI_QUANT health check UTC={int(time.time())}"
    r = requests.post(url, json={'chat_id': chat, 'text': text}, timeout=15)
    ok = False
    try:
        ok = bool(r.json().get('ok'))
    except Exception:
        ok = False
    print(f"status_code={r.status_code} ok={ok}")
    return 0 if (r.status_code == 200 and ok) else 1

if __name__ == '__main__':
    raise SystemExit(main())
