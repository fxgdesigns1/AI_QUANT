import requests

TOKEN = "${TELEGRAM_TOKEN}"
CHAT_ID = "${TELEGRAM_CHAT_ID}"

message = """📊 ACCOUNT STATUS - RIGHT NOW

✅ CURRENT POSITIONS:

Gold (009): 0 trades (clean, ready)
Ultra Strict (010): 1 trade (GBP_USD -$33)
GBP #2 (007): 0 trades (clean, ready)
GBP #1 (008): 0 trades (clean, ready)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 PENDING ORDERS:

Account 010: 2 pending orders
  • Stop Loss for GBP trade
  • Take Profit for GBP trade

All others: NO pending orders

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔮 WHAT THEY'RE PREPPING FOR:

🥇 GOLD (009):
Watching: $3,980 support
Ready for: 2-3 scalps today
Targets: 15, 30, 50 pips
Imminent: Next volatility spike

💱 EUR/USD (010):
Watching: 1.0800 support (uptrend)
Ready for: BUY dips
Targets: 15, 30, 50 pips
Imminent: Eurozone data reactions

💷 GBP/USD (010, 007, 008):
Watching: 1.2500 level
CRITICAL: THURSDAY BoE DECISION! 🚨
Ready for: 50-100 pip breakout
Imminent: THURSDAY = HUGE EVENT!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ IMMINENT EVENTS:

TODAY: Gold scalping opportunities
THIS WEEK: Thursday BoE = GBP explosion
NEXT WEEK: US CPI (inflation data)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 ALL READY:

• Gold DNA entries active
• Small targets set (15, 30, 50 pips)
• Multi-stage exits ready
• Big win protection armed
• Waiting for 85%+ signals!

Patient like Gold strategy! 🎯
"""

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message}, timeout=10)

if response.status_code == 200:
    print("✅ Status update sent to Telegram!")
else:
    print(f"❌ Failed: {response.status_code}")
