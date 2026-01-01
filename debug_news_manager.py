import sys
sys.path.insert(0, "/opt/quant_system_clean")
import logging
logging.basicConfig(level=logging.INFO)
from news_manager import NewsManager
n = NewsManager()
print("keys", n.marketaux_keys)
print("should_call_api", n._should_make_api_call())
print("all_keys_exhausted", n._all_keys_exhausted())
print("cached_count_before", len(n.article_cache))
arts = n.fetch_latest_articles(limit=10, max_age_hours=24)
print("returned", len(arts))
print("cached_count_after", len(n.article_cache))
print("last_api_call_time", n.last_api_call_time)
