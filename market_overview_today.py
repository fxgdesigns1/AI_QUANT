#!/usr/bin/env python3
"""
Market Overview - Today's Analysis
Shows what's happening, opportunities, and lessons learned
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "google-cloud-trading-system"))

# Try to import with credentials
try:
    from dotenv import load_dotenv
    load_dotenv('google-cloud-trading-system/oanda_config.env')
    
    from src.core.oanda_client import OandaClient
    from src.core.data_feed import DataFeed
    import pandas as pd
    
    CREDENTIALS_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Limited mode: {e}")
    CREDENTIALS_AVAILABLE = False

# London timezone
LONDON_TZ = pytz.timezone('Europe/London')

def get_london_time():
    """Get current time in London"""
    return datetime.now(LONDON_TZ)

def format_time(dt):
    """Format datetime for display"""
    return dt.strftime('%H:%M:%S %Z on %A, %B %d, %Y')

def check_session():
    """Determine current trading session"""
    now = get_london_time()
    hour = now.hour
    
    if 0 <= hour < 8:
        return "🌙 Asian Session (Low Activity)", "Off-peak - Limited opportunities"
    elif 8 <= hour < 13:
        return "🇬🇧 London Session", "Prime European trading hours"
    elif 13 <= hour < 17:
        return "🔥 London/NY Overlap", "PEAK TRADING TIME - Most volatile & liquid"
    elif 17 <= hour < 22:
        return "🇺🇸 NY Session", "Active US trading"
    else:
        return "🌙 Off-Hours", "Low activity period"

def analyze_market_conditions():
    """Analyze current market conditions"""
    now = get_london_time()
    
    print("="*80)
    print("📊 MARKET OVERVIEW")
    print("="*80)
    print(f"\n⏰ Current Time: {format_time(now)}")
    
    session, description = check_session()
    print(f"\n📍 Trading Session: {session}")
    print(f"   {description}")
    
    # Check if market is open
    weekday = now.weekday()
    hour = now.hour
    
    if weekday < 5:  # Monday-Friday
        if 0 <= hour < 23:
            market_status = "✅ MARKET OPEN"
        else:
            market_status = "⏸️  Market Closing Soon"
    elif weekday == 4 and hour >= 22:
        market_status = "⏸️  Market Closing (Friday Evening)"
    elif weekday >= 5:
        market_status = "🚫 MARKET CLOSED (Weekend)"
    else:
        market_status = "⏸️  Market Opening Soon"
    
    print(f"\n🏛️  Market Status: {market_status}")
    
    return now, session, market_status

def get_opportunities_from_live_data():
    """Fetch live market data and identify opportunities"""
    if not CREDENTIALS_AVAILABLE:
        return None
    
    try:
        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('PRIMARY_ACCOUNT')
        
        if not api_key or not account_id:
            return None
        
        client = OandaClient(api_key=api_key, account_id=account_id)
        
        # Key pairs to monitor
        pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD', 'USD_CAD']
        
        print("\n" + "="*80)
        print("💹 LIVE MARKET DATA")
        print("="*80)
        
        opportunities = []
        
        for pair in pairs:
            try:
                # Get current price
                price_data = client.get_current_price(pair)
                if not price_data:
                    continue
                
                # Get recent candles for trend
                candles = client.get_candles(pair, granularity='H1', count=24)
                if not candles or len(candles) < 2:
                    continue
                
                current_price = (price_data['bid'] + price_data['ask']) / 2
                
                # Calculate simple momentum
                prices = [float(c['mid']['c']) for c in candles]
                price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
                
                # Determine trend
                if price_change > 0.5:
                    trend = "📈 Bullish"
                    opportunity = "Consider LONG entries"
                elif price_change < -0.5:
                    trend = "📉 Bearish"
                    opportunity = "Consider SHORT entries"
                else:
                    trend = "➡️  Neutral"
                    opportunity = "Wait for clear direction"
                
                print(f"\n{pair.replace('_', '/')}:")
                print(f"   Price: {current_price:.5f}")
                print(f"   24h Change: {price_change:+.2f}%")
                print(f"   Trend: {trend}")
                print(f"   💡 {opportunity}")
                
                opportunities.append({
                    'pair': pair,
                    'price': current_price,
                    'change': price_change,
                    'trend': trend,
                    'opportunity': opportunity
                })
                
            except Exception as e:
                print(f"\n{pair}: ⚠️ Could not fetch data - {e}")
                continue
        
        return opportunities
        
    except Exception as e:
        print(f"\n⚠️  Could not fetch live data: {e}")
        return None

def analyze_today_activity():
    """Analyze today's trading activity from logs"""
    print("\n" + "="*80)
    print("📋 TODAY'S ACTIVITY ANALYSIS")
    print("="*80)
    
    log_files = [
        Path("logs/real_system_manual_fix.log"),
        Path("logs/real_system_final.log"),
        Path("google-cloud-trading-system/working_server.log"),
    ]
    
    today = datetime.now().date()
    signals_found = []
    trades_found = []
    
    for log_file in log_files:
        if not log_file.exists():
            continue
        
        try:
            # Read last 2000 lines for performance
            with open(log_file, 'r') as f:
                lines = f.readlines()[-2000:]
            
            for line in lines:
                if str(today) in line or datetime.now().strftime('%Y-%m-%d') in line:
                    # Look for signals
                    if any(word in line.upper() for word in ['SIGNAL', 'OPPORTUNITY', 'ENTRY']):
                        if any(pair in line.upper() for pair in ['EUR', 'GBP', 'USD', 'JPY', 'XAU', 'GOLD']):
                            signals_found.append(line.strip())
                    
                    # Look for trades
                    if any(word in line.upper() for word in ['TRADE', 'ORDER', 'POSITION', 'EXECUTED']):
                        trades_found.append(line.strip())
        
        except Exception as e:
            continue
    
    if signals_found:
        print(f"\n✅ Found {len(signals_found)} signals today")
        print("\nRecent signals:")
        for signal in signals_found[-5:]:
            print(f"   • {signal[:120]}")
    else:
        print("\n⚠️  No signals detected in logs today")
    
    if trades_found:
        print(f"\n✅ Found {len(trades_found)} trade activities today")
        print("\nRecent activity:")
        for trade in trades_found[-5:]:
            print(f"   • {trade[:120]}")
    else:
        print("\n⚠️  No trade execution detected today")
    
    return len(signals_found), len(trades_found)

