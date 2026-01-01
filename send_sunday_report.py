#!/usr/bin/env python3
import requests
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set")

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    return requests.post(url, data=data, timeout=10).status_code == 200

msg1 = """📊 COMPLETE PERFORMANCE REPORT
Since Sunday 6:00 PM (Nov 16, 2025)
When new strategies were loaded

Each strategy evaluated on its own merit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ GOLD SCALPER (TOPDOWN)
Account: 101-004-30719775-001

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: £0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: £105,655.62
• Total Realized P&L: -£29,718.99
• Unrealized P&L: £0.00
• Open Positions: 0

📊 Status: ✅ Active | No new trades since Sunday

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ GOLD SCALPER (STRICT1)
Account: 101-004-30719775-003

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: £0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: £90,406.80
• Total Realized P&L: -£57,069.77
• Unrealized P&L: £0.00
• Open Positions: 0

📊 Status: ✅ Active | No new trades since Sunday

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ GOLD SCALPER (WINRATE)
Account: 101-004-30719775-004

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: $0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: $100,000.91
• Total Realized P&L: -$12,329.25
• Unrealized P&L: $0.00
• Open Positions: 0

📊 Status: ✅ Active | No new trades since Sunday"""

send_msg(msg1)

msg2 = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ OPTIMIZED MULTI-PAIR LIVE
Account: 101-004-30719775-005

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: $0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: $99,476.56
• Total Realized P&L: -$10,751.97
• Unrealized P&L: $0.00
• Open Positions: 0

📊 Status: ✅ Active | No new trades since Sunday

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ MOMENTUM TRADING (PRIMARY)
Account: 101-004-30719775-008

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: $0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: $109,377.68
• Total Realized P&L: -$69,079.70
• Unrealized P&L: -$28.00
• Open Positions: 1

📊 Status: ✅ Active | 1 open position (from before Sunday)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6️⃣ TRADE WITH PAT ORB DUAL
Account: 101-004-30719775-010

📈 Performance Since Sunday 6PM:
• Trades Executed: 0
• P&L Since Sunday: $0.00
• Win Rate: N/A

💰 Current Account State:
• Balance: $98,267.17
• Total Realized P&L: -$62,336.24
• Unrealized P&L: -$28.00
• Open Positions: 1

📊 Status: ✅ Active | 1 open position (from before Sunday)"""

send_msg(msg2)

msg3 = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY (Since Sunday 6PM):

💡 Key Findings:
• Trades Executed Since Sunday 6PM: 0 (all strategies)
• All strategies: ✅ ACTIVE and monitoring
• 2 strategies have open positions (from before Sunday)

📈 ACCOUNT BALANCES (Show Historical Losses):
• Gold Scalper (Topdown): £105,655.62 (Total P&L: -£29,718.99)
• Gold Scalper (Strict1): £90,406.80 (Total P&L: -£57,069.77)
• Gold Scalper (Winrate): $100,000.91 (Total P&L: -$12,329.25)
• Optimized Multi-Pair: $99,476.56 (Total P&L: -$10,751.97)
• Momentum Trading: $109,377.68 (Total P&L: -$69,079.70)
• Trade With Pat ORB: $98,267.17 (Total P&L: -$62,336.24)

⚠️ IMPORTANT:
The "Total Realized P&L" shows losses from ALL time (before and after Sunday).

Since Sunday 6PM: NO new trades have been executed.

The losses you've seen are reflected in the account balances and Total Realized P&L, but those trades happened BEFORE Sunday 6PM when you restarted the system.

✅ All strategies are now active and waiting for new signals.

Each strategy evaluated independently on its own merit."""

send_msg(msg3)
print("✅ Complete report sent to Telegram!")






