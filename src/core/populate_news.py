#!/usr/bin/env python3
import os
import sys
import json

# Load env file
env_path = '/opt/quant_system_clean/google-cloud-trading-system/oanda_config.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for ln in f:
            if '=' in ln and not ln.strip().startswith('#'):
                k, v = ln.strip().split('=', 1)
                v = v.strip().strip('"')
                os.environ[k] = v

sys.path.insert(0, '/opt/quant_system_clean/google-cloud-trading-system')
from src.core.news_manager import NewsManager

def main():
    nm = NewsManager()
    articles = nm.fetch_latest_articles(limit=50, max_age_hours=24)
    print('fetched', len(articles), 'articles')
    for a in articles:
        key = a.get('url') or a.get('id') or a.get('title')
        if not key:
            key = str(hash(json.dumps(a, sort_keys=True)))
        a['cached_at'] = a.get('published_at') or a.get('cached_at') or __import__('datetime').datetime.utcnow().isoformat()
        nm.article_cache[key] = a
    nm._save_article_cache()
    print('cache now', len(nm.article_cache))
    try:
        latest = nm._get_latest_cached_article_date()
        print('latest cached at', latest)
    except Exception as e:
        print('no latest date', e)

if __name__ == '__main__':
    main()


