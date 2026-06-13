# Dashboard Truth Lockdown - Final Fixes Applied

**Date**: 2026-01-22  
**Status**: ✅ **FIXES APPLIED**

---

## Issues Found in Screenshot

1. ❌ **"EXECUTION ON PAPER"** - UI-derived combined label
2. ❌ **Market prices show "-"** instead of "MISSING"
3. ❌ **URL is localhost** instead of tunnel URL

---

## Fixes Applied

### 1. Removed UI-Derived "EXECUTION ON" Label ✅

**File**: `frontend/fxg-dashboard/src/Dashboard.jsx` (line ~553)

**Before**:
```javascript
text={getField(data.status.data, 'execution_enabled', false) ? "EXECUTION ON" : "EXECUTION OFF"}
```

**After**:
```javascript
text={getField(data.status.data, 'execution_enabled', false) ? "ENABLED" : "DISABLED"}
// Plus separate mode badge and reason code if blocked
```

**Result**: Header now shows:
- `ENABLED` / `DISABLED` (from `execution_enabled`)
- `PAPER` / `LIVE` (from `mode`)
- `BLOCKED: <reason_code>` (from `execution_guard.reason_code` if disabled)

### 2. Fixed Market Prices to Show "MISSING" ✅

**File**: `frontend/fxg-dashboard/src/Dashboard.jsx` (line ~243-246)

**Before**:
```javascript
{inst.mid !== null && inst.mid !== undefined ? inst.mid : MISSING}
```

**After**:
```javascript
{inst.mid !== null && inst.mid !== undefined && inst.mid !== "" ? inst.mid : MISSING}
```

**Result**: Empty strings now also show "MISSING" instead of "-"

### 3. Tunnel URL Configuration ✅

**File**: `playwright.config.js`

**Current**: Defaults to `https://alpha-dashboard.fxg.internal`

**To Use**: Set environment variable:
```bash
export DASHBOARD_URL=https://alpha-dashboard.fxg.internal
npx playwright test
```

---

## Next Steps

1. **Rebuild frontend** (if needed):
   ```bash
   cd frontend/fxg-dashboard
   npm run build
   ```

2. **Restart dashboard service** (on VM):
   ```bash
   sudo systemctl restart ai-quant-control-plane
   ```

3. **Run tests with tunnel URL**:
   ```bash
   export DASHBOARD_URL=https://alpha-dashboard.fxg.internal
   npx playwright test tests/dashboard/dashboard_truth.spec.ts
   ```

4. **Verify in browser**:
   - Visit `https://alpha-dashboard.fxg.internal`
   - Check header shows "ENABLED"/"DISABLED" + "PAPER" separately
   - Check market prices show "MISSING" not "-"
   - Verify no "EXECUTION ON PAPER" combined label

---

## Expected Result

**Header should show**:
- `ENABLED` (green) or `DISABLED` (gray)
- `BLOCKED: <reason>` (red) if execution disabled with reason
- `PAPER` or `LIVE` (yellow warning badge)

**Market Overview should show**:
- `MISSING` for null/undefined/empty bid/ask/mid values
- Not "-" or empty strings

**URL should be**:
- `https://alpha-dashboard.fxg.internal` (tunnel)
- Not `127.0.0.1:8787` (localhost)

---

**Status**: ✅ **CODE FIXED - NEEDS DEPLOYMENT & VERIFICATION**
