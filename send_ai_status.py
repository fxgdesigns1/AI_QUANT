#!/usr/bin/env python3
import requests

# Telegram credentials
BOT_TOKEN = '7248728383:REDACTED'
CHAT_ID = '6100678501'

message = """🤖 AI TRADING SYSTEM WITH TELEGRAM COMMANDS IS LIVE!

STATUS: RUNNING & RESPONDING TO COMMANDS
Demo Account: 101-004-30719775-008
Current P&L: +$976.49

✅ NEW AI FEATURES:
- Reads Telegram messages in real-time
- Executes commands instantly
- Responds with live data
- Controls trading system remotely

📱 AVAILABLE COMMANDS:
/status - System status
/balance - Account balance
/positions - Open positions
/trades - Recent trades
/start_trading - Enable trading
/stop_trading - Disable trading
/trade EUR_USD BUY - Manual trade
/risk 0.01 - Set risk per trade
/market - Market analysis
/performance - Performance summary
/help - Full command list

🎯 AI CAPABILITIES:
- Real-time market analysis
- Automated trade execution
- Risk management control
- Position monitoring
- Performance tracking
- Emergency controls

The AI is now fully interactive and will respond to all your commands!
Try sending /status to see the system respond in real-time."""

# Send to Telegram
url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
data = {'chat_id': CHAT_ID, 'text': message}
response = requests.post(url, data=data, timeout=10)
print('AI Trading System status sent to Telegram!')
