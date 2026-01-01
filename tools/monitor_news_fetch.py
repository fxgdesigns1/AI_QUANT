#!/usr/bin/env python3
"""
Monitor news cache and Marketaux activity on the VM and write a small log.
Writes to /tmp/news_monitor.log. Intended to run on the VM.
"""
import json
import os
import time
from datetime import datetime

OUT_PATH = "/tmp/news_monitor.log"
CACHE_PATH_CANDIDATES = [
    "/opt/quant_system_clean/runtime/news_articles_cache.json",
    "/home/mac/runtime/news_articles_cache.json",
    "/opt/quant_system_clean/google-cloud-trading-system/runtime/news_articles_cache.json",
]
USAGE_PATH = "/opt/quant_system_clean/runtime/marketaux_usage.json"

def read_cache_info():
    for p in CACHE_PATH_CANDIDATES:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    updated = data.get("updated_at")
                    count = data.get("article_count") or (len(data.get("articles", {})) if isinstance(data.get("articles"), dict) else 0)
                    return p, updated, count
        except Exception:
            continue
    return None, None, 0

def read_usage():
    try:
        if os.path.exists(USAGE_PATH):
            with open(USAGE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def log(msg: str):
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} - {msg}\\n")

def main():
    iterations = 10
    interval = 60  # seconds
    log("Starting news monitor (10 iterations, 60s interval)")
    for i in range(iterations):
        path, updated, count = read_cache_info()
        usage = read_usage()
        keys = usage.get("keys", []) if isinstance(usage, dict) else []
        key_status = [(k.get("masked_key"), k.get("last_status")) for k in keys]
        log(f"iter={i+1} cache_path={path} updated={updated} article_count={count} marketaux_keys={len(keys)} key_status={key_status}")
        # Also attempt a quick journal check (if available)
        try:
            import subprocess
            out = subprocess.check_output(["journalctl", "-u", "ai_trading.service", "-n", "20", "--no-pager"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            # Look for API call success lines
            matched = [l for l in out.splitlines() if ("API call successful" in l or "Fetched" in l or "Fetching articles" in l)]
            if matched:
                log("journal_hits: " + "; ".join(matched[-5:]))
        except Exception:
            pass
        time.sleep(interval)
    log("Monitor finished")

if __name__ == "__main__":
    main()




