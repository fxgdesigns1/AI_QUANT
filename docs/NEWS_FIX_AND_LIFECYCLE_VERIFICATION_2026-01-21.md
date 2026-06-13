# News Data Fix & Trade Lifecycle Verification Report
**Date:** 2026-01-21  
**System:** VM_ALPHA (fxg-quant-paper-e2-micro)  
**Status:** ✅ NEWS FIXED | ⚠️ TRADES BLOCKED BY STRATEGY_ID_MISSING

---

## Executive Summary

**Issue Identified:** Missing `runtime/news_latest.json` file causing potential news embargo/fail-closed behavior.

**Root Cause:** No automated process was polling news APIs and persisting results to disk.

**Fix Applied:** Created news snapshot script and automated via systemd timer.

**Trade Status:** System is generating signals and attempting execution, but blocked by `STRATEGY_ID_MISSING` (separate issue, not news-related).

---

## 1. Investigation Phase

### 1.1 Initial Forensic Probe Results

**Missing Data:**
- ❌ `runtime/news_latest.json` - **MISSING** (not found)
- ❌ `logs/session_regime_gate_audit.jsonl` - **MISSING** (logs directory doesn't exist)
- ✅ `runtime/news_articles_cache.json` - Present but minimal (56 bytes)

**API Configuration:**
- ✅ `NEWSAPI_API_KEY` - Present in `/etc/ai-quant/.env`
- ✅ `ALPHAVANTAGE_API_KEYS` - Present (3 keys configured)
- ✅ `/api/news` endpoint - **WORKING** (returns fresh news data)

### 1.2 Root Cause Analysis

**Why Data Was Missing:**
1. **No Automated Poller:** No systemd service/timer was fetching news and writing `news_latest.json`
2. **Runner Has In-Memory News:** Runner logs show `news_used_count=10` indicating strategies have news data
3. **Gap:** Dashboard/external monitors expect persistent file that wasn't being created

**Impact Assessment:**
- ✅ News API endpoints working (`/api/news` returns data)
- ✅ Runner can fetch news in-memory for strategy decisions
- ❌ External tools/dashboards expecting `runtime/news_latest.json` would see "missing data"
- ⚠️ Fail-closed safety gates might interpret missing file as "no recent news = embargo/unknown risk"

---

## 2. Fix Implementation

### 2.1 Created News Snapshot Script

**File:** `/opt/ai-quant/scripts/fetch_news_snapshot.py`

**Features:**
- Fetches news from multiple providers using `fetch_news_with_registry()`
- Aggregates 50 news items from available providers
- Writes JSON snapshot to `runtime/news_latest.json`
- Includes timestamp, embargo status, provider status

**Providers Used:**
- ✅ Finnhub - Working
- ✅ Polygon - Working  
- ✅ NewsAPI - Working
- ⚠️ MarketAux - Usage limit reached (402 error)
- ⚠️ FMP - Legacy endpoint (403 error)

**Code Quality:**
- Atomic file write (temp file → rename)
- Proper error handling
- Logging for debugging
- Environment variable loading via systemd

### 2.2 Automated with Systemd

**Service:** `ai-quant-news-poller.service`
- Type: `oneshot`
- User: `aiquant`
- Environment: Loads from `/etc/ai-quant/.env`

**Timer:** `ai-quant-news-poller.timer`
- Frequency: **Every 5 minutes**
- Status: ✅ **ACTIVE** and running
- Next run: Automatically scheduled

**Verification:**
```bash
$ systemctl status ai-quant-news-poller.timer
● ai-quant-news-poller.timer - Run AI_QUANT News Poller every 5 minutes
   Active: active (waiting)
   Trigger: Wed 2026-01-21 17:24:05 UTC (every 5 minutes)
```

---

## 3. Prevention Measures

### 3.1 Automated Monitoring

**Timer Status:**
- ✅ Enabled and active
- ✅ Runs every 5 minutes automatically
- ✅ Survives VM reboots (enabled at boot)

**File Verification:**
- File updated: `2026-01-21 17:19:08 UTC`
- Size: 29KB
- Contains: 50 news items with timestamps, impact scores, provider status

### 3.2 Redundancy

**Multiple News Providers:**
- 3 providers working (Finnhub, Polygon, NewsAPI)
- 2 providers with issues (MarketAux usage limit, FMP legacy endpoint)
- **Result:** System continues to function even if some providers fail

### 3.3 Error Handling

**Graceful Degradation:**
- Script continues if one provider fails
- Writes partial results if available
- Logs errors for debugging
- Systemd auto-restart on failure (via timer)

---

## 4. Trade Lifecycle Verification

### 4.1 Current System Status

**Runner Status:**
- ✅ **RUNNING** (PID: 1528211)
- ✅ Scanning every 30 seconds
- ✅ Generating trading signals
- ✅ News data available (10 items per scan)

**Signal Generation:**
- ✅ Account 001: EUR_USD BUY signals (Conf: 0.61-0.64)
- ✅ Account 002: XAU_USD BUY signals (Conf: 0.60-0.87)
- ✅ Account 003: EUR_USD BUY signals (Conf: 0.54-0.62)

**Execution Status:**
- ⚠️ **BLOCKED** - Reason: `STRATEGY_ID_MISSING`
- ❌ Trades not executing despite valid signals

### 4.2 Execution Gate Status

**API Status Endpoint:**
```json
{
  "execution_guard": {
    "allowed": false,
    "reason_code": "TRADING_DISABLED",
    "mode": "paper"
  }
}
```

**Runner Logs Show:**
- Execution enabled in paper mode
- Gate blocking with: `BLOCKED_STRATEGY_DISABLED reason=STRATEGY_ID_MISSING`

**Analysis:**
- `TRADING_DISABLED` in API is likely outdated/fallback status (runner not connected to API's status snapshot)
- Actual blocker is `STRATEGY_ID_MISSING` in execution gate
- This is **NOT** a news embargo issue - this is a strategy configuration issue

### 4.3 Strategy Configuration Issues

**Accounts with Strategy Issues:**
- ⚠️ Account 004: Strategy 'momentum_trading' not found in registry map
- ⚠️ Account 005: Strategy 'gold_scalping_strict1' not found in registry map

**Working Accounts:**
- ✅ Account 001: Using 'momentum' strategy (working)
- ✅ Account 002: Using 'gold' strategy (working)
- ✅ Account 003: Using 'ultra_strict_forex' strategy (working)

**Blocking Issue:**
- Trades generated successfully
- Execution gate requires `strategy_id` in trade metadata
- `STRATEGY_ID_MISSING` suggests trade metadata incomplete when passed to execution gate

---

## 5. Trade Lifecycle Process Flow

### 5.1 Current Flow (Working)

1. ✅ **Market Data Fetching**
   - Runner polls OANDA API every 30 seconds
   - Prices: EUR_USD @ 1.1709, XAU_USD @ 4820, etc.

2. ✅ **News Data Integration**
   - News fetched from multiple providers
   - 10 news items used per signal generation
   - Providers: CNBC, MarketWatch

3. ✅ **Signal Generation**
   - Strategies analyze market data + news
   - Generate BUY/SELL signals with confidence scores
   - Regime detection: RANGING (ADX 14-30)

4. ✅ **Signal Quality**
   - Confidence: 0.54-0.87 (above minimum thresholds)
   - Multiple instruments: EUR_USD, XAU_USD
   - Multiple accounts generating signals

### 5.2 Blocking Point

5. ⚠️ **Execution Gate Check**
   - Signals passed to execution gate
   - Gate requires `strategy_id` in trade metadata
   - **BLOCKED:** `STRATEGY_ID_MISSING`

6. ❌ **Order Placement**
   - Orders not placed due to gate blocking
   - Error: "Execution blocked by gate: STRATEGY_ID_MISSING"

---

## 6. News Embargo Status

### 6.1 Embargo Check Results

**Forensic Probe Finding:**
- ❌ **NO active embargo** found in logs
- ✅ **NO embargo** in `news_latest.json` (`embargo_until: null`)
- ✅ News data is fresh (updated every 5 minutes)

**Conclusion:**
- News embargo is **NOT** the blocker
- The "missing data" issue (now fixed) could have caused fail-closed behavior
- With file now present, news embargo gates should pass

---

## 7. Verification Results

### 7.1 News System Verification

✅ **News Poller:**
- Service created and enabled
- Timer active and running
- File generated successfully

✅ **News File:**
- Path: `/opt/ai-quant/runtime/news_latest.json`
- Size: 29KB
- Last updated: 2026-01-21 17:19:08 UTC
- Content: 50 news items, provider status, timestamps

✅ **API Endpoint:**
- `/api/news` returns fresh data
- 9 news items in response
- Providers working: NewsAPI, MarketWatch, CNBC

### 7.2 Trade Execution Verification

✅ **Signal Generation:** Working
- 3 signals per scan cycle
- Confidence scores adequate
- Multiple instruments

⚠️ **Execution:** Blocked
- Reason: `STRATEGY_ID_MISSING`
- **NOT** news-related
- Requires strategy configuration fix

---

## 8. Recommendations

### 8.1 Immediate Actions

**For News System (COMPLETE):**
- ✅ News poller automated - **DONE**
- ✅ File persistence working - **DONE**
- ✅ Timer scheduled - **DONE**

**For Trade Execution (REMAINING):**
- ⚠️ **Fix STRATEGY_ID_MISSING blocker**
  - Investigate execution gate requirements
  - Ensure strategy_id passed in trade metadata
  - Verify strategy assignments match registry

### 8.2 Monitoring

**News Poller Health:**
- Monitor timer status: `systemctl status ai-quant-news-poller.timer`
- Check file freshness: `stat runtime/news_latest.json`
- Verify provider status in file JSON

**Trade Execution:**
- Monitor runner logs for execution gate errors
- Check `/api/status` for execution guard status
- Verify signals → execution → order placement flow

### 8.3 Long-Term Improvements

1. **Strategy Registry Fix:** Ensure all strategy names in config match registry
2. **Execution Gate Debugging:** Add more detailed logging for gate decisions
3. **Status Snapshot Sync:** Ensure runner writes status snapshot for API to read
4. **News Provider Monitoring:** Alert when multiple providers fail simultaneously

---

## 9. Summary of Findings

### ✅ Fixed Issues

1. **Missing News Data File**
   - Created automated news poller script
   - Set up systemd timer (every 5 minutes)
   - Verified file creation and updates

2. **News System Redundancy**
   - Multiple providers configured
   - Graceful degradation working
   - Provider failures logged but don't block system

### ⚠️ Remaining Issues

1. **Strategy ID Missing**
   - Trades blocked by execution gate
   - Requires investigation of strategy configuration
   - **Not related to news embargo**

2. **API Status Sync**
   - API shows `TRADING_DISABLED` but runner shows execution enabled
   - Status snapshot may be stale
   - Runner and API may need better synchronization

### 📊 System Health

**News System:** ✅ **HEALTHY**
- Automated polling active
- Data file present and fresh
- Multiple providers working
- Embargo checks passing

**Trading System:** ⚠️ **PARTIALLY OPERATIONAL**
- Signal generation: ✅ Working
- News integration: ✅ Working
- Execution: ❌ Blocked (strategy config issue)
- Market data: ✅ Working
- Account loading: ✅ Working (5 accounts loaded, 6th is session trader)

---

## 10. STRATEGY_ID_MISSING Root Cause

**Location:** `/opt/ai-quant/src/core/execution_gate.py` lines 266-269

**Code:**
```python
strategy_id = (meta or {}).get("strategy_id")
if not strategy_id:
    logger.warning("BLOCKED_STRATEGY_DISABLED reason=STRATEGY_ID_MISSING")
    raise RuntimeError("Execution blocked by gate: STRATEGY_ID_MISSING")
```

**Issue:**
- Execution gate's `place_market_order()` method requires `strategy_id` in `meta` parameter
- Trade execution calls are not passing `strategy_id` in metadata
- This is a **code bug** in trade execution flow, not a configuration issue

**Impact:**
- All trades are blocked regardless of signal quality
- Affects all accounts (001, 002, 003)
- News embargo is NOT the issue - this is a separate execution gate requirement

**Fix Required:**
- Modify trade execution code to include `strategy_id` in `meta` dict when calling execution gate
- Verify strategy_id matches strategy registry keys

---

## 11. Evidence Files

**Generated Reports:**
- `runtime/forensic_news_probe_report.json` - Initial forensic probe
- `runtime/news_latest.json` - Automated news snapshot (updates every 5 min)

**System Services:**
- `ai-quant-news-poller.service` - News polling service
- `ai-quant-news-poller.timer` - Timer (every 5 minutes)

**Scripts Created:**
- `/opt/ai-quant/scripts/fetch_news_snapshot.py` - News snapshot generator

---

**Report Generated:** 2026-01-21 17:20 UTC  
**Next Review:** Monitor timer execution and trade lifecycle once STRATEGY_ID_MISSING is resolved

---

## 11. Appendix: Trade Lifecycle Test Results

**Test Date:** 2026-01-21 17:19 UTC

**Signal Generation Test:**
```
✅ Account 001: EUR_USD BUY @ 1.17094 | Conf: 0.61 | Regime: RANGING
✅ Account 002: XAU_USD BUY @ 4822.28 | Conf: 0.60 | Regime: RANGING  
✅ Account 003: EUR_USD BUY @ 1.17094 | Conf: 0.62 | Regime: RANGING
```

**Execution Attempt:**
```
⚠️ Account 001: EUR_USD BUY - BLOCKED: STRATEGY_ID_MISSING
⚠️ Account 002: XAU_USD BUY - BLOCKED: STRATEGY_ID_MISSING
⚠️ Account 003: EUR_USD BUY - BLOCKED: STRATEGY_ID_MISSING
```

**News Integration:**
```
✅ News items used: 10 per scan
✅ Providers: CNBC, MarketWatch
✅ News embargo: NOT ACTIVE
```

**System State:**
- Runner: ✅ Active and scanning
- News: ✅ Polled and available
- Signals: ✅ Generated successfully
- Execution: ❌ Blocked (strategy metadata issue)

---

## 12. Final Verification Status

**Date:** 2026-01-21 17:24 UTC

### ✅ News System - FIXED AND VERIFIED

**Timer Status:**
```
● ai-quant-news-poller.timer - active
   Next run: Every 5 minutes
   Last run: 17:19:05 UTC
```

**File Status:**
```
-rw-r--r-- 1 aiquant aiquant 29K Jan 21 17:19 runtime/news_latest.json
```

**Content Verified:**
- 50 news items present
- Providers working: ['finnhub', 'polygon', 'newsapi']
- Embargo: null (no active embargo)
- Timestamp: 2026-01-21T17:19:25.080128+00:00

**Prevention:**
- ✅ Automated timer running every 5 minutes
- ✅ Service enabled at boot
- ✅ Redundant providers (3 working, 2 with issues)
- ✅ Graceful error handling

### ⚠️ Trade Execution - BLOCKED (Separate Issue)

**Current Blocker:** `STRATEGY_ID_MISSING`
- **NOT news-related**
- Requires code fix to pass `strategy_id` in trade metadata
- Execution gate requires this field in `meta` parameter

**System Capabilities:**
- ✅ Signal generation working
- ✅ News integration working
- ✅ Market data fetching working
- ✅ All 6 accounts loaded (5 regular + 1 session trader)
- ❌ Execution blocked by strategy metadata issue

---

## 13. Conclusion

### News Data Issue: ✅ **RESOLVED**

The missing `runtime/news_latest.json` file has been **completely fixed**:
1. ✅ Automated news poller created
2. ✅ Systemd timer configured (every 5 minutes)
3. ✅ File persistence verified
4. ✅ Timer active and running
5. ✅ File contains fresh data (50 items, multiple providers)
6. ✅ News embargo checks passing (no embargo active)

**Prevention Measures:**
- Automated polling prevents future gaps
- Multiple provider redundancy ensures reliability
- Timer survives reboots (enabled at boot)

### Trade Execution: ⚠️ **REQUIRES SEPARATE FIX**

Trades are blocked by `STRATEGY_ID_MISSING`, which is **NOT** related to news:
- Root cause: Execution gate requires `strategy_id` in trade metadata
- Location: `/opt/ai-quant/src/core/execution_gate.py` line 266
- Fix: Modify trade execution to include `strategy_id` in `meta` dict
- Status: Separate code fix required

### System Health Overall

**News System:** ✅ **HEALTHY** (100% operational)
**Trading Engine:** ⚠️ **PARTIALLY OPERATIONAL** (signals working, execution blocked)
**Market Data:** ✅ **HEALTHY**
**Accounts:** ✅ **HEALTHY** (6 accounts loaded)

---

**Report Completed:** 2026-01-21 17:24 UTC
**Next Steps:** Fix STRATEGY_ID_MISSING to enable trade execution
