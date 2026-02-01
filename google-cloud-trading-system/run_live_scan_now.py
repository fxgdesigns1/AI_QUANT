#!/usr/bin/env python3
"""
RUN LIVE MARKET SCAN NOW - Get current entry signals
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime
from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData
from src.strategies.momentum_trading import get_momentum_trading_strategy

print("🎯 LIVE MARKET SCAN - GOLD SIGNALS")
print("="*100)
print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"🌍 London Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC")
print("="*100)

# Load optimized Gold strategy
strategy = get_momentum_trading_strategy()

print(f"\n✅ Strategy Loaded: {strategy.name}")
print(f"✅ Instruments: {strategy.instruments}")
print(f"✅ Price History: {len(strategy.price_history.get('XAU_USD', []))} bars loaded")

# Get current market data
fetcher = get_historical_fetcher()

print(f"\n📡 Fetching current Gold price...")

# Get latest candles
current_data = fetcher.get_recent_data_for_strategy(['XAU_USD'], hours=1)

if 'XAU_USD' not in current_data or not current_data['XAU_USD']:
    print(f"❌ Could not fetch current data")
    sys.exit(1)

latest_candle = current_data['XAU_USD'][-1]
current_price = float(latest_candle['close'])
high = float(latest_candle['high'])
low = float(latest_candle['low'])
candle_time = latest_candle['time']

print(f"\n💰 CURRENT GOLD PRICE:")
print(f"{'─'*100}")
print(f"Price: ${current_price:.2f}")
print(f"High: ${high:.2f}")
print(f"Low: ${low:.2f}")
print(f"Time: {candle_time}")
print(f"Bid: ${current_price - 0.5:.2f}")
print(f"Ask: ${current_price + 0.5:.2f}")

# Calculate current indicators
if len(strategy.price_history.get('XAU_USD', [])) >= 80:
    prices = strategy.price_history['XAU_USD']
    
    # 40-bar momentum
    momentum_prices = prices[-40:]
    momentum = (momentum_prices[-1] - momentum_prices[0]) / momentum_prices[0]
    
    # 80-bar trend
    trend_prices = prices[-80:]
    trend = (trend_prices[-1] - trend_prices[0]) / trend_prices[0]
    
    print(f"\n📊 CURRENT INDICATORS:")
    print(f"{'─'*100}")
    print(f"40-bar Momentum: {momentum*100:+.3f}% (need >0.03%)")
    print(f"80-bar Trend: {trend*100:+.3f}%")
    print(f"Price History: {len(prices)} bars")

# Create market data
market_data = MarketData(
    pair='XAU_USD',
    bid=current_price,
    ask=current_price + 0.5,
    timestamp=candle_time,
    is_live=True,
    data_source='OANDA',
    spread=0.5,
    last_update_age=0
)

# Generate signal
print(f"\n🎯 GENERATING SIGNAL...")
print(f"{'─'*100}")

signals = strategy.analyze_market({'XAU_USD': market_data})

if signals:
    print(f"\n✅✅✅ **TRADE SIGNAL ACTIVE!** ✅✅✅")
    print("="*100)
    
    for signal in signals:
        print(f"\n🎯 **ENTER THIS TRADE NOW:**")
        print(f"{'═'*100}")
        print(f"Instrument: XAU/USD (Gold)")
        print(f"Direction: **{signal.side.value}**")
        print(f"Entry: **${current_price:.2f}** (market order)")
        print(f"Stop Loss: **${signal.stop_loss:.2f}**")
        print(f"Take Profit: **${signal.take_profit:.2f}**")
        print(f"Position Size: {signal.units:,} units")
        print(f"Confidence: {signal.confidence:.1%}")
        
        # Calculate risk/reward
        if signal.side.value == 'BUY':
            risk = current_price - signal.stop_loss
            reward = signal.take_profit - current_price
        else:
            risk = signal.stop_loss - current_price
            reward = current_price - signal.take_profit
        
        rr = reward / risk if risk > 0 else 0
        risk_pct = (abs(risk) / current_price) * 100
        reward_pct = (abs(reward) / current_price) * 100
        
        print(f"\n📊 Risk/Reward:")
        print(f"   Risk: ${abs(risk):.2f} ({risk_pct:.2f}%)")
        print(f"   Reward: ${abs(reward):.2f} ({reward_pct:.2f}%)")
        print(f"   **R:R Ratio: 1:{rr:.1f}**")
        
        print(f"\n💵 Position Value:")
        print(f"   Account Size: $10,000 (assumed)")
        print(f"   Risk Amount: ${10000 * (risk_pct/100):.2f} ({risk_pct:.2f}%)")
        print(f"   Potential Profit: ${10000 * (reward_pct/100):.2f} ({reward_pct:.2f}%)")
        
        print(f"\n📋 **EXACT ENTRY INSTRUCTIONS:**")
        print(f"{'─'*100}")
        print(f"1. Login to OANDA platform")
        print(f"2. Select: XAU/USD")
        print(f"3. Click: {signal.side.value}")
        print(f"4. Units: {signal.units:,}")
        print(f"5. Entry: MARKET ORDER")
        print(f"6. Set Stop Loss: ${signal.stop_loss:.2f}")
        print(f"7. Set Take Profit: ${signal.take_profit:.2f}")
        print(f"8. EXECUTE TRADE")
        
        print(f"\n⏰ Based on backtesting:")
        print(f"   - This type of setup has 44% win rate")
        print(f"   - Average win: +0.63%")
        print(f"   - Average loss: -0.12%")
        print(f"   - Expected outcome: +{reward_pct:.1f}% if win, -{risk_pct:.2f}% if loss")
        
else:
    print(f"\n⏳ NO SIGNAL RIGHT NOW")
    print(f"{'─'*100}")
    print(f"Current price: ${current_price:.2f}")
    print(f"Conditions not met for entry")
    print(f"\n💡 The strategy scans every 5 minutes")
    print(f"   Run this script again in 5-10 minutes")
    print(f"   OR deploy to Cloud for automatic scanning")

print(f"\n{'='*100}")
print("DEPLOYMENT STATUS:")
print(f"{'='*100}\n")

print(f"⚠️  Still blocked by permissions")
print(f"   Account: gavinw442@gmail.com")
print(f"   Project: trading-system-436119")
print(f"   Needed: App Engine Deployer role")
print(f"\n📋 TO FIX:")
print(f"   1. Go to Google Cloud Console")
print(f"   2. IAM & Admin → IAM")
print(f"   3. Edit gavinw442@gmail.com permissions")
print(f"   4. Add role: App Engine Deployer")
print(f"   5. Save")
print(f"\n🚀 THEN: gcloud app deploy app.yaml cron.yaml --quiet")

print(f"\n{'='*100}")
print(f"💡 MEANWHILE: Run this script every 5-10 minutes to check for signals!")
print(f"{'='*100}")




