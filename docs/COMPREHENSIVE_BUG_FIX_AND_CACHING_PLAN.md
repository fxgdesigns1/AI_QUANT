# Comprehensive Bug Fix & Smart Caching Implementation

**Date**: 2026-01-13  
**Status**: URGENT - Fix all bugs and implement smart caching

---

## 🔍 User Concerns

1. **Sections show "Loading..." forever** - Not actually completed
2. **Need smart caching**: News (10 min), Account Info (30 sec), Prices (NO cache)
3. **0 dummy/placeholder text** - Remove all "Loading..." and placeholder text
4. **Caching must not reduce performance**

---

## 🐛 Bugs Identified

### 1. News Tab Shows "Loading..." Forever
**Problem**: `loadNews()` function may be failing silently  
**Root Cause**: Need to check actual API responses and error handling

### 2. Outlook Tab Shows "Loading outlook..."
**Problem**: `loadOutlook()` may not be completing  
**Root Cause**: Need to check `/api/v1/outlook` endpoint

### 3. Account Info Not Cached
**Problem**: `/api/trades/active` called repeatedly (hits OANDA API limit)  
**Solution**: Add 30-second cache for account info

### 4. Prices May Be Cached (WRONG)
**Problem**: Need to ensure prices are NEVER cached  
**Solution**: Verify `updateLivePrices()` doesn't use cache

### 5. Placeholder/Dummy Text
**Problem**: Various "Loading..." states that never clear  
**Solution**: Replace with real data or explicit empty states

---

## ✅ Implementation Plan

### Step 1: Fix Smart Caching for Account Info

Add caching to `loadActiveTrades()`:
```javascript
// Cache account info for 30 seconds
const data = await smartFetch("active_trades", "/api/trades/active", 30);
```

### Step 2: Ensure Prices Are NOT Cached

Verify `updateLivePrices()` uses `apiGet()` directly (NOT `smartFetch`):
```javascript
// Prices: NO caching (must be real-time)
const data = await apiGet("/api/market/prices?instruments=XAU_USD");
```

### Step 3: Fix Error Handling

All functions should:
- Show explicit error messages (not "Loading...")
- Hide loading state on error
- Display error state clearly

### Step 4: Remove All Placeholder Text

Replace:
- "Loading..." → Real data or explicit empty state
- "Loading outlook..." → Real outlook or "No outlook available"
- "Loading strategies..." → Real strategies or "No strategies configured"

### Step 5: Backend Caching (Optional)

Add backend caching for news:
- Cache news for 10 minutes in memory
- Use snapshot cache if available

---

## 📝 Files to Modify

1. **`templates/forensic_command.html`**
   - Add account info caching (30 sec)
   - Verify prices use `apiGet` (NOT `smartFetch`)
   - Fix error handling in all load functions
   - Remove placeholder text

2. **`src/control_plane/api.py`** (Optional)
   - Add backend caching for news (if needed)
   - Add account info caching (if needed)

---

## 🎯 Verification Checklist

- [ ] News tab shows cached news immediately
- [ ] Account info cached for 30 seconds
- [ ] Prices always fresh (no cache)
- [ ] No "Loading..." states remain
- [ ] No placeholder/dummy text
- [ ] All sections show real data or explicit empty states
- [ ] Error messages are clear and actionable
