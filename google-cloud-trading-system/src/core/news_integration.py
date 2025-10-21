#!/usr/bin/env python3
"""
Safe News API Integration for Google Cloud Trading System
PRODUCTION VERSION - Real data only, no mock fallbacks
"""

import os
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    """News item structure - compatible with existing system"""
    title: str
    summary: str
    source: str
    published_at: datetime
    impact: str  # 'high', 'medium', 'low'
    currency_pairs: List[str]
    sentiment: float  # -1 to 1
    url: str = ""

class SafeNewsIntegration:
    """Safe news integration that won't break existing system"""
    
    def __init__(self):
        """Initialize safe news integration"""
        self.enabled = False
        self.api_keys = {}
        self.session = None
        self.cache = {}
        self.last_update = None
        self.update_interval = 3600  # 1 hour - matches scan frequency
        self.api_call_times = {}  # Track API call times for rate limiting
        self.rate_limits = {
            'alpha_vantage': 300,  # 5 minutes (allows use on every scan)
            'marketaux': 300,      # 5 minutes
            'newsdata': 300,       # 5 minutes
            'newsapi': 300         # 5 minutes
        }
        
        # Load API keys safely
        self._load_api_keys()
        
        # Initialize if keys are available
        if self.api_keys:
            self.enabled = True
            logger.info("✅ News API integration enabled")
        else:
            logger.info("⚠️ News API integration disabled - no API keys found")
    
    def _load_api_keys(self):
        """Safely load API keys from environment - PRODUCTION FOCUS"""
        try:
            # Load from environment variables - prioritize real APIs
            self.api_keys = {
                'alpha_vantage': os.getenv('ALPHA_VANTAGE_API_KEY', ''),
                'marketaux': os.getenv('MARKETAUX_API_KEY', ''),
                'newsdata': os.getenv('NEWSDATA_API_KEY', ''),
                'newsapi': os.getenv('NEWSAPI_KEY', ''),
                'fmp': os.getenv('FMP_API_KEY', ''),
                'polygon': os.getenv('POLYGON_API_KEY', ''),
                'twelve_data': os.getenv('TWELVE_DATA_API_KEY', '')
            }
            
            # Filter out empty keys and placeholder keys
            self.api_keys = {k: v for k, v in self.api_keys.items() if v and v != 'your_' + k + '_api_key'}
            
            # Log available APIs
            if self.api_keys:
                logger.info(f"✅ Loaded {len(self.api_keys)} real API keys: {list(self.api_keys.keys())}")
            else:
                logger.error("❌ CRITICAL: No valid API keys found - news integration disabled")
            
        except Exception as e:
            logger.error(f"❌ Failed to load API keys: {e}")
            self.api_keys = {}
    
    async def get_news_data(self, currency_pairs: List[str] = None) -> List[Dict[str, Any]]:
        """Get news data - PRODUCTION: Real data only, no mock fallback"""
        try:
            if not self.enabled:
                logger.error("❌ News integration disabled - no API keys available")
                return []
            
            # Check cache first
            if self._is_cache_valid():
                cached_data = self.cache.get('news_data', [])
                if cached_data:
                    logger.info(f"📰 Using cached news data: {len(cached_data)} items")
                    return cached_data
            
            # Try to get real news data
            news_data = await self._fetch_real_news(currency_pairs or ['EUR_USD', 'GBP_USD', 'USD_JPY'])
            
            if news_data:
                self.cache['news_data'] = news_data
                self.last_update = datetime.now()
                logger.info(f"📰 Retrieved {len(news_data)} real news items from APIs")
                return news_data
            else:
                # PRODUCTION: No mock data fallback
                logger.error("❌ CRITICAL: No real news data available - trading without news analysis")
                return []
                
        except Exception as e:
            logger.error(f"❌ News data fetch failed: {e}")
            logger.error("❌ CRITICAL: News integration failed - trading without news analysis")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.last_update:
            return False
        
        return (datetime.now() - self.last_update).seconds < self.update_interval
    
    def _can_call_api(self, api_name: str) -> bool:
        """Check if we can call an API without hitting rate limits"""
        if api_name not in self.api_call_times:
            return True
        
        last_call = self.api_call_times[api_name]
        time_since_last_call = (datetime.now() - last_call).seconds
        
        return time_since_last_call >= self.rate_limits[api_name]
    
    def _record_api_call(self, api_name: str):
        """Record API call time for rate limiting"""
        self.api_call_times[api_name] = datetime.now()
    
    async def _fetch_real_news(self, currency_pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch real news data from APIs - PRODUCTION PRIORITY"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # PRODUCTION: Try APIs in order of reliability and data quality
            # 1. MarketAux (most reliable for news)
            if 'marketaux' in self.api_keys and self._can_call_api('marketaux'):
                logger.info("🔄 Fetching news from MarketAux API...")
                news_data = await self._fetch_marketaux_news(currency_pairs)
                self._record_api_call('marketaux')
                if news_data:
                    logger.info(f"✅ MarketAux: Retrieved {len(news_data)} news items")
                    return news_data
                else:
                    logger.warning("⚠️ MarketAux: No news data returned")
            elif 'marketaux' in self.api_keys:
                logger.info("⏳ MarketAux: Rate limited, skipping")
            
            # 2. Alpha Vantage (financial data + news)
            if 'alpha_vantage' in self.api_keys and self._can_call_api('alpha_vantage'):
                logger.info("🔄 Fetching news from Alpha Vantage API...")
                news_data = await self._fetch_alpha_vantage_news(currency_pairs)
                self._record_api_call('alpha_vantage')
                if news_data:
                    logger.info(f"✅ Alpha Vantage: Retrieved {len(news_data)} news items")
                    return news_data
                else:
                    logger.warning("⚠️ Alpha Vantage: No news data returned")
            elif 'alpha_vantage' in self.api_keys:
                logger.info("⏳ Alpha Vantage: Rate limited, skipping")
            
            # 3. NewsData.io (news specialist)
            if 'newsdata' in self.api_keys and self._can_call_api('newsdata'):
                logger.info("🔄 Fetching news from NewsData.io API...")
                news_data = await self._fetch_newsdata_news(currency_pairs)
                self._record_api_call('newsdata')
                if news_data:
                    logger.info(f"✅ NewsData.io: Retrieved {len(news_data)} news items")
                    return news_data
                else:
                    logger.warning("⚠️ NewsData.io: No news data returned")
            elif 'newsdata' in self.api_keys:
                logger.info("⏳ NewsData.io: Rate limited, skipping")
            
            # 4. NewsAPI (fallback)
            if 'newsapi' in self.api_keys and self._can_call_api('newsapi'):
                logger.info("🔄 Fetching news from NewsAPI...")
                news_data = await self._fetch_newsapi_news(currency_pairs)
                self._record_api_call('newsapi')
                if news_data:
                    logger.info(f"✅ NewsAPI: Retrieved {len(news_data)} news items")
                    return news_data
                else:
                    logger.warning("⚠️ NewsAPI: No news data returned")
            elif 'newsapi' in self.api_keys:
                logger.info("⏳ NewsAPI: Rate limited, skipping")
            
            logger.error("❌ CRITICAL: All news APIs failed - no real news data available")
            return []
            
        except Exception as e:
            logger.error(f"❌ Real news fetch failed: {e}")
            return []
    
    async def _fetch_marketaux_news(self, currency_pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch news from MarketAux API - OPTIMIZED for rate limits"""
        try:
            # Simplified parameters to avoid 400 errors
            params = {
                'api_token': self.api_keys['marketaux'],
                'limit': 10,  # Reduced to stay within limits
                'published_after': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d')  # Last 6 hours only
            }
            
            # Only add symbols if we have specific pairs
            if currency_pairs and len(currency_pairs) <= 3:  # Limit to 3 pairs max
                # Convert to MarketAux format
                symbols = []
                for pair in currency_pairs[:3]:
                    if '_' in pair:
                        symbols.append(pair.replace('_', ''))
                if symbols:
                    params['symbols'] = ','.join(symbols)
            
            url = "https://api.marketaux.com/v1/news/all"
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_marketaux_response(data)
                elif response.status == 429:
                    logger.warning("⚠️ MarketAux: Rate limit exceeded, skipping")
                    return []
                else:
                    logger.warning(f"⚠️ MarketAux API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.warning(f"⚠️ MarketAux API request failed: {e}")
            return []
    
    async def _fetch_alpha_vantage_news(self, currency_pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch news from Alpha Vantage API - OPTIMIZED for rate limits"""
        try:
            # Alpha Vantage has strict rate limits (5 calls per minute)
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.api_keys['alpha_vantage'],
                'limit': 5,  # Reduced to stay within limits
                'time_from': (datetime.now() - timedelta(hours=6)).strftime('%Y%m%dT%H%M'),
                'time_to': datetime.now().strftime('%Y%m%dT%H%M')
            }
            
            url = "https://www.alphavantage.co/query"
            
            async with self.session.get(url, params=params, timeout=20) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check for rate limit message in response
                    if 'Note' in data and 'API call frequency' in data['Note']:
                        logger.warning("⚠️ Alpha Vantage: Rate limit exceeded")
                        return []
                    return self._parse_alpha_vantage_response(data)
                elif response.status == 429:
                    logger.warning("⚠️ Alpha Vantage: Rate limit exceeded")
                    return []
                else:
                    logger.warning(f"⚠️ Alpha Vantage error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.warning(f"⚠️ Alpha Vantage request failed: {e}")
            return []
    
    async def _fetch_newsdata_news(self, currency_pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch news from NewsData.io API - OPTIMIZED for rate limits"""
        try:
            # Simplified parameters to avoid 401 errors
            params = {
                'apikey': self.api_keys['newsdata'],
                'country': 'us,gb',  # Reduced countries to stay within limits
                'category': 'business',
                'language': 'en',
                'size': 10  # Reduced size to stay within limits
            }
            
            url = "https://newsdata.io/api/1/news"
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_newsdata_response(data)
                elif response.status == 401:
                    logger.warning("⚠️ NewsData.io: Invalid API key")
                    return []
                elif response.status == 429:
                    logger.warning("⚠️ NewsData.io: Rate limit exceeded")
                    return []
                else:
                    logger.warning(f"⚠️ NewsData.io API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.warning(f"⚠️ NewsData.io API request failed: {e}")
            return []
    
    async def _fetch_newsapi_news(self, currency_pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch news from NewsAPI - OPTIMIZED for rate limits"""
        try:
            # Simplified parameters to avoid 401 errors
            params = {
                'apiKey': self.api_keys['newsapi'],
                'country': 'us',  # Single country to stay within limits
                'category': 'business',
                'language': 'en',
                'pageSize': 10  # Reduced size to stay within limits
            }
            
            url = "https://newsapi.org/v2/top-headlines"
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_newsapi_response(data)
                elif response.status == 401:
                    logger.warning("⚠️ NewsAPI: Invalid API key")
                    return []
                elif response.status == 429:
                    logger.warning("⚠️ NewsAPI: Rate limit exceeded")
                    return []
                else:
                    logger.warning(f"⚠️ NewsAPI error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.warning(f"⚠️ NewsAPI request failed: {e}")
            return []
    
    def _parse_marketaux_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse MarketAux API response"""
        news_items = []
        
        if 'data' not in data:
            return news_items
        
        for item in data['data']:
            try:
                news_item = {
                    'title': item.get('title', ''),
                    'summary': item.get('description', ''),
                    'source': item.get('source', ''),
                    'published_at': item.get('published_at', ''),
                    'impact': self._calculate_impact(item),
                    'currency_pairs': self._extract_currency_pairs(item),
                    'sentiment': self._calculate_sentiment(item),
                    'url': item.get('url', '')
                }
                news_items.append(news_item)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse news item: {e}")
                continue
        
        return news_items
    
    def _parse_alpha_vantage_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse Alpha Vantage API response"""
        news_items = []
        
        if 'feed' not in data:
            return news_items
        
        for item in data['feed']:
            try:
                news_item = {
                    'title': item.get('title', ''),
                    'summary': item.get('summary', ''),
                    'source': item.get('source', ''),
                    'published_at': item.get('time_published', ''),
                    'impact': self._calculate_impact(item),
                    'currency_pairs': self._extract_currency_pairs(item),
                    'sentiment': float(item.get('overall_sentiment_score', 0.0)),
                    'url': item.get('url', '')
                }
                news_items.append(news_item)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse Alpha Vantage news item: {e}")
                continue
        
        return news_items
    
    def _parse_newsdata_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse NewsData.io API response"""
        news_items = []
        
        if 'results' not in data:
            return news_items
        
        for item in data['results']:
            try:
                news_item = {
                    'title': item.get('title', ''),
                    'summary': item.get('description', ''),
                    'source': item.get('source_id', ''),
                    'published_at': item.get('pubDate', ''),
                    'impact': self._calculate_impact(item),
                    'currency_pairs': self._extract_currency_pairs(item),
                    'sentiment': self._calculate_sentiment(item),
                    'url': item.get('link', '')
                }
                news_items.append(news_item)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse news item: {e}")
                continue
        
        return news_items
    
    def _parse_newsapi_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse NewsAPI response"""
        news_items = []
        
        if 'articles' not in data:
            return news_items
        
        for item in data['articles']:
            try:
                news_item = {
                    'title': item.get('title', ''),
                    'summary': item.get('description', ''),
                    'source': item.get('source', {}).get('name', ''),
                    'published_at': item.get('publishedAt', ''),
                    'impact': self._calculate_impact(item),
                    'currency_pairs': self._extract_currency_pairs(item),
                    'sentiment': self._calculate_sentiment(item),
                    'url': item.get('url', '')
                }
                news_items.append(news_item)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse news item: {e}")
                continue
        
        return news_items
    
    def _extract_currency_pairs(self, item: Dict) -> List[str]:
        """Extract currency pairs from news item"""
        text = (item.get('title', '') + ' ' + item.get('description', '')).upper()
        pairs = []
        
        # Common currency pairs
        currency_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'NZD/USD']
        
        for pair in currency_pairs:
            if pair in text or pair.replace('/', '') in text:
                pairs.append(pair.replace('/', '_'))
        
        return pairs
    
    def _calculate_impact(self, item: Dict) -> str:
        """Calculate news impact level"""
        text = (item.get('title', '') + ' ' + item.get('description', '')).lower()
        
        # High impact keywords
        high_impact = ['fed', 'ecb', 'boe', 'rate', 'inflation', 'gdp', 'unemployment', 
                      'crisis', 'recession', 'war', 'election', 'brexit']
        
        # Medium impact keywords
        medium_impact = ['economic', 'policy', 'trade', 'market', 'forex', 'currency']
        
        high_count = sum(1 for keyword in high_impact if keyword in text)
        medium_count = sum(1 for keyword in medium_impact if keyword in text)
        
        if high_count >= 2:
            return 'high'
        elif high_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_sentiment(self, item: Dict) -> float:
        """Calculate sentiment score (-1 to 1)"""
        text = (item.get('title', '') + ' ' + item.get('description', '')).lower()
        
        # Positive keywords
        positive = ['positive', 'growth', 'increase', 'rise', 'bullish', 'strong', 
                   'improve', 'gain', 'profit', 'success']
        
        # Negative keywords
        negative = ['negative', 'decline', 'decrease', 'fall', 'bearish', 'weak', 
                   'worse', 'loss', 'crisis', 'recession']
        
        pos_count = sum(1 for keyword in positive if keyword in text)
        neg_count = sum(1 for keyword in negative if keyword in text)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        return (pos_count - neg_count) / (pos_count + neg_count)
    
    def get_news_analysis(self, currency_pairs: List[str] = None) -> Dict[str, Any]:
        """Get news analysis for trading decisions"""
        try:
            news_data = asyncio.run(self.get_news_data(currency_pairs))
            
            if not news_data:
                return {
                    'overall_sentiment': 0.0,
                    'market_impact': 'low',
                    'trading_recommendation': 'hold',
                    'confidence': 0.0,
                    'key_events': [],
                    'risk_factors': [],
                    'opportunities': []
                }
            
            # Calculate overall sentiment
            sentiments = [item.get('sentiment', 0.0) for item in news_data]
            overall_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            
            # Calculate market impact
            high_impact_count = sum(1 for item in news_data if item.get('impact') == 'high')
            medium_impact_count = sum(1 for item in news_data if item.get('impact') == 'medium')
            
            if high_impact_count >= 2:
                market_impact = 'high'
            elif high_impact_count >= 1 or medium_impact_count >= 2:
                market_impact = 'medium'
            else:
                market_impact = 'low'
            
            # Generate trading recommendation
            if market_impact == 'high':
                if overall_sentiment > 0.3:
                    trading_recommendation = 'buy'
                elif overall_sentiment < -0.3:
                    trading_recommendation = 'sell'
                else:
                    trading_recommendation = 'avoid'
            else:
                if overall_sentiment > 0.2:
                    trading_recommendation = 'buy'
                elif overall_sentiment < -0.2:
                    trading_recommendation = 'sell'
                else:
                    trading_recommendation = 'hold'
            
            # Extract key events
            key_events = [item['title'] for item in news_data if item.get('impact') == 'high']
            
            # Identify risk factors
            risk_factors = []
            for item in news_data:
                if item.get('impact') == 'high' and item.get('sentiment', 0) < -0.3:
                    risk_factors.append(f"High impact negative news: {item['title']}")
            
            # Identify opportunities
            opportunities = []
            for item in news_data:
                if item.get('impact') == 'high' and item.get('sentiment', 0) > 0.3:
                    opportunities.append(f"Positive catalyst: {item['title']}")
            
            return {
                'overall_sentiment': overall_sentiment,
                'market_impact': market_impact,
                'trading_recommendation': trading_recommendation,
                'confidence': min(len(news_data) / 10, 1.0),
                'key_events': key_events,
                'risk_factors': risk_factors,
                'opportunities': opportunities
            }
            
        except Exception as e:
            logger.error(f"❌ News analysis failed: {e}")
            return {
                'overall_sentiment': 0.0,
                'market_impact': 'low',
                'trading_recommendation': 'hold',
                'confidence': 0.0,
                'key_events': [],
                'risk_factors': [],
                'opportunities': []
            }
    
    def should_pause_trading(self, currency_pairs: List[str] = None) -> bool:
        """Check if trading should be paused based on news.

        Notes:
        - Skips pausing for instruments listed in env NEWS_PAUSE_SKIP (comma-separated),
          default includes XAU_USD so gold momentum is not blocked.
        - NEVER pauses if news integration is disabled - only pauses when we have real news
        """
        try:
            # If news integration is disabled, NEVER pause trading
            if not self.enabled:
                return False
            
            # Bypass pause for configured instruments (default: XAU_USD)
            skip_list = os.getenv('NEWS_PAUSE_SKIP', 'XAU_USD')
            skip_instruments = {s.strip() for s in skip_list.split(',') if s.strip()}
            if currency_pairs:
                pairs = set(currency_pairs)
                if skip_instruments & pairs:
                    return False

            analysis = self.get_news_analysis(currency_pairs)
            
            # Pause trading for high impact negative news
            if (analysis['market_impact'] == 'high' and 
                analysis['overall_sentiment'] < -0.3):
                logger.warning("🚫 Trading paused due to high impact negative news")
                return True
            
            # Only pause for low confidence if we actually have news APIs enabled
            # Low confidence means no data - don't pause when APIs are working
            if analysis['confidence'] < 0.3 and len(analysis.get('key_events', [])) == 0:
                # No news data at all - don't pause, just trade on technicals
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ News pause check failed: {e}")
            return False
    
    def get_news_boost_factor(self, signal_side: str, currency_pairs: List[str] = None) -> float:
        """Get news-based boost factor for trading signals"""
        try:
            analysis = self.get_news_analysis(currency_pairs)
            
            # Boost bullish signals for positive news
            if (signal_side == 'BUY' and analysis['overall_sentiment'] > 0.2 and 
                analysis['market_impact'] in ['high', 'medium']):
                return 1.2
            
            # Boost bearish signals for negative news
            elif (signal_side == 'SELL' and analysis['overall_sentiment'] < -0.2 and 
                  analysis['market_impact'] in ['high', 'medium']):
                return 1.2
            
            # Reduce signal strength for conflicting news
            elif ((analysis['overall_sentiment'] > 0.2 and signal_side == 'SELL') or
                  (analysis['overall_sentiment'] < -0.2 and signal_side == 'BUY')):
                return 0.8
            
            return 1.0
            
        except Exception as e:
            logger.error(f"❌ News boost calculation failed: {e}")
            return 1.0
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.session:
                asyncio.run(self.session.close())
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")

# Global instance
safe_news_integration = SafeNewsIntegration()