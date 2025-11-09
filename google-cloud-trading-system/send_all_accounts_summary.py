#!/usr/bin/env python3
import requests

TOKEN = "${TELEGRAM_TOKEN}"
CHAT_ID = "${TELEGRAM_CHAT_ID}"

message = """ALL 5 ACCOUNTS ACTIVE - COMPLETE BREAKDOWN

STRATEGY COMPETITION ROSTER:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Gold Scalping (009) - CHAMPION

Instrument: XAU_USD
Balance: $86,148
Targets: +$1,723-$5,169/week (2-6%)
Max DD: -$2,584/day (3%)

Strategy:
  • Tight stops: 6 pips
  • Small targets: 15, 30, 50 pips
  • Max 5 trades/day
  • Pullback entries only
  • 85%+ signal strength

Economic Factors:
  • Fed policy (USD strength)
  • Safe-haven demand
  • Inflation expectations
  • Central bank buying

This Week:
  • Range: $3,960-$4,040
  • 2-3 scalps/day expected
  • Small wins compound

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. Ultra Strict Forex (010)

Instruments: EUR_USD, GBP_USD
Balance: $79,027
Targets: +$1,581-$4,742/week (2-6%)
Max DD: -$2,371/day (3%)

EUR_USD:
  • Uptrend (Eurozone GDP 1.5%)
  • BUY dips to 1.0800
  • ECB turning hawkish
  • 2-3 trades/week expected

GBP_USD:
  • BoE THURSDAY decision!
  • 50-100 pip move expected
  • Wait for announcement
  • Trade breakout after

Strategy:
  • Tight stops: 8 pips
  • Small targets: 15, 30, 50 pips
  • Max 10 trades/day
  • 85%+ quality

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. GBP Strategy #2 (007)

Instrument: GBP_USD
Balance: $90,537
Targets: +$1,811-$5,432/week (2-6%)
Max DD: -$2,716/day (3%)

Strategy:
  • Tight stops: 8 pips
  • Small targets: 15, 25, 40 pips
  • RSI: 25-80 (balanced)
  • Max 10 trades/day
  • 85%+ quality

This Week Focus:
  • THURSDAY BoE decision!
  • 50-100 pip breakout
  • This is THE opportunity
  • Could make weekly target in 1 day!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. GBP Strategy #1 (008)

Instrument: GBP_USD
Balance: $94,263
Targets: +$1,885-$5,656/week (2-6%)
Max DD: -$2,828/day (3%)

Strategy:
  • Tight stops: 8 pips
  • Small targets: 15, 25, 40 pips
  • RSI: 20-80 (most aggressive)
  • Max 10 trades/day
  • 85%+ quality

This Week Focus:
  • Same as #2 - BoE Thursday!
  • More aggressive RSI = more entries
  • Target 35.90 Sharpe ratio

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Momentum USD/JPY (011) - RE-ENABLED!

Instrument: USD_JPY
Balance: $119,552
Targets: +$2,391-$7,172/week (2-6%)
Max DD: -$3,586/day (3%)

STRICT SAFEGUARDS:
  • ONLY BUY (uptrend only!)
  • Max 1 position (testing)
  • Max 3 trades/day
  • 1% risk (conservative)
  • 85%+ quality (Gold DNA)

Market Analysis:
  • USD/JPY: 145.60 (uptrend)
  • BoJ: Ultra-dovish (Yen weak)
  • Fed: Tightening (USD strong)
  • Policy gap widening

Entry Zones:
  • BUY: 145.00-145.50 (dips only)
  • NO SELLS! (would fight trend)
  • Targets: 15, 30, 50 pips

This Week:
  • Test with 1 trade max
  • Prove trend logic fixed
  • If profitable, increase next week

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PORTFOLIO TOTAL:

5 accounts active
5 instruments covered:
  • XAU_USD (Gold)
  • EUR_USD (Euro)
  • GBP_USD (Pound) - 3 strategies!
  • USD_JPY (Yen) - RE-ENABLED

Weekly Target: +$9,380-$28,141 (2-6%)
All with Gold DNA + small targets!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU'LL GET NOTIFIED:

✅ When ANY account gets 85%+ signal
✅ Immediate entry alerts
✅ Partial profit alerts (Layers 2, 3, 4)
✅ Big win protection (>$1,000)
✅ Exit notifications

Plus:
  • 6 AM: All 5 analyzed individually
  • 9:30 PM: All 5 results reported
  • Sundays: Weekly competition rankings

FULL COVERAGE - All accounts, all instruments!
"""

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={'chat_id': CHAT_ID, 'text': message}, timeout=10)

if response.status_code == 200:
    print("✅ Complete portfolio summary sent to Telegram!")
else:
    print(f"❌ Failed: {response.status_code}")
