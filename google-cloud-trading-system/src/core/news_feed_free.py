#!/usr/bin/env python3
"""
FREE NEWS FEED - No API Keys Required
Uses free sources for market news
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict
try:
    import feedparser
except ImportError:
    feedparser = None
    logging.warning("feedparser not available - news feed will be limited")

logger = logging.getLogger(__name__)

class FreeNewsFeed:
    """Free news feed - no API keys needed"""
    
    def __init__(self):
        self.news_cache = []
        self.last_fetch = None
        
        # FREE RSS feeds (no API key required)
        self.rss_feeds = [
            'https://www.forexlive.com/feed/news',  # Forex news
            'https://www.fxstreet.com/rss/news',  # FX Street
            'https://www.reuters.com/business/finance',  # Reuters finance
        ]
    
    def get_latest_news(self, hours: int = 4) -> List[Dict]:
        """Get latest news from free sources"""
        
        # Use cache if recent (15 minutes)
        if self.last_fetch and (datetime.now() - self.last_fetch).seconds < 900:
            if self.news_cache:
                logger.info(f"📦 Using cached news ({len(self.news_cache)} items)")
                return self.news_cache
        
        logger.info("📰 Fetching news from free RSS feeds...")
        
        news_items = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # Last 10 from each feed
                    try:
                        # Parse date
                        published = entry.get('published_parsed', None)
                        if published:
                            pub_date = datetime(*published[:6])
                            
                            if pub_date > cutoff_time:
                                news_items.append({
                                    'title': entry.get('title', 'No title'),
                                    'summary': entry.get('summary', '')[:200],
                                    'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                                    'source': feed_url.split('/')[2]
                                })
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"⚠️ Feed {feed_url} failed: {str(e)[:50]}")
        
        # Sort by date
        news_items.sort(key=lambda x: x['published'], reverse=True)
        
        self.news_cache = news_items[:20]  # Keep top 20
        self.last_fetch = datetime.now()
        
        logger.info(f"✅ Fetched {len(news_items)} news items")
        
        return self.news_cache
    
    def get_currency_sentiment(self, currency: str) -> Dict:
        """Get sentiment for currency from news (basic)"""
        news = self.get_latest_news(hours=2)
        
        positive_words = ['rise', 'surge', 'gain', 'strong', 'bullish', 'up', 'higher']
        negative_words = ['fall', 'drop', 'decline', 'weak', 'bearish', 'down', 'lower']
        
        positive_count = 0
        negative_count = 0
        
        for item in news:
            text = (item['title'] + ' ' + item['summary']).lower()
            
            if currency.lower() in text:
                for word in positive_words:
                    if word in text:
                        positive_count += 1
                
                for word in negative_words:
                    if word in text:
                        negative_count += 1
        
        total = positive_count + negative_count
        
        if total == 0:
            sentiment = 'NEUTRAL'
            score = 0
        else:
            score = (positive_count - negative_count) / total
            if score > 0.3:
                sentiment = 'POSITIVE'
            elif score < -0.3:
                sentiment = 'NEGATIVE'
            else:
                sentiment = 'NEUTRAL'
        
        return {
            'currency': currency,
            'sentiment': sentiment,
            'score': score,
            'mentions': total
        }


# Singleton
_news_feed = None

def get_free_news_feed():
    """Get free news feed singleton"""
    global _news_feed
    if _news_feed is None:
        _news_feed = FreeNewsFeed()
        logger.info("✅ Free news feed initialized")
    return _news_feed


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    feed = get_free_news_feed()
    
    print("\n" + "=" * 70)
    print("📰 FREE NEWS FEED TEST")
    print("=" * 70)
    
    news = feed.get_latest_news(hours=4)
    
    print(f"\n✅ Latest news ({len(news)} items):")
    for item in news[:5]:
        print(f"\n• {item['title']}")
        print(f"  {item['published']} | {item['source']}")
    
    print("\n🔍 CURRENCY SENTIMENT:")
    for currency in ['USD', 'EUR', 'GBP', 'JPY']:
        sentiment = feed.get_currency_sentiment(currency)
        print(f"   {currency}: {sentiment['sentiment']} ({sentiment['score']:+.2f})")

