import time
from typing import Dict, Any, Optional

class NewsCache:
    """
    A simple in-memory cache for news articles and sentiment data.
    """
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and time.time() < self._expiry[key]:
            return self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int):
        self._cache[key] = value
        self._expiry[key] = time.time() + ttl

_news_cache: Optional[NewsCache] = None

def get_news_cache() -> NewsCache:
    global _news_cache
    if _news_cache is None:
        _news_cache = NewsCache()
    return _news_cache




