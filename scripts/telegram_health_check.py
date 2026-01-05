#!/usr/bin/env python3
"""
Telegram Health Check - Gated and Safe

Gates:
- SECRETS_ROTATED_OK=true AND TELEGRAM_TEST_APPROVED=true required
- Refuses placeholder tokens (REDACTED, your_, __, etc.)
- Never prints token values (only length)
- Provides safe diagnostics for 404 and other errors
"""

import os
import sys
import time
import requests

def is_placeholder(value: str) -> bool:
    """Check if value is a placeholder pattern"""
    if not value or not value.strip():
        return True
    
    value_lower = value.lower().strip()
    
    # Common placeholder patterns
    placeholder_patterns = [
        'redacted', 'your_', '__', 'placeholder', 'replace_me', 
        'insert_here', 'example', 'demo', 'test_token'
    ]
    
    return any(pattern in value_lower for pattern in placeholder_patterns)


def main() -> int:
    # Gate 1: Check if secrets rotation approved and test approved
    secrets_rotated = os.environ.get('SECRETS_ROTATED_OK', '').strip().lower() == 'true'
    test_approved = os.environ.get('TELEGRAM_TEST_APPROVED', '').strip().lower() == 'true'
    
    if not (secrets_rotated and test_approved):
        print('TELEGRAM_LOCKED: Set SECRETS_ROTATED_OK=true AND TELEGRAM_TEST_APPROVED=true to run test.')
        print('This prevents accidental token exposure during rotation.')
        return 0  # Exit 0 = skipped, not error
    
    # Gate 2: Get tokens
    bot = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    
    if not bot or not chat:
        print('ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing')
        return 2
    
    # Gate 3: Refuse placeholders
    if is_placeholder(bot):
        print(f'ERROR: TELEGRAM_BOT_TOKEN appears to be a placeholder (detected placeholder pattern)')
        print(f'Token length: {len(bot)} chars')
        return 2
    
    if is_placeholder(chat):
        print(f'ERROR: TELEGRAM_CHAT_ID appears to be a placeholder (detected placeholder pattern)')
        return 2
    
    # Never print token - only length
    print(f'Token length: {len(bot)} chars')
    print(f'Chat ID length: {len(chat)} chars')
    
    # Test 1: getMe (sanity probe)
    getme_url = f"https://api.telegram.org/bot{bot}/getMe"
    try:
        getme_r = requests.get(getme_url, timeout=10)
        getme_ok = False
        getme_data = {}
        try:
            getme_data = getme_r.json()
            getme_ok = bool(getme_data.get('ok'))
        except Exception:
            pass
        
        if not getme_ok:
            print(f'getMe FAILED: status_code={getme_r.status_code}')
            if getme_r.text:
                # Truncate response body for diagnosis (max 300 chars)
                body_preview = getme_r.text[:300]
                print(f'Response preview: {body_preview}')
            return 1
        else:
            bot_info = getme_data.get('result', {})
            bot_username = bot_info.get('username', 'unknown')
            print(f'getMe OK: bot @{bot_username}')
    except requests.exceptions.RequestException as e:
        print(f'getMe ERROR: {type(e).__name__}: {str(e)[:200]}')
        return 1
    
    # Test 2: sendMessage
    send_url = f"https://api.telegram.org/bot{bot}/sendMessage"
    text = f"AI_QUANT health check UTC={int(time.time())}"
    
    try:
        r = requests.post(send_url, json={'chat_id': chat, 'text': text}, timeout=15)
        ok = False
        response_data = {}
        try:
            response_data = r.json()
            ok = bool(response_data.get('ok'))
        except Exception:
            pass
        
        if r.status_code == 200 and ok:
            print(f'sendMessage OK: message_id={response_data.get("result", {}).get("message_id", "unknown")}')
            return 0
        else:
            print(f'sendMessage FAILED: status_code={r.status_code} ok={ok}')
            if r.text:
                # Truncate response body for diagnosis (max 300 chars)
                body_preview = r.text[:300]
                print(f'Response preview: {body_preview}')
            return 1
    except requests.exceptions.RequestException as e:
        print(f'sendMessage ERROR: {type(e).__name__}: {str(e)[:200]}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
