import os
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

# Assuming news_cache.py exists and has a simple caching mechanism
try:
    from .news_cache import get_news_cache
    NEWS_CACHE_AVAILABLE = True
except ImportError:
    NEWS_CACHE_AVAILABLE = False
    logging.warning("⚠️ News cache not available. News integration will not use caching.")

logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    description: str
    url: str
    published_at: datetime
    sentiment: float = 0.0 # -1 (bearish) to 1 (bullish)

class MarketAuxClient:
    """
    Client for interacting with the MarketAux API.
    Handles API key rotation and request limiting.
    """
    def __init__(self):
        self.api_keys = os.getenv('MARKETAUX_KEYS', '').split(',')
        if not self.api_keys or not self.api_keys[0]:
            logger.error("❌ MARKETAUX_KEYS environment variable not set or empty.")
            self.api_keys = []
        self.current_key_idx = 0
        self.last_request_time = 0
        self.request_interval = 1 # 1 second between requests to avoid hitting limits quickly
        self.base_url = "https://api.marketaux.com/v1/news/all"
        logger.info(f"✅ MarketAuxClient initialized with {len(self.api_keys)} API keys.")

    def _get_next_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        key = self.api_keys[self.current_key_idx]
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        return key

    def _rate_limit_wait(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def fetch_news(self, symbols: Optional[List[str]] = None, filter_entities: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches news articles from MarketAux.
        `symbols`: filter by stock symbols (e.g., ["TSLA", "AAPL"])
        `filter_entities`: filter by currency pairs (e.g., ["EURUSD", "XAUUSD"])
        """
        api_key = self._get_next_key()
        if not api_key:
            logger.error("❌ No MarketAux API key available to fetch news.")
            return []

        params = {
            "api_token": api_key,
            "language": "en",
            "limit": limit,
        }
        if symbols:
            params["symbols"] = ",".join(symbols)
        if filter_entities:
            # MarketAux API uses symbols parameter for both stocks and forex pairs
            # We'll use it for filter_entities as well, assuming they are tradable symbols
            params["symbols"] = ",".join(filter_entities) # This will override if symbols was also set

        self._rate_limit_wait()
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ MarketAux API request failed: {e}")
            return []

class NewsManager:
    """
    Manages news fetching, caching, and sentiment analysis for trading strategies.
    """
    def __init__(self, marketaux_client: MarketAuxClient):
        self.marketaux_client = marketaux_client
        self.news_cache = get_news_cache() if NEWS_CACHE_AVAILABLE else None
        self.cache_ttl_minutes = int(os.getenv('MARKETAUX_CACHE_TTL_MINUTES', '5'))
        self.last_fetch_time: Dict[str, datetime] = {}
        logger.info("✅ NewsManager initialized.")

    def _get_cached_news(self, key: str) -> Optional[List[NewsArticle]]:
        if self.news_cache:
            cached_data = self.news_cache.get(key)
            if cached_data:
                articles_data = json.loads(cached_data)
                articles = [
                    NewsArticle(
                        title=a['title'],
                        description=a['description'],
                        url=a['url'],
                        published_at=datetime.fromisoformat(a['published_at']),
                        sentiment=a.get('sentiment', 0.0)
                    )
                    for a in articles_data
                ]
                return articles
        return None

    def _set_cached_news(self, key: str, articles: List[NewsArticle]):
        if self.news_cache:
            articles_data = [
                {
                    'title': a.title,
                    'description': a.description,
                    'url': a.url,
                    'published_at': a.published_at.isoformat(),
                    'sentiment': a.sentiment
                }
                for a in articles
            ]
            self.news_cache.set(key, json.dumps(articles_data), self.cache_ttl_minutes * 60)

    def fetch_and_analyze_news(self, instruments: List[str], limit: int = 10) -> List[NewsArticle]:
        """
        Fetches news for given instruments, caches it, and performs sentiment analysis.
        """
        cache_key = "news_" + "_".join(sorted(instruments))
        cached_news = self._get_cached_news(cache_key)

        if cached_news and (datetime.now() - self.last_fetch_time.get(cache_key, datetime.min)) < timedelta(minutes=self.cache_ttl_minutes):
            logger.info(f"📰 Using cached news for {instruments}")
            return cached_news

        logger.info(f"📰 Fetching fresh news for {instruments}...")
        # MarketAux uses 'symbols' for both stock and forex, so we pass instruments as symbols
        raw_articles = self.marketaux_client.fetch_news(filter_entities=instruments, limit=limit)
        processed_articles: List[NewsArticle] = []

        for article_data in raw_articles:
            try:
                published_at = datetime.fromisoformat(article_data['published_at'].replace('Z', '+00:00'))
                sentiment = self._analyze_sentiment(article_data.get('description', '') + " " + article_data.get('title', ''))
                processed_articles.append(
                    NewsArticle(
                        title=article_data.get('title', 'N/A'),
                        description=article_data.get('description', 'N/A'),
                        url=article_data.get('url', 'N/A'),
                        published_at=published_at,
                        sentiment=sentiment
                    )
                )
            except Exception as e:
                logger.warning(f"⚠️ Error processing news article: {e}")
        
        self._set_cached_news(cache_key, processed_articles)
        self.last_fetch_time[cache_key] = datetime.now()
        logger.info(f"✅ Fetched and analyzed {len(processed_articles)} news articles for {instruments}.")
        return processed_articles

    def _analyze_sentiment(self, text: str) -> float:
        """
        Simple keyword-based sentiment analysis for a given text.
        Returns a score between -1 (bearish) and 1 (bullish).
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        positive_keywords = ["bullish", "gain", "rise", "strong", "up", "gains", "positive", "rally", "growth", "improve"]
        negative_keywords = ["bearish", "loss", "drop", "weak", "down", "losses", "negative", "decline", "fall", "cut"]
        
        score = 0
        for keyword in positive_keywords:
            if keyword in text_lower:
                score += 1
        for keyword in negative_keywords:
            if keyword in text_lower:
                score -= 1
        
        if score > 0:
            return min(1.0, score / 3) # Cap at 1.0
        elif score < 0:
            return max(-1.0, score / 3) # Cap at -1.0
        return 0.0

    def get_news_analysis(self, instruments: List[str]) -> Dict[str, Any]:
        """
        Provides an overall news sentiment and list of recent articles for instruments.
        """
        articles = self.fetch_and_analyze_news(instruments)
        if not articles:
            return {"overall_sentiment": 0.0, "recent_articles": []}

        total_sentiment = sum(a.sentiment for a in articles)
        overall_sentiment = total_sentiment / len(articles) if articles else 0.0

        return {
            "overall_sentiment": overall_sentiment,
            "recent_articles": [a.title for a in articles] # Return titles for brevity
        }

    def should_pause_trading(self, instruments: List[str]) -> bool:
        """
        Determines if trading should be paused due to high-impact negative news.
        """
        analysis = self.get_news_analysis(instruments)
        if analysis["overall_sentiment"] < -0.7: # Strong bearish sentiment
            logger.warning(f"🚫 High-impact negative news detected for {instruments}. Trading pause recommended.")
            return True
        return False

    def get_news_boost_factor(self, trade_direction: str, instruments: List[str]) -> float:
        """
        Returns a confidence boost factor based on news sentiment aligning with trade direction.
        """
        analysis = self.get_news_analysis(instruments)
        sentiment = analysis["overall_sentiment"]

        if trade_direction.upper() == "BUY" and sentiment > 0.2:
            return 1.15 # 15% boost for bullish news
        elif trade_direction.upper() == "SELL" and sentiment < -0.2:
            return 1.15 # 15% boost for bearish news
        elif abs(sentiment) < 0.1:
            return 1.0 # Neutral news
        else:
            return 0.9 # Small penalty if news contradicts or is strongly neutral against direction

# Global instance and getter for easy integration
_news_manager: Optional[NewsManager] = None

def get_news_manager() -> NewsManager:
    global _news_manager
    if _news_manager is None:
        client = MarketAuxClient()
        _news_manager = NewsManager(client)
    return _news_manager

# Alias for backward compatibility if old code still calls safe_news_integration directly
def safe_news_integration(instruments: List[str], *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return get_news_manager().get_news_analysis(instruments)
