#!/usr/bin/env python3
"""
Force a news fetch on the VM by instantiating the deployed news_manager and calling fetch_latest_articles.
Run this script on the VM (it expects /opt/quant_system_clean in PYTHONPATH).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/opt/quant_system_clean")

try:
    from news_manager import NewsManager
except Exception as exc:
    print("ERROR: failed to import news_manager:", exc)
    raise

def main():
    nm = NewsManager()
    arts = nm.fetch_latest_articles(limit=20, max_age_hours=24)
    print("ARTICLES_FETCHED:", len(arts))
    print("CACHE_PATH:", nm.article_cache_path)
    print("CACHE_EXISTS:", nm.article_cache_path.exists())
    if nm.article_cache:
        # print a small sample
        keys = list(nm.article_cache.keys())[:3]
        for k in keys:
            a = nm.article_cache[k]
            print("-", a.get("title"), a.get("published_at"))

if __name__ == "__main__":
    main()




