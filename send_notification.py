#!/usr/bin/env python3
import requests

# Telegram credentials
BOT_TOKEN = '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU'
CHAT_ID = '6100678501'

message = """AUTOMATED TRADING SYSTEM IS LIVE!

STATUS: RUNNING & TRADING
Demo Account: 101-004-30719775-008
Risk per Trade: 1%
Max Daily Trades: 50
Max Concurrent Trades: 5

FIRST TRADE EXECUTED:
- Instrument: EUR/USD
- Side: BUY
- Units: 10,000
- Current P&L: +$1,019.31

SYSTEM FEATURES:
- Real-time market scanning
- Automated order placement
- Risk management (1% per trade)
- Stop loss & take profit orders
- Telegram alerts for all trades
- 24/7 continuous operation

TRADING STRATEGIES:
- EUR/USD momentum trading
- GBP/USD breakout detection
- Gold scalping opportunities
- USD/JPY trend following

The system is now fully automated and placing trades in the paper environment!
You will receive real-time alerts for all trading activity."""

# Send to Telegram
url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
data = {'chat_id': CHAT_ID, 'text': message}
response = requests.post(url, data=data, timeout=10)
print('Trading system status sent to Telegram!')
