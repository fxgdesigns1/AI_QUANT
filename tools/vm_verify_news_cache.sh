#!/usr/bin/env bash
# Shell helper for VM verification: validates cache, prints logs, optionally redeploys.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CACHE_PATH="$REPO_ROOT/runtime/news_articles_cache.json"
PYTHON_CMD="PYTHONPATH=. python3 tools/verify_news_cache.py"

echo "== News Cache Verification Helper =="
echo "Repository root: $REPO_ROOT"

mkdir -p "$(dirname "$CACHE_PATH")"
echo "- Cache path: $CACHE_PATH"
if touch "$CACHE_PATH" >/dev/null 2>&1; then
  echo "  ✅ Cache path writable"
else
  echo "  ⚠️  Cache path not writable (permissions issue)"
fi

echo ""
echo ">> Running cache verification script"
if $PYTHON_CMD; then
  echo "  ✅ Verification script ran successfully"
else
  echo "  ⚠️  Verification script failed (check output above)"
fi

echo ""
echo ">> Environment snapshot"
echo "  MARKETAUX_KEYS: ${MARKETAUX_KEYS:-<not set>}"
echo "  NEWS_API_KEY: ${NEWS_API_KEY:-<not set>}"
echo "  NEWS_CACHE_DAYS: ${NEWS_CACHE_DAYS:-7}"
echo "  NEWS_MIN_API_INTERVAL_SECONDS: ${NEWS_MIN_API_INTERVAL_SECONDS:-300}"

echo ""
systemctl >/dev/null 2>&1 && {
  echo ">> Checking ai_trading.service status"
  sudo systemctl status ai_trading.service --no-pager | head -n 20

  echo ""
  echo ">> Recent ai_trading logs (filtered for news/cache keywords)"
  journalctl -u ai_trading.service -n 100 --no-pager | grep -iE 'news|cache|marketaux' || echo "  (no matching log entries)"
} || {
  echo "  ⚠️  systemctl not available on this host; skip service/log checks"
}

if [[ "${1:-}" == "--deploy" ]]; then
  echo ""
  echo ">> Deployment requested; running deploy_news_manager_fix.sh"
  ./deploy_news_manager_fix.sh
  echo ""
  echo ">> Re-running verification script after deploy"
  $PYTHON_CMD
fi

echo ""
echo "== Verification helper complete =="

