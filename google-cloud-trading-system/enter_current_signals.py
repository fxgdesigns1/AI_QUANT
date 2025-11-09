#!/usr/bin/env python3
"""
Get current signals from Trump DNA strategy and enter them with proper lot sizing
"""

import os, sys, yaml
sys.path.insert(0, '.')

# Load credentials
with open('app.yaml') as f:
    config = yaml.safe_load(f)
    os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
with open('accounts.yaml') as f:
    accounts = yaml.safe_load(f)
    os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"

from src.core.oanda_client import OandaClient
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.core.data_feed import MarketData
from src.core.telegram_notifier import TelegramNotifier
from src.core.order_manager import OrderManager

# Initialize
client = OandaClient(os.environ['OANDA_API_KEY'], os.environ['OANDA_ACCOUNT_ID'], 'practice')
strategy = MomentumTradingStrategy()
account_info = client.get_account_info()
balance = account_info.balance

print("\n" + "="*70)
print("CURRENT MARKET SIGNALS - TRUMP DNA STRATEGY")
print("="*70)
print(f"Account Balance: ${balance:,.2f}")
print(f"Risk Per Trade: 1.0%")
print("="*70 + "\n")

# Get current prices and build market data
instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
market_data_dict = {}

for instrument in instruments:
    result = client.get_candles(instrument, granularity='M5', count=1)
    candle = result['candles'][0]
    
    market_data_dict[instrument] = MarketData(
        pair=instrument,
        bid=float(candle['bid']['c']),
        ask=float(candle['ask']['c']),
        spread=float(candle['ask']['c']) - float(candle['bid']['c']),
        timestamp=candle['time'],
        is_live=True,
        data_source='OANDA',
        last_update_age=0
    )

# Generate signals
signals = strategy.analyze_market(market_data_dict)

print(f"Signals Generated: {len(signals)}\n")

if not signals:
    print("⏸️ No signals from Trump DNA strategy right now")
    print("Market conditions don't meet quality threshold")
    sys.exit(0)

# Process each signal
orders_placed = []
telegram_msg = f"""🎯 **TRADE SIGNALS EXECUTED - {len(signals)} Positions**\n\n"""

for i, signal in enumerate(signals, 1):
    instrument = signal.instrument
    direction = signal.side.value
    current_price = market_data_dict[instrument].bid
    sl = signal.stop_loss
    tp = signal.take_profit
    
    # Calculate position size
    sl_distance = abs(current_price - sl)
    dollar_risk = balance * 0.01  # 1% risk
    
    if instrument == 'XAU_USD':
        units = int(dollar_risk / sl_distance)
    else:
        pip_value = 10 if 'JPY' in instrument else 10000
        units = int((dollar_risk / sl_distance) * pip_value)
    
    # For OANDA, SELL = negative units
    oanda_units = -units if direction == 'SELL' else units
    
    profit_if_win = units * abs(current_price - tp)
    loss_if_lose = units * sl_distance
    
    print(f"{'='*70}")
    print(f"SIGNAL #{i}: {instrument} {direction}")
    print(f"{'='*70}")
    print(f"Entry: {current_price:.5f}")
    print(f"Stop Loss: {sl:.5f}")
    print(f"Take Profit: {tp:.5f}")
    print(f"Position Size: {units:,} units")
    print(f"Risk: ${loss_if_lose:,.2f} | Reward: ${profit_if_win:,.2f}")
    print(f"R:R = 1:{abs(current_price-tp)/sl_distance:.1f}")
    
    # Place order on DEMO account
    try:
        order_result = client.create_market_order(
            instrument=instrument,
            units=oanda_units,
            stop_loss_price=sl,
            take_profit_price=tp
        )
        
        print(f"✅ ORDER PLACED!")
        print(f"   Order ID: {order_result.get('orderFillTransaction', {}).get('id', 'N/A')}")
        
        orders_placed.append({
            'instrument': instrument,
            'direction': direction,
            'units': units,
            'entry': current_price,
            'sl': sl,
            'tp': tp,
            'risk': loss_if_lose,
            'reward': profit_if_win
        })
        
        telegram_msg += f"""**#{i} - {instrument} {direction}**
📍 Entry: {current_price:.5f}
🛑 SL: {sl:.5f} | 🎯 TP: {tp:.5f}
💰 Size: {units:,} units
💵 Risk: \${loss_if_lose:,.2f} | Reward: \${profit_if_win:,.2f}
✅ ORDER PLACED

"""
        
    except Exception as e:
        print(f"❌ ORDER FAILED: {str(e)}")
        telegram_msg += f"""**#{i} - {instrument} {direction}**
❌ Order failed: {str(e)}

"""
    
    print()

# Send summary to Telegram
telegram_msg += f"""**Total:** {len(orders_placed)} orders placed
**Account:** ${balance:,.2f}
**Total Risk:** ${sum(o['risk'] for o in orders_placed):,.2f}

Monitor positions and update at 5 PM! 📊"""

notifier = TelegramNotifier()
notifier.send_system_status(f'{len(orders_placed)} Trades Entered', telegram_msg)

print("="*70)
print(f"✅ {len(orders_placed)} ORDERS PLACED")
print(f"📱 Telegram notification sent")
print("="*70)




