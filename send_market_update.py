#!/usr/bin/env python3
import requests
from datetime import datetime

# Telegram credentials
BOT_TOKEN = '${TELEGRAM_TOKEN}'
CHAT_ID = '${TELEGRAM_CHAT_ID}'

message = f"""📊 MARKET UPDATE
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

💰 ACCOUNT STATUS:
• Balance: $46,765.39
• Unrealized P&L: +$513.04 ✅
• Total Equity: $47,278.43
• Performance: +1.1% profit

📈 CURRENT POSITIONS:
• EUR/USD LONG: 496,934 units
  P&L: +$495.14 ✅ (recovering from drawdown)

• GBP/USD LONG: 40,000 units
  P&L: +$17.90 ✅ (new position)

🎯 MARKET CONDITIONS:
• EUR/USD: 1.16460 (spread: 0.7 pips)
  Status: BUY signal active (above 1.0500)
  Trend: BULLISH momentum

• GBP/USD: 1.32191 (spread: 1.0 pip)
  Status: BUY signal active (above 1.2500)
  Trend: BULLISH momentum

• Gold: $4,026.66 (spread: $0.88)
  Status: Spread too wide - monitoring only
  Note: Anti-chasing active (no entries after pump)

• USD/JPY: 152.277 (spread: 1.6 pips)
  Status: Spread acceptable but no signal

• AUD/USD: 0.66016 (spread: 1.4 pips)
  Status: Monitoring (no signal generated)

🤖 AI SYSTEM STATUS:
• Trading Cycles: 123+ completed
• Active Positions: 2/5 slots used
• Diversification: ✅ ACTIVE (EUR + GBP)
• Risk Management: ✅ PROTECTING PROFITS
• Anti-Chasing: ✅ ACTIVE (Gold blocked)

📊 KEY OBSERVATIONS:
1. EUR/USD position recovering nicely (+$495)
2. GBP/USD new position opened (+$18)
3. Gold spread too wide - waiting for better entry
4. Max positions reached (2/5) - diversification working
5. System not chasing pumps - smart risk management

🎯 NEXT MONITORING:
• Wait for Gold spread to narrow below $0.60
• Monitor EUR/USD for profit protection triggers
• Watch for GBP/USD continuation
• System ready for new opportunities

The AI is performing well with conservative, diversified approach!"""

# Send to Telegram
url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
data = {'chat_id': CHAT_ID, 'text': message}
response = requests.post(url, data=data, timeout=10)
print('Market update sent to Telegram!')
