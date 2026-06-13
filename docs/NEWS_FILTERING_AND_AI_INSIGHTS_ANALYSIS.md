# News Filtering & AI Insights Analysis

**Generated**: 2026-01-13  
**Status**: Filtering exists but may be too permissive; AI insights exist but NOT displayed in UI

---

## 🔍 Question 1: Does News Filter Out Nonsense?

### ✅ YES - Filtering Logic Exists

**Location**: `src/control_plane/api.py:1728-1825`

**What Gets EXCLUDED:**
- Sports (world cup, soccer, football, scores like "0-2")
- Entertainment (movies, celebrities, TV shows)
- Food/Lifestyle (recipes, restaurants)
- Tech reviews (product reviews, apps)
- Religion (pope, church)
- Crypto (bitcoin, blockchain) - unless also mentions forex
- General politics (Venezuela, Panama, war on drugs)

**What Gets INCLUDED (Must Match ONE):**
1. **Primary forex keywords**: "forex", "FX market", "currency pair", "EURUSD", "GBPUSD", "gold price"
2. **FX symbols**: EURUSD, GBPUSD, USDJPY, XAUUSD, etc.
3. **2+ Secondary keywords**: "federal reserve" + "interest rate" + "inflation"
4. **1 Secondary + Currency name**: "federal reserve" + "dollar"

### ⚠️ PROBLEM: Filter May Be Too Permissive

**Example from your screenshot:**
- News about "Federal Reserve Chair Powell" + "DOJ subpoenas"
- This passes because:
  - "federal reserve" is a secondary keyword
  - If it also mentions "interest rate" or "monetary policy" → passes filter
  - BUT: This is political/legal news, NOT trading-relevant

**The Issue:**
- Political news about the Fed (legal battles, subpoenas) gets through
- It mentions "Fed" which is a secondary keyword
- But it's not directly about monetary policy or trading

**Current Filter Logic:**
```python
# Line 1818: Include if ANY of these:
if has_primary or has_fx_symbol or secondary_count >= 2 or has_currency_with_economic:
    filtered_items.append(item)
```

**Recommendation:**
- Add exclusion for political/legal keywords: "subpoena", "indictment", "DOJ", "legal battle"
- OR: Require PRIMARY keyword + secondary (not just secondary alone)
- OR: Add negative sentiment filter for political news

---

## 🔍 Question 2: Does It Give Trade Insights?

### ✅ YES - AI Insights Endpoint Exists

**Location**: `/api/news/assess` (`src/control_plane/api.py:1915-2012`)

**What It Provides:**
- ✅ **AI Summary**: Gemini/OpenAI-generated market analysis
- ✅ **Sentiment**: positive/negative/neutral
- ✅ **Impact Score**: 1-10 scale
- ✅ **Per-Provider Signals**: Analysis by news provider
- ✅ **Model Used**: "gemini" or "openai"

**Query Used:**
```python
query="forex OR currency OR central bank OR interest rate"
```

### ❌ PROBLEM: AI Insights NOT Displayed in UI

**Current UI Behavior:**
- `loadNews()` function (line 1159) only calls `/api/news`
- It does NOT call `/api/news/assess`
- So AI insights are generated but never shown!

**What You're Missing:**
- AI-generated market summary
- Sentiment analysis
- Impact scores
- Trade recommendations

---

## 📊 Current Status

| Feature | Status | Location |
|---------|--------|----------|
| News Filtering | ✅ Exists | `api.py:1728-1825` |
| Filter Quality | ⚠️ Too Permissive | Political news gets through |
| AI Insights Backend | ✅ Working | `/api/news/assess` (Gemini verified) |
| AI Insights UI | ❌ NOT Displayed | `loadNews()` doesn't call assess endpoint |

---

## 🎯 Recommendations

### 1. Improve Filtering (Reduce Political Noise)

**Option A: Add Political Exclusion**
```python
exclude_keywords.extend([
    'subpoena', 'indictment', 'doj', 'department of justice',
    'legal battle', 'lawsuit', 'court case', 'criminal charge',
    'threatens', 'threatened', 'political attack'
])
```

**Option B: Require Primary Keyword**
```python
# Only include if has PRIMARY keyword (not just secondary)
if has_primary or has_fx_symbol:
    # Then check secondary for additional context
    if has_secondary:
        filtered_items.append(item)
```

### 2. Wire Up AI Insights Display

**Update `loadNews()` function to:**
1. Call `/api/news/assess` after loading news items
2. Display AI summary in a prominent card at top of news feed
3. Show sentiment and impact score
4. Display "Powered by Gemini" or "Powered by OpenAI"

**Example UI Addition:**
```javascript
// After loading news items, call assess endpoint
const aiData = await apiGet("/api/news/assess");
if (aiData.ok && aiData.summary) {
    // Add AI insights card at top of news feed
    container.innerHTML = `
        <div class="glass-card p-6 rounded-xl border-l-4 border-[#00ff88] mb-6">
            <div class="flex items-center gap-2 mb-3">
                <span class="text-2xl">🧠</span>
                <h3 class="font-bold text-lg text-white">AI Market Analysis</h3>
                <span class="chip chip-success text-[8px]">${aiData.model}</span>
            </div>
            <p class="text-sm text-gray-300 leading-relaxed mb-4">${aiData.summary}</p>
            <div class="flex gap-4 text-xs">
                <span>Sentiment: <strong>${aiData.sentiment}</strong></span>
                <span>Impact: <strong>${aiData.impact_score}/10</strong></span>
            </div>
        </div>
    ` + container.innerHTML;
}
```

---

## ✅ Verification Needed

1. **Test Current Filtering:**
   - Check if political news about Fed/DOJ is being filtered
   - Verify if only trading-relevant news passes

2. **Test AI Insights:**
   - Call `/api/news/assess` directly
   - Verify summary, sentiment, impact_score are present

3. **Wire Up UI:**
   - Add AI insights display to News tab
   - Test that it shows when news loads

---

## 📝 Summary

**Filtering:**
- ✅ Exists and works
- ⚠️ May be too permissive (political news gets through)
- 🔧 Needs refinement to exclude non-trading political news

**AI Insights:**
- ✅ Backend working (Gemini verified)
- ❌ NOT displayed in UI
- 🔧 Needs UI integration to show AI summary and trade insights
