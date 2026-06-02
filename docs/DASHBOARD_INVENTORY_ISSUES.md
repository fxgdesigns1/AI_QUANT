# Dashboard Issues Inventory (Post-Probe)

**Generated:** 2026-01-13
**Source:** Authenticated Probe (20260113T011042Z)
**Status:** EVIDENCE-BACKED (Ready for Fixes)

---

## 🔴 Critical Issues (Data/Functionality Broken)

### 1. Active Trades Section - Account Undefined
**Location:** `/api/trades/active` -> Active Trades Tab
**Evidence:**
- API returns: `{"account_id_masked": "101***001", "account_suffix": "001"}`
- UI Error: Displays "Account undefined"
- **Verdict:** Frontend mapping mismatch. UI expects `account_id` or doesn't fallback to `account_id_masked`.

### 2. Active Trades Section - Invalid Date
**Location:** Active Trades Tab header
**Evidence:**
- API returns: `"refreshed_at": "2026-01-13T01:10:47.810335Z"` (ISO 8601)
- UI Display: "Refreshed: Invalid Date"
- **Verdict:** JS date parser fails on this ISO format (likely needs `new Date(isoString)`).

### 3. News Integration Disabled
**Location:** News Tab / Terminal Tab
**Evidence:**
- API `/api/news` returns: `{"enabled": false, "integration_disabled": true}`
- UI Error: "News items 0", "Integration Disabled"
- **Verdict:** Feature disabled in runtime configuration.

### 4. Performance Metrics Zero
**Location:** Performance Tab
**Evidence:**
- API `/api/performance/summary` returns valid 200 OK but all zeros.
- **Verdict:** Likely empty trade ledger (no trades executed yet due to blocks).

---

## 🟡 Warning Issues (Partial Functionality)

### 5. Structural Scanner Insufficient History
**Location:** Scanner Tab
**Evidence:**
- API `/api/v1/scanner/structural` returns "INSUFFICIENT HISTORY" for all instruments.
- **Verdict:** Candle fetch requirements > available history in paper mode.

### 6. Price Integrity Blocks (High Count)
**Location:** Terminal Tab Banner
**Evidence:**
- API `/api/status` shows `price_sanity_blocks_per_account` > 170.
- UI Banner: "Price Integrity Blocked"
- **Verdict:** Valid system behavior (safety blocking), but indicates strategy/price alignment issue (M14).

---

## 🟢 Verified Working
- **Endpoints:** All 13/13 endpoints reachable (200 OK).
- **Tabs:** All 10/10 tabs load without 404/500 errors.
- **Auth:** Cloudflare Access working (tunnel functional).
