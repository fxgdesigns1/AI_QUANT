# Bug Investigation & Smart Caching Implementation

**Date**: 2026-01-13  
**Status**: Investigating and fixing

---

## 🔍 Issues Identified

### 1. `smartFetch` Function Missing
- **Location**: `templates/forensic_command.html:1294, 1333`
- **Problem**: `loadNews()` calls `smartFetch()` which doesn't exist
- **Impact**: News tab shows "Loading..." forever
- **Fix**: Implement `smartFetch()` function with proper caching

### 2. No Smart Caching
- **Problem**: Every API call hits the server (wastes API quota)
- **Required**: 
  - News: Cache for 10 minutes (limited API calls)
  - Account info: Cache for 30 seconds (changes slowly)
  - Prices: NO caching (must be real-time)

### 3. Loading States Never Clear
- **Problem**: UI shows "Loading..." when API calls fail or return empty
- **Fix**: Proper error handling and empty states

### 4. Placeholder/Dummy Text
- **Problem**: Various "Loading..." and placeholder text
- **Fix**: Remove all dummy text, show real data or explicit empty states

---

## ✅ Implementation Plan

### Step 1: Implement `smartFetch` with Caching
```javascript
const cache = {}; // Simple in-memory cache

async function smartFetch(cacheKey, endpoint, ttlSeconds) {
    const now = Date.now();
    const cached = cache[cacheKey];
    
    // Return cached if fresh
    if (cached && (now - cached.timestamp < ttlSeconds * 1000)) {
        return cached.data;
    }
    
    // Fetch fresh
    const data = await apiGet(endpoint);
    
    // Cache it
    cache[cacheKey] = {
        data: data,
        timestamp: now
    };
    
    return data;
}
```

### Step 2: Cache Configuration
- **News**: 10 minutes (600 seconds)
- **AI Insights**: 15 minutes (900 seconds)
- **Account Info**: 30 seconds (30 seconds)
- **Outlook**: 5 minutes (300 seconds)
- **Prices**: NO caching (0 seconds)

### Step 3: Fix Error Handling
- Show explicit error messages instead of "Loading..."
- Remove all placeholder text
- Show empty states with clear messaging

### Step 4: Backend Caching (News API)
- News endpoint already uses snapshot cache
- Add TTL check to avoid fetching if cached news is fresh
- Cache news for 10 minutes on backend

---

## 📝 Files to Modify

1. `templates/forensic_command.html`
   - Add `smartFetch` function
   - Update `loadNews` to use `smartFetch`
   - Fix error handling
   - Remove placeholder text

2. `src/control_plane/api.py`
   - Improve news caching with TTL
   - Add account info caching (if needed)

---

## 🎯 Verification Steps

1. Open News AI tab - should show cached news immediately
2. Refresh - should use cache (no API call)
3. Wait 10 minutes - should fetch fresh news
4. Check prices - should always be fresh (no cache)
5. Check account info - should cache for 30 seconds
6. Verify no "Loading..." states remain
7. Verify no placeholder/dummy text
