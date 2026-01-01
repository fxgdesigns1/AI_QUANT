#!/usr/bin/env python3
"""
Extract all trades from logs and OANDA, create comprehensive report
"""
import requests
import json
import subprocess
import os
from datetime import datetime
import pytz
from collections import defaultdict

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set")

API_KEY = os.getenv('OANDA_API_KEY')
if not API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
BASE_URL = os.getenv('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

london_tz = pytz.timezone('Europe/London')
sunday_eve = london_tz.localize(datetime(2025, 11, 16, 18, 0, 0))
sunday_eve_utc = sunday_eve.astimezone(pytz.UTC)

# Strategy mapping
strategy_map = {
    '101-004-30719775-001': 'Gold Scalper (Topdown)',
    '101-004-30719775-003': 'Gold Scalper (Strict1)',
    '101-004-30719775-004': 'Gold Scalper (Winrate)',
    '101-004-30719775-005': 'Optimized Multi-Pair Live',
    '101-004-30719775-008': 'Momentum Trading',
    '101-004-30719775-010': 'Trade With Pat ORB Dual',
    '101-004-30719775-011': 'Dynamic Multi-Pair Unified',
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    return requests.post(url, data=data, timeout=10).status_code == 200

# Get all accounts
response = requests.get(f'{BASE_URL}/v3/accounts', headers=headers, timeout=10)
all_accounts = [acc['id'] for acc in response.json().get('accounts', [])]

all_trades_summary = {}

for account_id in all_accounts:
    strategy_name = strategy_map.get(account_id, f'Account {account_id}')
    
    try:
        # Get ALL transactions (no time filter to catch everything)
        tx_response = requests.get(
            f'{BASE_URL}/v3/accounts/{account_id}/transactions',
            headers=headers,
            params={'state': 'ALL'},
            timeout=15
        )
        
        if tx_response.status_code == 200:
            all_transactions = tx_response.json().get('transactions', [])
            
            # Filter since Sunday
            since_sunday = []
            for t in all_transactions:
                t_time = t.get('time', '')
                if t_time:
                    try:
                        t_dt = datetime.fromisoformat(t_time.replace('Z', '+00:00'))
                        if t_dt >= sunday_eve_utc:
                            since_sunday.append(t)
                    except:
                        pass
            
            # Get fills and closes
            fills = [t for t in since_sunday if t.get('type') == 'ORDER_FILL']
            closes = [t for t in since_sunday if t.get('type') in ['TRADE_CLOSE', 'TAKE_PROFIT_ORDER_FILLED', 'STOP_LOSS_ORDER_FILLED']]
            
            # Calculate P&L
            total_pl = sum(float(t.get('pl', 0)) for t in closes)
            wins = sum(1 for t in closes if float(t.get('pl', 0)) > 0)
            losses = sum(1 for t in closes if float(t.get('pl', 0)) < 0)
            
            # Get current state
            summary_response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/summary', headers=headers, timeout=10)
            summary = summary_response.json().get('account', {}) if summary_response.status_code == 200 else {}
            
            trades_response = requests.get(f'{BASE_URL}/v3/accounts/{account_id}/openTrades', headers=headers, timeout=10)
            open_trades = trades_response.json().get('trades', []) if trades_response.status_code == 200 else []
            
            if fills or closes or open_trades:
                all_trades_summary[account_id] = {
                    'strategy': strategy_name,
                    'fills': len(fills),
                    'closes': len(closes),
                    'total_pl': round(total_pl, 2),
                    'wins': wins,
                    'losses': losses,
                    'win_rate': round((wins / len(closes) * 100) if closes else 0, 2),
                    'balance': round(float(summary.get('balance', 0)), 2),
                    'unrealized_pl': round(float(summary.get('unrealizedPL', 0)), 2),
                    'open_positions': len(open_trades),
                    'recent_closes': closes[-10:] if closes else []
                }
    except Exception as e:
        all_trades_summary[account_id] = {'error': str(e)}

# Build report
msg_parts = []
msg_parts.append("📊 COMPLETE TRADE REPORT\nSince Sunday 6PM (Nov 16, 2025)\n\nEach strategy on its own merit.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

for account_id, data in all_trades_summary.items():
    if 'error' in data:
        continue
    
    msg = f"""\n{data['strategy']}\nAccount: {account_id}\n\n📈 Since Sunday 6PM:\n• Trades Opened: {data['fills']}\n• Trades Closed: {data['closes']}\n• Total P&L: {data['total_pl']}\n• Wins: {data['wins']} | Losses: {data['losses']}\n• Win Rate: {data['win_rate']}%\n\n💰 Current State:\n• Balance: {data['balance']}\n• Unrealized P&L: {data['unrealized_pl']}\n• Open Positions: {data['open_positions']}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    msg_parts.append(msg)

# Send in chunks
full_msg = "\n".join(msg_parts)
if len(full_msg) > 4000:
    # Split
    chunk = ""
    for part in msg_parts:
        if len(chunk + part) > 4000:
            send_telegram(chunk)
            chunk = part
        else:
            chunk += part
    if chunk:
        send_telegram(chunk)
else:
    send_telegram(full_msg)

# Summary
total_fills = sum(d.get('fills', 0) for d in all_trades_summary.values() if 'error' not in d)
total_closes = sum(d.get('closes', 0) for d in all_trades_summary.values() if 'error' not in d)
total_pl = sum(d.get('total_pl', 0) for d in all_trades_summary.values() if 'error' not in d)

summary_msg = f"""\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📊 TOTAL SUMMARY:\n• Total Trades Opened: {total_fills}\n• Total Trades Closed: {total_closes}\n• Total P&L: {total_pl}\n\n⚠️ NOTE: Blotter system is NOT logging trades.\nThis report extracted from OANDA API directly.\n\nI will now fix the blotter system."""

send_telegram(summary_msg)
print("✅ Complete trade report sent!")






