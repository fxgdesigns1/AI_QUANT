#!/usr/bin/env python3
"""
Fetch latest Marketaux articles and populate the deployed news article cache file.
Intended to run on the VM as root so it writes to /opt/quant_system_clean/runtime/news_articles_cache.json.
"""
import json
import os
from datetime import datetime
import requests

OUTPUT_PATH = "/opt/quant_system_clean/runtime/news_articles_cache.json"

def discover_key():
    # 1) Try runtime usage snapshot produced by the service
    candidates = [
        "/opt/quant_system_clean/runtime/marketaux_usage.json",
        "/home/mac/runtime/marketaux_usage.json",
        "/opt/quant_system_clean/google-cloud-trading-system/runtime/marketaux_usage.json",
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    keys = [k.get("key") for k in data.get("keys", []) if k.get("key")]
                    if keys:
                        return keys[0]
        except Exception:
            continue
    # 2) Fallback to environment variable
    env_val = os.getenv("MARKETAUX_KEYS", "") or os.getenv("MARKETAUX_KEY", "")
    if env_val:
        return env_val.split(",")[0].strip()
    return None

def main():
    MARKETAUX_KEY = discover_key()
    if not MARKETAUX_KEY:
        print("No Marketaux key discovered; aborting")
        return
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "limit": 20,
        "language": "en",
        "api_token": MARKETAUX_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            print("Marketaux fetch failed:", r.status_code, r.text[:200])
            return
        data = r.json().get("data", [])
        # Build article cache dict keyed by uuid/url
        cache = {}
        for entry in data:
            article_id = entry.get("uuid") or entry.get("url") or entry.get("title")
            if not article_id:
                continue
            cache[article_id] = {
                "title": entry.get("title"),
                "summary": entry.get("description") or entry.get("summary"),
                "published_at": entry.get("published_at"),
                "url": entry.get("url"),
                "source": entry.get("source"),
                "sentiment": entry.get("sentiment", 0.0),
                "entities": entry.get("entities", []),
                "cached_at": datetime.utcnow().isoformat(),
            }
        payload = {
            "updated_at": datetime.utcnow().isoformat(),
            "article_count": len(cache),
            "articles": cache,
        }
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print("Wrote cache with", len(cache), "articles to", OUTPUT_PATH)
    except Exception as exc:
        print("Fetch or write failed:", exc)

if __name__ == "__main__":
    main()


