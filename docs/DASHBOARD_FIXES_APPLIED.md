# Dashboard Fixes Applied (Restored)

**Last Updated:** 2026-01-13
**Status:** In Progress

---

## 🛑 Critical Fixes (Pre-Probe)

### 1. Fix "Account undefined" in Active Trades
- **Issue:** Active trades display "Account undefined" and "Invalid Date"
- **Status:** ❌ Pending Verification
- **Action:** 
  - Update `templates/forensic_command.html` `loadActiveTrades()`
  - Implement robust account ID masking/fallback
  - Fix date parsing for `refreshed_at`

### 2. Fix News Integration
- **Issue:** News tab shows "Integration Disabled" or 0 items
- **Status:** ❌ Pending Verification
- **Action:**
  - Verify `news_integration_enabled` in runtime config
  - Check news provider wiring
  - Ensure `/api/news` returns valid structure

### 3. Fix Performance Metrics
- **Issue:** Performance tab shows all zeros
- **Status:** ❌ Pending Verification
- **Action:**
  - Verify trade ledger writes in `src/control_plane/trade_ledger.py`
  - Check `/api/performance/summary` aggregation logic

---

## 🟡 Functionality Fixes

### 4. Structural Scanner
- **Issue:** "Insufficient History" for all instruments
- **Status:** ❌ Pending Verification
- **Action:**
  - Check candle history fetch requirements
  - Verify scanner data pipeline

### 5. Signal Display
- **Issue:** Active Signal widget shows empty/scanning state
- **Status:** ❌ Pending Verification
- **Action:**
  - Verify `/api/signals/pending`
  - Check signal generation logic

---

## ✅ Completed Fixes (History)

*(None in this session yet)*
