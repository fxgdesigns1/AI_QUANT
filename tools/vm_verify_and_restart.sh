#!/usr/bin/env bash
set -euo pipefail

# VM verification wrapper:
# 1) Prints environment vars relevant to news caching
# 2) Shows cache file permissions and head
# 3) Restarts news_manager.service (if present) or runs deploy script
# 4) Runs the Python verify script and prints output

echo "=== ENV VARS ==="
echo "NEWS_CACHE_DAYS=${NEWS_CACHE_DAYS:-<not set>}"
echo "NEWS_MIN_API_INTERVAL_SECONDS=${NEWS_MIN_API_INTERVAL_SECONDS:-<not set>}"
echo "MARKETAUX_KEYS=${MARKETAUX_KEYS:-<not set>}"
echo "NEWS_API_KEY=${NEWS_API_KEY:-<not set>}"

CACHE_PATH="./runtime/news_articles_cache.json"
echo
echo "=== CACHE FILE STATUS ==="
if [ -f \"$CACHE_PATH\" ]; then
  ls -l \"$CACHE_PATH\"
  echo "CACHE HEAD:"
  head -n 40 \"$CACHE_PATH\" || true
else
  echo "Cache file not found at $CACHE_PATH"
fi

echo
echo "=== RESTART SERVICE / DEPLOY ==="
if systemctl --version >/dev/null 2>&1 && systemctl list-units --type=service | grep -q news_manager; then
  echo "Restarting news_manager.service via systemctl"
  sudo systemctl restart news_manager.service
  sleep 2
  sudo systemctl status news_manager.service --no-pager --lines=20 || true
else
  if [ -x ./deploy_news_manager_fix.sh ]; then
    echo "Running deploy_news_manager_fix.sh"
    ./deploy_news_manager_fix.sh
  else
    echo "No systemd service or deploy script found; skipping restart step"
  fi
fi

echo
echo "=== RUN VERIFY SCRIPT ==="
PYTHONPATH=. python3 tools/verify_news_cache.py || true

echo
echo "=== TAIL LOGS (if present) ==="
LOG_PATH="./runtime/news_manager.log"
if [ -f \"$LOG_PATH\" ]; then
  tail -n 200 \"$LOG_PATH\"
else
  echo "No runtime/news_manager.log present"
fi

echo
echo "=== DONE ==="




