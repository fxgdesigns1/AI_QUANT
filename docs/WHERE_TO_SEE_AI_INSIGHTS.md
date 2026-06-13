# Where to See AI Insights

**Generated**: 2026-01-13  
**Dashboard URL**: https://alpha.fxgdesigns.co.uk  
**Status**: ✅ AI Insights Operational (Gemini + OpenAI)

---

## 📍 Location 1: News Tab → AI Insights

**How to Access:**
1. Go to https://alpha.fxgdesigns.co.uk
2. Click **"News AI"** tab in the left sidebar (📰 icon)
3. The News tab displays:
   - News headlines from `/api/news`
   - AI analysis from `/api/news/assess` (if wired in UI)

**What You'll See:**
- News items with impact ratings (HIGH/MEDIUM/LOW)
- AI-generated summaries (if `/api/news/assess` is called)
- Sentiment analysis
- Impact scores

**Current Status:**
- ✅ `/api/news/assess` endpoint is **WORKING** (verified with Gemini)
- ⚠️ UI may need to be updated to display AI insights from this endpoint
- The News tab currently shows news items but may not display the AI summary

---

## 📍 Location 2: Outlook Tab → Market Outlook

**How to Access:**
1. Go to https://alpha.fxgdesigns.co.uk
2. Click **"Outlook"** tab in the left sidebar
3. Select horizon: Daily / Weekly / Monthly
4. Click **"Recompute"** to regenerate outlooks

**What You'll See:**
- Market outlook for each instrument (EUR/USD, GBP/USD, etc.)
- Bias (BULLISH/BEARISH/NEUTRAL)
- Scenarios with probabilities
- Key support/resistance levels

**Endpoint:** `/api/v1/outlook/{horizon}`

---

## 📍 Location 3: Live Terminal → Active Signal

**How to Access:**
1. Go to https://alpha.fxgdesigns.co.uk
2. Click **"Live Terminal"** tab (default view)
3. Look at the **"Active Signal"** section in the sidebar

**What You'll See:**
- Current trading signal
- Instrument, side (BUY/SELL), confidence
- Signal metadata

**Endpoint:** `/api/signals/pending`

---

## 🔍 Direct API Access (For Verification)

You can verify AI insights are working by calling the endpoint directly:

```bash
curl https://alpha.fxgdesigns.co.uk/api/news/assess
```

**Expected Response:**
```json
{
  "ok": true,
  "model": "gemini",
  "summary": "AI-generated market analysis...",
  "sentiment": 0.65,
  "impact_score": 7.5,
  "ai_meta": {
    "provider_used": "gemini",
    "enabled": true,
    "mode": "advisory",
    "latency_ms": 1234
  },
  "news_count": 10,
  "ts_utc": 1234567890.0
}
```

---

## ✅ Verification Status

**AI Insights Endpoint (`/api/news/assess`):**
- ✅ **WORKING** - Verified 3+ times
- ✅ **Model**: `gemini-2.5-flash`
- ✅ **Provider**: Gemini (with OpenAI fallback)
- ✅ **Summary**: AI-generated text present
- ✅ **Non-Destructive**: OpenAI preserved

**Outlook Endpoint (`/api/v1/outlook/{horizon}`):**
- ✅ **EXISTS** - Returns market outlook
- ⚠️ May return stub data if not fully integrated

**Signals Endpoint (`/api/signals/pending`):**
- ✅ **EXISTS** - Returns pending signals
- ✅ **UI Wired** - Displayed in Live Terminal

---

## 🎯 Next Steps (If AI Insights Not Visible in UI)

If you don't see AI insights in the News tab, the UI may need to be updated to:
1. Call `/api/news/assess` endpoint
2. Display the `summary` field
3. Show `sentiment` and `impact_score`
4. Display `ai_meta.provider_used` (e.g., "Powered by Gemini")

**Current Implementation:**
- The News tab (`templates/forensic_command.html`) calls `/api/news` for news items
- It does NOT currently call `/api/news/assess` for AI insights
- The endpoint is working, but needs to be wired into the UI

---

## 📝 Summary

**Where to Look:**
1. **News AI Tab** → News items (AI insights endpoint exists but may not be displayed)
2. **Outlook Tab** → Market outlook analysis
3. **Live Terminal** → Active trading signals

**AI Insights Status:**
- ✅ Backend operational (Gemini + OpenAI)
- ⚠️ UI may need update to display AI insights from `/api/news/assess`
