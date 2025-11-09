#!/usr/bin/env python3
"""
Find ALL current opportunities (quality >40) and enter with proper sizing
"""

import os, sys, yaml
sys.path.insert(0, '.')

with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"

from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import TelegramNotifier
from datetime import datetime

def calculate_momentum(prices, period):
    if len(prices) < period:
        return 0
    return (prices[-1] - prices[-period]) / prices[-period]

def calculate_adx_simple(prices, period=14):
    if len(prices) < period + 1:
        return 0
    up_moves = []
    down_moves = []
    for i in range(len(prices) - period, len(prices)):
        if i > 0:
            change = prices[i] - prices[i-1]
            up_moves.append(max(change, 0))
            down_moves.append(max(-change, 0))
    avg_up = sum(up_moves) / len(up_moves) if up_moves else 0
    avg_down = sum(down_moves) / len(down_moves) if down_moves else 0
    if avg_up + avg_down == 0:
        return 0
    return abs(avg_up - avg_down) / (avg_up + avg_down) * 100

# Initialize
client = OandaClient(os.environ['OANDA_API_KEY'], os.environ['OANDA_ACCOUNT_ID'], 'practice')
account_info = client.get_account_info()
balance = account_info.balance

print("\n" + "="*70)
print(f"FINDING OPPORTUNITIES - {datetime.now().strftime('%A %H:%M London')}")
print("="*70)
print(f"Account: ${balance:,.2f}")
print(f"Risk Per Trade: 1.0% = ${balance * 0.01:,.2f}")
print("="*70 + "\n")

instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
opportunities = []

for instrument in instruments:
    print(f"Scanning {instrument}...")
    
    result = client.get_candles(instrument, granularity='M5', count=100)
    candles = result['candles']
    prices = [float(c['bid']['c']) for c in candles]
    
    current_price = prices[-1]
    mom_1h = calculate_momentum(prices, 12)
    mom_4h = calculate_momentum(prices, 48)
    adx = calculate_adx_simple(prices, 14)
    
    # Determine direction (LOWERED threshold from 0.001 to 0.0005)
    if mom_1h > 0.0005 and mom_4h > 0.0003:
        direction = "BUY"
        strength = (mom_1h + mom_4h) / 2
    elif mom_1h < -0.0005 and mom_4h < -0.0003:
        direction = "SELL"
        strength = abs((mom_1h + mom_4h) / 2)
    else:
        print(f"  ⏸️ Weak momentum (1H: {mom_1h*100:.3f}%, 4H: {mom_4h*100:.3f}%)\n")
        continue
    
    # Calculate SL/TP
    recent_range = max(prices[-20:]) - min(prices[-20:])
    atr = recent_range / 20
    
    if direction == "BUY":
        entry = current_price
        sl = entry - (atr * 2.5)
        tp = entry + (atr * 10)
    else:
        entry = current_price
        sl = entry + (atr * 2.5)
        tp = entry - (atr * 10)
    
    # Position sizing
    sl_distance = abs(entry - sl)
    dollar_risk = balance * 0.01
    
    if instrument == 'XAU_USD':
        units = int(dollar_risk / sl_distance)
    else:
        pip_value = 10 if 'JPY' in instrument else 10000
        units = int((dollar_risk / sl_distance) * pip_value)
    
    profit_if_win = units * abs(entry - tp)
    loss_if_lose = units * sl_distance
    rr = abs(entry - tp) / sl_distance
    
    # Quality score
    quality = 0
    if adx > 20:
        quality += 30
    elif adx > 10:
        quality += 15
    if abs(mom_1h) > 0.002:
        quality += 30
    elif abs(mom_1h) > 0.001:
        quality += 20
    elif abs(mom_1h) > 0.0005:
        quality += 10
    if mom_1h * mom_4h > 0:
        quality += 20
    if rr > 3:
        quality += 20
    
    # Accept quality >40 (lowered from 50)
    if quality < 40:
        print(f"  ⏸️ Quality {quality}/100 (need 40+)\n")
        continue
    
    opportunities.append({
        'instrument': instrument,
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'units': units,
        'risk': loss_if_lose,
        'reward': profit_if_win,
        'rr': rr,
        'quality': quality,
        'adx': adx,
        'mom_1h': mom_1h * 100,
        'mom_4h': mom_4h * 100
    })
    
    print(f"  ✅ {direction} - Quality: {quality}/100, ADX: {adx:.1f}, Mom: {mom_1h*100:.3f}%")
    print(f"     Units: {units:,}, Risk: ${loss_if_lose:,.2f}, Reward: ${profit_if_win:,.2f}\n")

# Rank by quality
opportunities.sort(key=lambda x: x['quality'], reverse=True)

print("="*70)
print(f"FOUND {len(opportunities)} OPPORTUNITIES")
print("="*70 + "\n")

if not opportunities:
    print("⏸️ No quality setups right now. Market too choppy.")
    sys.exit(0)

# Enter trades
telegram_msg = f"""🎯 **{len(opportunities)} TRADES ENTERED** - {datetime.now().strftime('%A %H:%M')}\n\n"""

for i, opp in enumerate(opportunities, 1):
    oanda_units = -opp['units'] if opp['direction'] == 'SELL' else opp['units']
    
    print(f"Entering #{i}: {opp['instrument']} {opp['direction']}...")
    
    try:
        order = client.place_market_order(
            instrument=opp['instrument'],
            units=oanda_units,
            stop_loss=opp['sl'],
            take_profit=opp['tp']
        )
        
        print(f"  ✅ PLACED!\n")
        
        telegram_msg += f"""**#{i} - {opp['instrument']} {opp['direction']}** (Q: {opp['quality']}/100)
📍 Entry: {opp['entry']:.5f}
🛑 SL: {opp['sl']:.5f} | 🎯 TP: {opp['tp']:.5f}
💰 Size: {opp['units']:,} units
💵 Risk: ${opp['risk']:,.2f} | Reward: ${opp['reward']:,.2f}
📊 R:R = 1:{opp['rr']:.1f}
📈 ADX: {opp['adx']:.1f}, Mom: {opp['mom_1h']:.2f}%
✅ ORDER PLACED

"""
    except Exception as e:
        print(f"  ❌ FAILED: {str(e)}\n")
        telegram_msg += f"""**#{i} - {opp['instrument']} {opp['direction']}**
❌ Failed: {str(e)}

"""

telegram_msg += f"""**Account:** ${balance:,.2f}
**Total Positions:** {len(opportunities)}

I'll monitor and update you at 5 PM! 📊"""

notifier = TelegramNotifier()
notifier.send_system_status('Trades Entered', telegram_msg)

print("="*70)
print("✅ DONE - Check Telegram for summary!")
print("="*70)

