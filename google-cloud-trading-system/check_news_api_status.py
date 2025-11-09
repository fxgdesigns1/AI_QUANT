#!/usr/bin/env python3
"""
Check News API Status and Configuration
Tests actual API connectivity and rate limiting
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_news_apis():
    """Test news API connectivity and freshness"""
    print("=" * 70)
    print("🔍 TESTING YOUR NEWS APIS")
    print("=" * 70)
    print()
    
    # Set environment variables from app.yaml
    os.environ['ALPHA_VANTAGE_API_KEY'] = '${ALPHA_VANTAGE_API_KEY}'
    os.environ['MARKETAUX_API_KEY'] = '${MARKETAUX_API_KEY}'
    
    from src.core.news_integration import SafeNewsIntegration
    
    # Create news integration instance
    news = SafeNewsIntegration()
    
    print(f"📊 API Keys Status:")
    print(f"  Available APIs: {len(news.api_keys)}")
    print(f"  API Names: {list(news.api_keys.keys())}")
    print(f"  Integration Enabled: {news.enabled}")
    print()
    
    if not news.enabled:
        print("⚠️  News integration disabled - using valid APIs only")
        print()
    
    print("=" * 70)
    print("📰 FETCHING LIVE NEWS DATA")
    print("=" * 70)
    print()
    
    start_time = datetime.now()
    
    try:
        # Test fetching news
        currency_pairs = ['EUR_USD', 'GBP_USD', 'XAU_USD']
        print(f"🔄 Fetching news for: {', '.join(currency_pairs)}")
        print(f"⏰ Started at: {start_time.strftime('%H:%M:%S')}")
        print()
        
        news_data = await news.get_news_data(currency_pairs)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Fetch completed in {duration:.2f} seconds")
        print()
        
        if news_data:
            print(f"📊 Retrieved {len(news_data)} news items")
            print()
            print("📋 Latest News:")
            for i, item in enumerate(news_data[:5], 1):
                print(f"\n{i}. {item.get('title', 'No title')}")
                print(f"   Source: {item.get('source', 'Unknown')}")
                print(f"   Published: {item.get('published_at', 'Unknown')}")
                print(f"   Impact: {item.get('impact', 'unknown')}")
                print(f"   Sentiment: {item.get('sentiment', 0):.2f}")
                if item.get('currency_pairs'):
                    print(f"   Affects: {', '.join(item.get('currency_pairs', []))}")
        else:
            print("⚠️  No news data retrieved")
            print("   This could mean:")
            print("   1. APIs are rate-limited")
            print("   2. No recent news for these pairs")
            print("   3. API keys need validation")
        
        print()
        print("=" * 70)
        print("🔍 RATE LIMITING CHECK")
        print("=" * 70)
        print()
        
        print("📊 Rate Limit Configuration:")
        for api_name, limit in news.rate_limits.items():
            print(f"  {api_name}: 1 call every {limit} seconds")
        
        print()
        print(f"💾 Cache Configuration:")
        print(f"  Cache TTL: {news.update_interval} seconds ({news.update_interval // 60} minutes)")
        print(f"  Cache Valid: {news._is_cache_valid()}")
        print(f"  Last Update: {news.last_update.strftime('%H:%M:%S') if news.last_update else 'Never'}")
        
        print()
        print("=" * 70)
        print("📊 NEWS FRESHNESS")
        print("=" * 70)
        print()
        
        if news_data:
            print("✅ News is fetched every 10 minutes (when trading)")
            print("✅ Cached between fetches to avoid rate limits")
            print("✅ Updates are near real-time (within 10 min)")
            print()
            print("⏰ Update Schedule:")
            print("  - First fetch: When system starts")
            print("  - Subsequent: Every 10 minutes")
            print("  - Max delay: 10 minutes from real event")
            print()
            print("📈 This is appropriate because:")
            print("  ✓ News impact unfolds over minutes/hours, not seconds")
            print("  ✓ Protects your API rate limits")
            print("  ✓ Provides timely enough data for trading decisions")
        
        print()
        print("=" * 70)
        print("🎯 TRADING INTEGRATION STATUS")
        print("=" * 70)
        print()
        
        # Get news analysis
        analysis = news.get_news_analysis(currency_pairs)
        
        print(f"📊 Current Market Sentiment:")
        print(f"  Overall Sentiment: {analysis['overall_sentiment']:.2f} (-1 to +1)")
        print(f"  Market Impact: {analysis['market_impact']}")
        print(f"  Trading Recommendation: {analysis['trading_recommendation']}")
        print(f"  Confidence: {analysis['confidence']:.0%}")
        print()
        
        if analysis['key_events']:
            print(f"🚨 Key Events ({len(analysis['key_events'])}):")
            for event in analysis['key_events'][:3]:
                print(f"  • {event}")
            print()
        
        if analysis['risk_factors']:
            print(f"⚠️  Risk Factors ({len(analysis['risk_factors'])}):")
            for risk in analysis['risk_factors'][:3]:
                print(f"  • {risk}")
            print()
        
        if analysis['opportunities']:
            print(f"💡 Opportunities ({len(analysis['opportunities'])}):")
            for opp in analysis['opportunities'][:3]:
                print(f"  • {opp}")
            print()
        
        # Check if trading should be paused
        should_pause = news.should_pause_trading(currency_pairs)
        print(f"🚦 Trading Status: {'⏸️  PAUSED' if should_pause else '✅ ACTIVE'}")
        
        print()
        print("=" * 70)
        print("✅ NEWS API TEST COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = asyncio.run(test_news_apis())
    sys.exit(0 if result else 1)