def provide_recommendations():
    """Provide trading recommendations based on current conditions"""
    now = get_london_time()
    hour = now.hour
    weekday = now.weekday()
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS & LESSONS")
    print("="*80)
    
    # Time-based recommendations
    if weekday >= 5:
        print("\n🚫 WEEKEND - Market Closed")
        print("   ✓ Review this week's performance")
        print("   ✓ Plan strategies for next week")
        print("   ✓ No trading opportunities until Monday")
    
    elif 13 <= hour < 17 and weekday < 5:
        print("\n🔥 PEAK TRADING TIME (London/NY Overlap)")
        print("   ✓ Highest liquidity and volatility")
        print("   ✓ Best time for scalping and day trading")
        print("   ✓ Watch for breakouts and momentum trades")
        print("   ✓ Tighten stop losses due to volatility")
        print("   ⚠️  Risk: Fast moves can trigger stops quickly")
    
    elif 8 <= hour < 13 and weekday < 5:
        print("\n🇬🇧 LONDON SESSION")
        print("   ✓ Good liquidity for EUR, GBP pairs")
        print("   ✓ Watch for European economic data")
        print("   ✓ Trending moves often start here")
        print("   ⚠️  Be ready for NY session at 1pm London time")
    
    elif 17 <= hour < 22 and weekday < 5:
        print("\n🇺🇸 NEW YORK SESSION")
        print("   ✓ Still good for USD pairs")
        print("   ✓ Watch US economic releases")
        print("   ✓ Momentum from London may continue")
        print("   ⚠️  Liquidity decreases after 5pm NY (10pm London)")
    
    else:
        print("\n🌙 OFF-PEAK HOURS")
        print("   ⚠️  Low liquidity - wider spreads")
        print("   ⚠️  Asian session - different dynamics")
        print("   ✓ Better to wait for London/NY sessions")
        print("   ✓ Use this time for analysis and planning")
    
    # General lessons
    print("\n📚 KEY LESSONS FOR PROFITABLE TRADING:")
    print("   1. Trade during London/NY overlap (1pm-5pm London) for best results")
    print("   2. Avoid trading during Asian session (10pm-8am London)")
    print("   3. Use 5-minute charts for scalping, H1/H4 for swing trades")
    print("   4. Always set stop losses - protect capital first")
    print("   5. Take profits at 0.3-0.5% for scalping, 1-2% for swings")
    print("   6. Don't overtrade - quality over quantity")
    print("   7. Watch for news events - they create volatility")

def main():
    """Main function"""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "🌍 MARKET OVERVIEW & ANALYSIS" + " "*29 + "║")
    print("╚" + "="*78 + "╝")
    
    # Current conditions
    now, session, market_status = analyze_market_conditions()
    
    # Live market data
    if CREDENTIALS_AVAILABLE:
        opportunities = get_opportunities_from_live_data()
    else:
        print("\n⚠️  Run with credentials for live market data")
        print("   Set up .env file or use Secret Manager")
        opportunities = None
    
    # Today's activity
    signals, trades = analyze_today_activity()
    
    # Recommendations
    provide_recommendations()
    
    # Summary
    print("\n" + "="*80)
    print("📊 QUICK SUMMARY")
    print("="*80)
    print(f"\n⏰ Time: {format_time(now)}")
    print(f"📍 Session: {session.split()[0]} {session.split()[1] if len(session.split()) > 1 else ''}")
    print(f"🏛️  Status: {market_status}")
    print(f"📊 Signals Today: {signals}")
    print(f"💼 Trades Today: {trades}")
    
    if opportunities and len(opportunities) > 0:
        # Find best opportunity
        best_opp = max(opportunities, key=lambda x: abs(x['change']))
        print(f"\n🎯 Best Opportunity: {best_opp['pair'].replace('_', '/')}")
        print(f"   {best_opp['trend']} ({best_opp['change']:+.2f}%)")
        print(f"   💡 {best_opp['opportunity']}")
    
    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)

if __name__ == '__main__':
    main()


