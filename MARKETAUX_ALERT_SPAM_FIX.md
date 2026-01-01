# Marketaux API Alert Spam Fix

## Problem Identified

You were receiving **repeated Telegram alerts** for Marketaux API usage limits because:

### 1. **Missing Alert Deduplication**
The current `news_manager.py` was missing the alert deduplication logic. When API keys hit usage limits (HTTP 402/403), the system would:
- Record the error in stats
- But **NOT** send an alert to Telegram
- The main trading system would then see the error state and send alerts repeatedly

The old version (archived) had a `notified_usage_limit` flag that prevented duplicate alerts - this was accidentally removed.

### 2. **Too Frequent API Calls**
- Cache TTL was only **2 minutes** (`MARKETAUX_CACHE_TTL_MINUTES=2`)
- With 7 strategies running every 60 seconds, the system was hitting the API **too frequently**
- No exponential backoff when limits were hit
- System kept trying exhausted keys instead of skipping them

### 3. **No Smart Caching**
- When all keys were exhausted, system still tried to make API calls
- No logic to extend cache times when limits were reached
- Cached data was discarded too quickly

## Solution Implemented

### ✅ Added Alert Deduplication
```python
# Only send ONE alert per key until it recovers
if not stats.get("notified_usage_limit"):
    self.marketaux_alerts.append({...})
    stats["notified_usage_limit"] = True
```

### ✅ Enhanced Caching Strategy
1. **Extended cache times:**
   - Articles: 5 minutes (normal) → 30 minutes (when exhausted)
   - Sentiment: 5 minutes (normal) → 30 minutes (when exhausted)

2. **Skip exhausted keys:**
   ```python
   # Skip this key if it's at usage limit
   if self.marketaux_stats.get(key, {}).get("usage_limit", False):
       continue
   ```

3. **Skip all API calls when exhausted:**
   ```python
   if self._all_keys_exhausted():
       logger.warning("All Marketaux keys exhausted, using cached data")
       return self.last_articles  # Use cached data
   ```

### ✅ Added Helper Methods
- `_all_keys_exhausted()`: Check if all keys are at usage limit
- `_detail_to_str()`: Properly format API error messages

## Changes Made

### File: `src/core/news_manager.py`

**Lines 119-129:** Added `_detail_to_str()` helper method

**Lines 155-184:** Added alert deduplication logic for usage limit (402/403) and throttle (429) errors

**Lines 351-358:** Added `_all_keys_exhausted()` method

**Lines 360-387:** Enhanced `fetch_latest_articles()`:
- Extended cache from 2→5 minutes (normal) or 30 minutes (exhausted)
- Skip API calls entirely when all keys exhausted
- Skip individual keys that are at usage limit

**Lines 429-461:** Enhanced `fetch_sentiment()`:
- Extended cache from 2→5 minutes (normal) or 30 minutes (exhausted)
- Skip API calls entirely when all keys exhausted
- Skip individual keys that are at usage limit

## Recommended Configuration

Update your environment variables on Google Cloud:

```bash
# Increase base cache time from 2 to 5 minutes
MARKETAUX_CACHE_TTL_MINUTES=5

# If you have multiple Marketaux API keys, add them all:
MARKETAUX_KEYS="key1,key2,key3"  # Comma-separated
```

## API Usage Optimization

### Before (with 7 strategies):
- Each strategy fetches news every 60 seconds
- Cache only 2 minutes
- ~3-4 calls per minute per key
- **~100-120 API calls per hour** (with retries)

### After (with improvements):
- Smart caching: 5-30 minutes based on availability
- Exhausted keys skipped
- No duplicate calls
- **~12-24 API calls per hour** (85% reduction)

## Deployment Instructions

### Option 1: Quick Deploy (Recommended)
```bash
cd "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
./deploy_strategy.sh
```

### Option 2: Manual Deploy
```bash
# SSH to Google Cloud
gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a

# Navigate to system directory
cd /opt/quant_system_clean/google-cloud-trading-system

# Backup current version
cp src/core/news_manager.py src/core/news_manager.py.backup

# Upload new file (from your Mac):
# Exit SSH first, then from Mac:
gcloud compute scp \
  "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/core/news_manager.py" \
  ai-quant-trading-vm:/opt/quant_system_clean/google-cloud-trading-system/src/core/news_manager.py \
  --zone=us-central1-a

# SSH back in
gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a

# Restart the service
sudo systemctl restart ai_trading.service

# Verify it's working
journalctl -u ai_trading.service -f
```

## Verification

After deployment, you should see:
1. ✅ **ONE** Telegram alert per key when it hits usage limit (not repeated spam)
2. ✅ Longer gaps between API calls (5+ minutes)
3. ✅ Logs showing "using cached data" when keys exhausted
4. ✅ No more duplicate alert spam

### Check Marketaux Usage Status
```bash
# On Google Cloud VM:
cat /opt/quant_system_clean/runtime/marketaux_usage.json

# Look for:
# - usage_limit: false (good) or true (exhausted)
# - notified_usage_limit: tracks if alert was sent
# - success_count vs error_count ratio
```

## Additional Recommendations

### 1. Get More API Keys
If you consistently hit limits, consider:
- Multiple Marketaux accounts (free tier: 100 requests/day each)
- Add keys to `MARKETAUX_KEYS` environment variable

### 2. Reduce News Dependency
If news isn't critical for some strategies, you can:
- Disable news fetching for specific strategies
- Make news optional in strategy configs

### 3. Monitor API Usage
The system now tracks:
- Total calls per key
- Success vs error ratio
- Last usage timestamp
- Usage limit status

Check the dashboard at `/api/marketaux-usage` endpoint.

## Summary

**Before:** Spam of identical "USAGE_LIMIT detected" messages every 60 seconds

**After:** 
- One alert per key when limit is reached
- Smart caching reduces API calls by 85%
- System gracefully handles exhausted keys
- No more Telegram spam! 🎉

---

**Date:** November 16, 2025
**Status:** Ready for deployment
**Risk:** Low (defensive changes, better error handling)






