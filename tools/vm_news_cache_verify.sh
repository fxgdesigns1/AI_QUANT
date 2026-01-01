#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_PATH="$REPO_ROOT/runtime/news_articles_cache.json"

echo "== VM News Cache Verification =="
echo "Repository root: $REPO_ROOT"

echo "--> Ensuring cache directory is writable"
mkdir -p "$(dirname "$CACHE_PATH")"
touch "$CACHE_PATH"
chmod 644 "$CACHE_PATH"
echo "Cache path ready: $CACHE_PATH"

echo "--> Running cache verification helper"
PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/tools/verify_news_cache.py"

echo "--> Restarting ai_trading.service to pick up new cache"
sleep 1
sudo systemctl restart ai_trading.service
echo "--> Waiting for service to settle"
sleep 5
echo "--> Recent news cache activity from journalctl"
sudo journalctl -u ai_trading.service -n 30 --no-pager | grep -Ei "news|marketaux|cache" || true

echo "== Verification complete =="

