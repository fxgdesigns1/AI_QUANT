#!/usr/bin/env python3
"""
Verification helper: fetch from intelligent cache and print summary.
Run on the VM to verify cache population and sentiment calculation.
"""
import json
from typing import List

def main():
    try:
        from src.core.news_cache import fetch_latest_articles, fetch_sentiment
    except Exception as exc:
        print("ERROR: failed to import news_cache:", exc)
        return

    articles = fetch_latest_articles(limit=10, max_age_hours=48)
    sentiment = fetch_sentiment(window_minutes=60)
    print("Fetched articles:", len(articles))
    print("Sentiment (cached window 60m):", sentiment)
    print("Sample articles:")
    for a in (articles[:3] or []):
        print(f"- {a.get('title') or 'untitled'} ({a.get('published_at')})")

if __name__ == "__main__":
    main()




