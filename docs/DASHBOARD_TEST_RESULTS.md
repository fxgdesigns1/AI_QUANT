# Dashboard Test Results

**Date:** 2026-01-21  
**Test Suite:** `verification/test_dashboard_endpoints.py`  
**Server:** http://127.0.0.1:8787

---

## Test Summary

**Total Endpoints Tested:** 12  
**✅ Passed:** 9  
**❌ Failed:** 3

---

## Core Endpoints ✅

All core endpoints are working correctly:

| Endpoint | Status | Truth Envelope | Notes |
|---|---|---|---|
| `/health` | ✅ OK | N/A | Health check working |
| `/api/status` | ✅ OK | COMPLETE | System status available |
| `/api/truth/status` | ✅ OK | COMPLETE | Truth system operational |
| `/api/config` | ✅ OK | COMPLETE | Config accessible |
| `/api/strategies` | ✅ OK | COMPLETE | Strategy list available |
| `/api/trades/active` | ✅ OK | INCOMPLETE | Active trades (some accounts may not have trades) |
| `/api/market/overview` | ✅ OK | COMPLETE | Market data working |
| `/api/news` | ✅ OK | COMPLETE | News feed operational |
| `/api/performance/summary` | ✅ OK | COMPLETE | Performance metrics available |

---

## Session Regime Gate Endpoints ⚠️

**Status:** Requires server restart to load new transparency code

| Endpoint | Status | Reason |
|---|---|---|
| `/api/session-regime-gate/snapshot` | ❌ 404 | Server needs restart |
| `/api/session-regime-gate/decisions` | ❌ 404 | Server needs restart |
| `/api/session-regime-gate/statistics` | ❌ 404 | Server needs restart |

**Action Required:** Restart API server to load enhanced transparency endpoints.

**How to Restart:**
```bash
# Option 1: Stop existing server and restart
bash scripts/stop_control_plane.sh
bash scripts/start_control_plane_clean.sh

# Option 2: Restart if using systemd
sudo systemctl restart ai-quant-control-plane

# Option 3: Manual restart
pkill -f "python.*src.control_plane.api"
python3 -m src.control_plane.api
```

---

## Transparency Features to Verify (After Restart)

Once the server is restarted, the following transparency fields should be available in `/api/session-regime-gate/snapshot`:

### Required Fields
- ✅ `trade_block_reason` - Explicit reason if trading is blocked
- ✅ `block_details` - Structured details (roadmap_aligned, is_embargo, daily_bias, weekly_bias, etc.)
- ✅ `readiness` - READY | WAITING | BLOCKED indicator
- ✅ `readiness_score` - 0-100 readiness score
- ✅ `candles_remaining` - Number of candles needed before regime detection
- ✅ `eta_seconds` - Estimated time until readiness
- ✅ `next_session` - Next tradable session info:
  - `next_tradable_session` - Name (e.g., "London")
  - `countdown_seconds` - Time remaining
  - `target_utc` - Target timestamp

### Verification Command

After restart, run:
```bash
python3 verification/test_dashboard_endpoints.py
```

Expected output:
- ✅ All 12 endpoints passing
- ✅ Transparency fields check: All fields present
- ✅ Readiness indicator showing correct state
- ✅ Countdown timer working

---

## Dashboard UI Verification Checklist

Once endpoints are verified, test the dashboard UI:

### 1. Settings Modal
- [ ] Warning banner visible: "⚠️ SIMULATION / UI ONLY – NO SYSTEM EFFECT"
- [ ] No POST requests when toggling settings
- [ ] Console logs show intent-only logging

### 2. Session Gate Panel
- [ ] Readiness indicator visible (READY/WAITING/BLOCKED)
- [ ] Readiness score gauge showing (0-100)
- [ ] ETA countdown timer working (HH:MM:SS)
- [ ] Candles remaining displayed
- [ ] Block reason shown when blocked
- [ ] Current session displayed
- [ ] Next session countdown working
- [ ] Auto-refreshes every 10 seconds

### 3. Truth Badges
- [ ] All cards show source badge (REAL/MOCK/CACHE/STALE)
- [ ] STALE badge appears when freshness_ms > 30000
- [ ] "NO BACKEND FACT AVAILABLE" shown when incomplete

### 4. Network Tab
- [ ] Only GET requests visible
- [ ] No POST/PUT/PATCH/DELETE requests
- [ ] All responses wrapped in TruthEnvelope

---

## Next Steps

1. **Restart API Server** to load transparency enhancements
2. **Re-run Test Suite** to verify all endpoints
3. **Open Dashboard** in browser: http://127.0.0.1:8787
4. **Verify UI Elements** match transparency data
5. **Check Audit Log** to confirm gate decisions match UI

---

## Test Command

Run the test suite:
```bash
python3 verification/test_dashboard_endpoints.py
```

Or test individual endpoints:
```bash
# Test snapshot endpoint
curl -s "http://127.0.0.1:8787/api/session-regime-gate/snapshot" | python3 -m json.tool

# Test decisions endpoint
curl -s "http://127.0.0.1:8787/api/session-regime-gate/decisions?limit=5" | python3 -m json.tool

# Test statistics endpoint
curl -s "http://127.0.0.1:8787/api/session-regime-gate/statistics" | python3 -m json.tool
```

---

**Last Updated:** 2026-01-21  
**Test Status:** ⚠️ Pending Server Restart
