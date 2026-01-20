# News AI Fix - Deployment Status

**Date**: 2026-01-19  
**Status**: ✅ Code Deployed, ⚠️ Service Needs Restart

## Summary

Fixed News AI insights endpoint to properly analyze sentiment and return summary/impact_score. Code changes have been committed and deployed to VM, but the running service needs to be restarted to use the new code.

## Changes Made

### 1. Fixed `/api/news/assess` Endpoint (`src/control_plane/api.py`)
- **Issue**: Endpoint only checked snapshot, didn't fetch from provider when snapshot was empty
- **Fix**: Now fetches news from provider registry when snapshot has no news
- **Added**: Sentiment analysis using keyword heuristics
- **Returns**: `summary`, `sentiment`, `impact_score` fields

### 2. Updated Dashboard Templates
- `dashboard/templates/dashboard_advanced.html`: Added AI insights display in `loadNewsData()`
- `templates/forensic_command.html`: Already had rendering logic, now receives correct data

### 3. Added Verification Scripts
- `scripts/test_news_ai_playwright.py`: Comprehensive Playwright test for News AI
- `scripts/verify_news_ai_fix.py`: Verification script
- `scripts/test_dashboard_tunnel.py`: Dashboard tunnel testing
- `scripts/quick_tunnel.sh`: Quick tunnel setup
- `scripts/start_tunnel_and_test.sh`: Full tunnel + test setup

## Git Commit

```
Commit: 5452e83
Message: Fix News AI insights on dashboard
Files: 8 files changed, 4468 insertions(+), 1588 deletions(-)
```

## Deployment Status

✅ **Code Deployed**: Changes pushed to VM via `push_repo_to_vm.sh`  
⚠️ **Service Status**: Service needs restart to load new code  
✅ **Files Verified**: Code changes confirmed on VM  

## Current Issue

The running service is returning a response structure that doesn't match the new code:
- Returns: `providers_used`, `providers_used_status` (old structure)
- Expected: `summary`, `sentiment`, `impact_score` (new structure)

This indicates the service process is still using cached bytecode or hasn't restarted.

## Next Steps

1. **Restart Service** (requires proper permissions):
   ```bash
   # On VM
   sudo systemctl restart ai-quant-control-plane.service
   # OR
   pkill -9 -f 'python.*control_plane' && sleep 2
   cd ~/gcloud-system && CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh
   ```

2. **Verify Fix**:
   ```bash
   curl http://127.0.0.1:28787/api/news/assess | jq '.data | {summary, sentiment, impact_score}'
   ```

3. **Test with Playwright**:
   ```bash
   python3 scripts/test_news_ai_playwright.py
   ```

## Expected Response (After Restart)

```json
{
  "data": {
    "ok": true,
    "news_count": 30,
    "summary": "Market sentiment remains NEUTRAL across 30 analyzed news items...",
    "sentiment": "neutral",
    "impact_score": 5,
    "provider": "AI_QUANT_INTERNAL",
    "timestamp": 1768861034.3495
  }
}
```

## Files Modified

- `src/control_plane/api.py` - Fixed `/api/news/assess` endpoint
- `dashboard/templates/dashboard_advanced.html` - Added AI insights display
- `templates/forensic_command.html` - (Already had rendering logic)
- Various test scripts added

## Verification

Once service is restarted, verify with:
```bash
# Check endpoint
curl http://127.0.0.1:28787/api/news/assess | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d.get('data', {})
print('✅ Summary:', 'summary' in data)
print('✅ Sentiment:', 'sentiment' in data)
print('✅ Impact Score:', 'impact_score' in data)
"

# Run Playwright test
python3 scripts/test_news_ai_playwright.py
```
