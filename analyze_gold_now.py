#!/usr/bin/env python3
"""
Gold Market Analysis - Real-Time
Uses your trading system to analyze current gold conditions, news, and provide recommendations
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / "AI_QUANT_credentials" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except:
    pass

# Import system components
from src.control_plane.market_data_provider import get_latest_price, get_candles, MarketDataError
from src.control_plane.news_provider import fetch_news_with_registry
from src.core.settings import load_settings

LONDON_TZ = pytz.timezone('Europe/London')

def format_price(price: float) -> str:
    """Format gold price for display"""
    return f"${price:,.2f}"

def analyze_gold_price():
    """Get current gold price and recent trend"""
    print("\n" + "="*80)
    print("🥇 CURRENT GOLD PRICE (XAU/USD)")
    print("="*80)
    
    try:
        # Get current price
        price = get_latest_price("XAU_USD")
        spread = price.ask - price.bid
        spread_pct = (spread / price.mid) * 100
        
        print(f"\n📊 Current Market:")
        print(f"   Bid:  {format_price(price.bid)}")
        print(f"   Ask:  {format_price(price.ask)}")
        print(f"   Mid:  {format_price(price.mid)}")
        print(f"   Spread: ${spread:.2f} ({spread_pct:.3f}%)")
        
        # Get recent candles for trend analysis
        print(f"\n📈 Trend Analysis:")
        candles_h1 = []
        candles_m15 = None
        
        # Try different granularities and counts
        for granularity, count in [("H1", 12), ("H1", 6), ("H4", 6), ("D", 5)]:
            try:
                candles_h1 = get_candles("XAU_USD", granularity=granularity, count=count)
                if candles_h1 and len(candles_h1) >= 2:
                    break
            except MarketDataError:
                continue
        
        # Try M15 for support/resistance
        for count in [48, 24, 12]:
            try:
                candles_m15 = get_candles("XAU_USD", granularity="M15", count=count)
                if candles_m15 and len(candles_m15) >= 10:
                    break
            except MarketDataError:
                continue
        
        if candles_h1 and len(candles_h1) >= 2:
            # 24-hour change
            price_24h_ago = candles_h1[0].c
            price_change_24h = ((price.mid - price_24h_ago) / price_24h_ago) * 100
            
            # 4-hour change (use available candles)
            if len(candles_h1) >= 4:
                price_4h_ago = candles_h1[-4].c
                price_change_4h = ((price.mid - price_4h_ago) / price_4h_ago) * 100
            elif len(candles_h1) >= 2:
                # Use half the available candles as proxy
                mid_point = len(candles_h1) // 2
                price_4h_ago = candles_h1[mid_point].c
                price_change_4h = ((price.mid - price_4h_ago) / price_4h_ago) * 100
            else:
                price_change_4h = 0
            
            # Recent volatility (use available candles)
            recent_candles = candles_h1[-min(4, len(candles_h1)):] if candles_h1 else []
            if recent_candles:
                highs = [c.h for c in recent_candles]
                lows = [c.l for c in recent_candles]
                volatility = (max(highs) - min(lows)) / price.mid * 100
            else:
                volatility = 0
            
            print(f"   24h Change: {price_change_24h:+.2f}%")
            print(f"   4h Change:  {price_change_4h:+.2f}%")
            print(f"   Recent Volatility (4h): {volatility:.2f}%")
            
            # Determine trend
            if price_change_24h > 0.3:
                trend = "📈 BULLISH"
                trend_strength = "Strong" if price_change_24h > 0.8 else "Moderate"
            elif price_change_24h < -0.3:
                trend = "📉 BEARISH"
                trend_strength = "Strong" if price_change_24h < -0.8 else "Moderate"
            else:
                trend = "➡️  NEUTRAL/SIDEWAYS"
                trend_strength = "Low"
            
            print(f"   Trend: {trend} ({trend_strength})")
            
            # Support/Resistance levels (simplified)
            if candles_m15 and len(candles_m15) >= 20:
                recent_lows = [c.l for c in candles_m15[-20:]]
                recent_highs = [c.h for c in candles_m15[-20:]]
                support = min(recent_lows)
                resistance = max(recent_highs)
                
                print(f"\n📊 Key Levels (Last 24h):")
                print(f"   Support:  {format_price(support)}")
                print(f"   Resistance: {format_price(resistance)}")
                print(f"   Current:  {format_price(price.mid)}")
                
                # Distance to levels
                dist_to_support = ((price.mid - support) / price.mid) * 100
                dist_to_resistance = ((resistance - price.mid) / price.mid) * 100
                print(f"   Distance to Support: {dist_to_support:.2f}%")
                print(f"   Distance to Resistance: {dist_to_resistance:.2f}%")
            
            return {
                'price': price,
                'change_24h': price_change_24h,
                'change_4h': price_change_4h,
                'trend': trend,
                'volatility': volatility,
                'support': support if candles_m15 else None,
                'resistance': resistance if candles_m15 else None
            }
        else:
            print("   ⚠️  Insufficient data for trend analysis")
            return {'price': price, 'change_24h': 0, 'change_4h': 0, 'trend': 'UNKNOWN'}
            
    except MarketDataError as e:
        print(f"\n❌ Error fetching market data: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_gold_news():
    """Fetch and analyze gold-related news"""
    print("\n" + "="*80)
    print("📰 GOLD NEWS & SENTIMENT")
    print("="*80)
    
    try:
        # Try to fetch news, but handle gracefully if providers aren't fully configured
        try:
            news_items, status = fetch_news_with_registry(
                query="gold OR XAU OR precious metals OR inflation OR fed OR interest rates",
                threshold="medium",
                max_items=20
            )
        except AttributeError as e:
            # Settings may not have all provider keys - use simpler approach
            print(f"\n⚠️  News provider configuration issue: {e}")
            print("   Using available news sources...")
            news_items = []
            status = {'providers_used': [], 'errors_by_provider': {}}
            
            # Try individual providers that are likely configured
            from src.control_plane.news_provider import fetch_news_alphavantage, fetch_news_newsapi
            settings = load_settings()
            
            if settings.alphavantage_api_key:
                try:
                    items = fetch_news_alphavantage(threshold="medium", max_items=20)
                    news_items.extend(items)
                    status['providers_used'].append('alphavantage')
                except Exception as e:
                    status['errors_by_provider']['alphavantage'] = str(e)[:100]
            
            if settings.newsapi_api_key:
                try:
                    items = fetch_news_newsapi(
                        query="gold OR XAU OR precious metals OR inflation OR fed",
                        threshold="medium",
                        max_items=20
                    )
                    news_items.extend(items)
                    status['providers_used'].append('newsapi')
                except Exception as e:
                    status['errors_by_provider']['newsapi'] = str(e)[:100]
            
            if settings.marketaux_keys:
                try:
                    from src.control_plane.news_provider import fetch_news_marketaux
                    items = fetch_news_marketaux(
                        query="gold OR XAU OR precious metals",
                        threshold="medium",
                        max_items=20
                    )
                    news_items.extend(items)
                    status['providers_used'].append('marketaux')
                except Exception as e:
                    status['errors_by_provider']['marketaux'] = str(e)[:100]
        
        if not news_items:
            print("\n⚠️  No recent news found")
            return None
        
        # Filter for gold-specific news
        gold_keywords = ['gold', 'xau', 'precious metal', 'bullion', 'inflation', 'fed', 'federal reserve', 
                        'interest rate', 'cpi', 'dollar', 'usd', 'treasury', 'safe haven']
        gold_news = []
        for item in news_items:
            title = (item.get('title', '') or '').lower()
            summary = (item.get('summary', '') or item.get('description', '') or '').lower()
            text = title + ' ' + summary
            if any(kw in text for kw in gold_keywords):
                gold_news.append(item)
        
        # If we filtered too much, use original list
        if len(gold_news) < 3:
            gold_news = news_items[:10]  # Use top 10 if filtering too aggressive
        
        print(f"\n📰 Found {len(news_items)} total news items")
        print(f"   Gold-relevant: {len(gold_news)} items")
        print(f"   Providers used: {', '.join(status.get('providers_used', []))}")
        
        # Show top gold-relevant news items
        print(f"\n🔝 Top Gold-Related News:")
        for i, item in enumerate(gold_news[:5], 1):
            title = item.get('title', 'No title')
            source = item.get('source', 'Unknown')
            published = item.get('published', 'Unknown date')
            sentiment = item.get('sentiment', 0)
            
            # Format sentiment
            if sentiment > 0.1:
                sent_icon = "🟢"
            elif sentiment < -0.1:
                sent_icon = "🔴"
            else:
                sent_icon = "🟡"
            
            print(f"\n   {i}. {sent_icon} {title[:80]}")
            print(f"      Source: {source} | {published}")
            if sentiment != 0:
                print(f"      Sentiment: {sentiment:+.2f}")
        
        # Calculate overall sentiment - use gold_news if available
        news_for_sentiment = gold_news if gold_news else news_items
        sentiments = []
        
        # Extract sentiment from items, or calculate from title
        for item in news_for_sentiment:
            sent = item.get('sentiment')
            if sent is not None:
                sentiments.append(sent)
            else:
                # Simple sentiment from title keywords
                title = (item.get('title', '') or '').lower()
                bullish_words = ['rise', 'up', 'gain', 'rally', 'surge', 'higher', 'boost', 'strong', 'positive']
                bearish_words = ['fall', 'down', 'drop', 'decline', 'lower', 'weak', 'negative', 'crash', 'plunge']
                bull_count = sum(1 for w in bullish_words if w in title)
                bear_count = sum(1 for w in bearish_words if w in title)
                if bull_count > bear_count:
                    sentiments.append(0.2)
                elif bear_count > bull_count:
                    sentiments.append(-0.2)
                else:
                    sentiments.append(0.0)
        
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            print(f"\n📊 Overall News Sentiment:")
            print(f"   Average: {avg_sentiment:+.3f}")
            
            if avg_sentiment > 0.15:
                print(f"   Interpretation: 🟢 BULLISH - News favors gold")
            elif avg_sentiment < -0.15:
                print(f"   Interpretation: 🔴 BEARISH - News negative for gold")
            else:
                print(f"   Interpretation: 🟡 NEUTRAL - Mixed signals")
            
            return {
                'items': gold_news if gold_news else news_items,
                'avg_sentiment': avg_sentiment,
                'count': len(gold_news) if gold_news else len(news_items)
            }
        else:
            return {
                'items': gold_news if gold_news else news_items,
                'avg_sentiment': 0,
                'count': len(gold_news) if gold_news else len(news_items)
            }
            
    except Exception as e:
        print(f"\n❌ Error fetching news: {e}")
        import traceback
        traceback.print_exc()
        return None

def provide_recommendations(price_data, news_data):
    """Provide trading recommendations based on analysis"""
    print("\n" + "="*80)
    print("💡 TRADING RECOMMENDATIONS")
    print("="*80)
    
    if not price_data:
        print("\n⚠️  Cannot provide recommendations - missing price data")
        return
    
    current_price = price_data['price'].mid
    trend = price_data.get('trend', 'UNKNOWN')
    change_24h = price_data.get('change_24h', 0)
    change_4h = price_data.get('change_4h', 0)
    volatility = price_data.get('volatility', 0)
    support = price_data.get('support')
    resistance = price_data.get('resistance')
    
    news_sentiment = news_data.get('avg_sentiment', 0) if news_data else 0
    
    # Determine recommendation
    print(f"\n🎯 Analysis Summary:")
    print(f"   Price Trend: {trend}")
    print(f"   24h Change: {change_24h:+.2f}%")
    print(f"   News Sentiment: {news_sentiment:+.3f}")
    
    # Combine signals
    bullish_signals = 0
    bearish_signals = 0
    
    if change_24h > 0.3:
        bullish_signals += 1
    elif change_24h < -0.3:
        bearish_signals += 1
    
    if change_4h > 0.2:
        bullish_signals += 1
    elif change_4h < -0.2:
        bearish_signals += 1
    
    if news_sentiment > 0.1:
        bullish_signals += 1
    elif news_sentiment < -0.1:
        bearish_signals += 1
    
    print(f"\n📊 Signal Strength:")
    print(f"   Bullish Signals: {bullish_signals}/3")
    print(f"   Bearish Signals: {bearish_signals}/3")
    
    # Recommendation
    print(f"\n💡 Recommendation:")
    
    if bullish_signals >= 2:
        print(f"   🟢 CONSIDER LONG (BUY)")
        print(f"   Rationale: Price trending up + positive news sentiment")
        if support:
            print(f"   Entry Zone: {format_price(support)} - {format_price(current_price * 1.001)}")
            if resistance:
                target = min(resistance, current_price * 1.005)
                print(f"   Target: {format_price(target)} (+{((target - current_price) / current_price * 100):.2f}%)")
        print(f"   Stop Loss: {format_price(current_price * 0.997)} (-{((current_price * 0.997 - current_price) / current_price * 100):.2f}%)")
        
    elif bearish_signals >= 2:
        print(f"   🔴 CONSIDER SHORT (SELL)")
        print(f"   Rationale: Price trending down + negative news sentiment")
        if resistance:
            print(f"   Entry Zone: {format_price(current_price * 0.999)} - {format_price(resistance)}")
            if support:
                target = max(support, current_price * 0.995)
                print(f"   Target: {format_price(target)} ({((target - current_price) / current_price * 100):.2f}%)")
        print(f"   Stop Loss: {format_price(current_price * 1.003)} (+{((current_price * 1.003 - current_price) / current_price * 100):.2f}%)")
        
    else:
        print(f"   🟡 WAIT FOR CLEARER SIGNAL")
        print(f"   Rationale: Mixed signals - price and news not aligned")
        print(f"   Action: Monitor for breakout above {format_price(resistance) if resistance else 'resistance'} or below {format_price(support) if support else 'support'}")
    
    # Risk warnings
    print(f"\n⚠️  Risk Considerations:")
    if volatility > 0.5:
        print(f"   • High volatility detected ({volatility:.2f}%) - use tighter stops")
    if abs(change_24h) > 1.0:
        print(f"   • Large move already occurred - may be overextended")
    if news_sentiment == 0 and news_data:
        print(f"   • News sentiment neutral - technicals may be more reliable")
    
    # Session timing
    now = datetime.now(LONDON_TZ)
    hour = now.hour
    weekday = now.weekday()
    
    print(f"\n⏰ Current Session:")
    if weekday >= 5:
        print(f"   🚫 Weekend - Markets closed")
    elif 8 <= hour < 13:
        print(f"   🇬🇧 London Session - Good liquidity")
    elif 13 <= hour < 17:
        print(f"   🔥 London/NY Overlap - BEST liquidity & volatility")
    elif 17 <= hour < 22:
        print(f"   🇺🇸 NY Session - Still active")
    else:
        print(f"   🌙 Off-peak - Lower liquidity, wider spreads")

def main():
    """Main analysis function"""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*25 + "🥇 GOLD MARKET ANALYSIS" + " "*29 + "║")
    print("╚" + "="*78 + "╝")
    
    now = datetime.now(LONDON_TZ)
    print(f"\n⏰ Analysis Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Analyze price
    price_data = analyze_gold_price()
    
    # Analyze news
    news_data = analyze_gold_news()
    
    # Provide recommendations
    provide_recommendations(price_data, news_data)
    
    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)
    print(f"\n💡 Remember: This is analysis, not financial advice.")
    print(f"   Always use proper risk management and stop losses.")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
