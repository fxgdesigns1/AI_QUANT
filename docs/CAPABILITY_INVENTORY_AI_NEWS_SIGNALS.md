# Capability Inventory: AI Insights, Trade Signals, News, Economic Calendar

**Generated**: 2026-01-13T01:47:25Z  
**Target**: ALPHA VM (fxg-quant-paper-e2-micro, us-east1-b)  
**Dashboard URL**: https://alpha.fxgdesigns.co.uk  
**Mode**: Paper-only, Signals-only

## Evidence Sources

- **VM Endpoint Probe**: 2026-01-13T01:47:20Z (all endpoints returned 000 - service not running)
- **Repo Scan**: grep results in `artifacts/capability_inventory/20260113T014725Z/`
- **Code Review**: `src/control_plane/api.py`, `src/control_plane/outlook_engine.py`, `src/ai/ai_insights.py`, `src/control_plane/news_provider.py`
- **UI Templates**: `templates/forensic_command.html`, `templates/dashboard_advanced.html`

---

## 1. AI Insights / Market Outlook

### Status: **PARTIALLY IMPLEMENTED** (Outlook exists, AI Insights requires keys)

### API Endpoints

| Endpoint | Status | HTTP Code (VM) | Implementation |
|----------|--------|----------------|----------------|
| `/api/v1/outlook/{horizon}` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:256-279` |
| `/api/v1/outlook/recompute` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:282-314` |
| `/api/insights` | ⚠️ NOISE SHIM | 000 (service down) | `src/control_plane/api.py:352-360` (returns 204) |

### Implementation Details

**Outlook Engine** (`src/control_plane/outlook_engine.py`):
- **Location**: `src/control_plane/outlook_engine.py`
- **Function**: Deterministic market outlook generator (daily/weekly/monthly)
- **Current State**: Returns stub/baseline outlook (no real market data integration)
- **No Dependencies**: Works without API keys (deterministic)
- **Horizons**: `daily`, `weekly`, `monthly`
- **UI Location**: `templates/forensic_command.html` - "Outlook" tab (line 344-1349)

**AI Insights** (`src/ai/ai_insights.py`):
- **Location**: `src/ai/ai_insights.py`
- **Function**: Advisory-only AI insights using OpenAI/Gemini
- **Current State**: Code exists but requires API keys
- **Dependencies**: 
  - `OPENAI_API_KEY` OR `GOOGLE_API_KEY` / `GEMINI_API_KEY`
  - `AI_INSIGHTS_ENABLED=1` (env var)
  - `AI_INSIGHTS_MODE=advisory` (default)
  - `AI_PROVIDER=openai` (default, can be `gemini` or chain)
- **UI Location**: `templates/dashboard_advanced.html` - "AI Insights" section (line 1373-1410), but `/api/insights` returns 204 (blocked)

### Configuration

**Settings** (`src/core/settings.py:38-44, 114-125`):
- `AI_INSIGHTS_ENABLED`: boolean (default: False)
- `AI_INSIGHTS_MODE`: string (default: "advisory")
- `OPENAI_API_KEY`: Optional[str]
- `OPENAI_MODEL`: string (default: "gpt-4o-mini")
- `GOOGLE_API_KEY` / `GEMINI_API_KEY`: Optional[str]
- `GEMINI_MODEL`: string (default: "gemini-1.5-flash")
- `AI_PROVIDER`: string (default: "openai")

### Feasibility Verdict

- **Outlook**: ✅ **FEASIBLE NOW** - No keys required, returns stub data, UI wired
- **AI Insights**: ⚠️ **NEEDS KEYS** - Code exists but requires `AI_INSIGHTS_ENABLED=1` + API key (OpenAI or Google)

### Next Actions

1. **Outlook**: Verify `/api/v1/outlook/daily` returns data when service is running (stub is fine)
2. **AI Insights**: If keys available, enable via `AI_INSIGHTS_ENABLED=1` + provider key
3. **UI**: `/api/insights` is blocked (returns 204) - remove UI references OR unblock if AI insights enabled

---

## 2. Trade Suggestions / Signals

### Status: **IMPLEMENTED** (Returns signals from status snapshot)

### API Endpoints

| Endpoint | Status | HTTP Code (VM) | Implementation |
|----------|--------|----------------|----------------|
| `/api/signals/pending` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:1415-1443` |

### Implementation Details

**Signals Endpoint** (`src/control_plane/api.py:1415-1443`):
- **Location**: `src/control_plane/api.py:1415-1443`
- **Function**: Returns pending signals from status snapshot
- **Source**: `status_snapshot.read().get("recent_signals", [])`
- **Execution Mode**: Signals-only (returns `execution_enabled: false` by default)
- **No Dependencies**: Reads from status snapshot (no API keys)
- **UI Location**: 
  - `templates/forensic_command.html` - "Live Terminal" tab, "Active Signal" section (line 257-336, 1395-1491)
  - `templates/dashboard_advanced.html` - "Trading Signals" section (line 1650-1687)

### Payload Schema

```json
{
  "ok": true,
  "signals": [...],
  "active_strategy": "...",
  "last_scan_utc": "...",
  "execution_enabled": false,
  "note": "Signals generated but NOT executed (signals-only)",
  "ts_utc": 1234567890.0
}
```

### Feasibility Verdict

✅ **FEASIBLE NOW** - Endpoint exists, reads from status snapshot, UI wired

### Next Actions

1. Verify `/api/signals/pending` returns data when status snapshot has `recent_signals`
2. Ensure UI maps fields correctly: `signal.confidence` → conviction, `signal.instrument`, `signal.side`

---

## 3. News Headlines + News Lookout

### Status: **IMPLEMENTED** (Requires config enablement + provider keys)

### API Endpoints

| Endpoint | Status | HTTP Code (VM) | Implementation |
|----------|--------|----------------|----------------|
| `/api/news` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:1690-1852` |
| `/api/news/status` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:1855-1912` |
| `/api/news/assess` | ✅ EXISTS | 000 (service down) | `src/control_plane/api.py:1915-2011` |

### Implementation Details

**News Endpoint** (`src/control_plane/api.py:1690-1852`):
- **Location**: `src/control_plane/api.py:1690-1852`
- **Function**: Fetches forex/trading news with intelligent filtering
- **Provider**: Uses `fetch_news_with_registry()` from `src/control_plane/news_provider.py`
- **Dependencies**:
  - Runtime config: `news_integration_enabled: true`
  - Provider keys: `NEWSAPI_API_KEY`, `ALPHAVANTAGE_API_KEY`, `MARKETAUX_KEY`, `FINNHUB_KEY`, `POLYGON_KEY`, `FMP_KEY` (at least one)
- **Filtering**: Intelligent forex/trading keyword filtering (excludes sports, entertainment, etc.)
- **UI Location**: 
  - `templates/forensic_command.html` - "News" tab (line 39)
  - `templates/dashboard_advanced.html` - "News" section

**News Status Endpoint** (`src/control_plane/api.py:1855-1912`):
- **Function**: Returns per-provider health status
- **No Dependencies**: Reads config (doesn't fetch)

**News Assess Endpoint** (`src/control_plane/api.py:1915-2011`):
- **Function**: AI assessment of latest news (uses `get_ai_insight()`)
- **Dependencies**: News provider keys + AI insights keys (if AI enabled)

### Configuration

**Runtime Config** (`src/control_plane/schema.py:89`):
- `news_integration_enabled`: boolean (default: False)

**Settings** (`src/core/settings.py:31-33, 90-91, 145-147`):
- `NEWSAPI_API_KEY`: Optional[str]
- `ALPHAVANTAGE_API_KEY`: Optional[str]
- `MARKETAUX_KEY`: Optional[str] (list)
- `FINNHUB_KEY`: Optional[str] (list)
- `POLYGON_KEY`: Optional[str] (list)
- `FMP_KEY`: Optional[str] (list)

### Feasibility Verdict

⚠️ **NEEDS CONFIG + KEYS** - Code exists, requires:
1. Runtime config: `news_integration_enabled: true`
2. At least one provider key (NewsAPI, AlphaVantage, MarketAux, Finnhub, Polygon, or FMP)

### Next Actions

1. Check runtime config for `news_integration_enabled`
2. If disabled, enable for ALPHA paper profile only (no secrets hardcoded)
3. If enabled but no keys, return explicit degraded state with reason
4. Verify `/api/news/status` shows provider health
5. UI: Ensure News tab shows items OR explicit "not configured" reason

---

## 4. Economic Calendar / Countdown

### Status: **NOT IMPLEMENTED** (No backend endpoints, UI uses synthetic fallback)

### API Endpoints

| Endpoint | Status | HTTP Code (VM) | Implementation |
|----------|--------|----------------|----------------|
| `/api/calendar/upcoming` | ❌ NOT FOUND | 000 (service down) | **MISSING** |
| `/api/v1/calendar/upcoming` | ❌ NOT FOUND | 000 (service down) | **MISSING** |
| `/api/econ/upcoming` | ❌ NOT FOUND | 000 (service down) | **MISSING** |

### Implementation Details

**Backend**: No implementation found
- **Location**: No code in `src/control_plane/` or `src/`
- **Search**: `grep -r "calendar\|econ" src/` found no calendar endpoints

**UI** (`templates/dashboard_advanced.html:3099-3140`):
- **Function**: `fetchEconomicCalendar()` tries `/api/status`, looks for `data.upcoming_news`
- **Fallback**: If no `upcoming_news`, creates synthetic event (next month, 8:30 AM)
- **Issue**: Creates fake countdown if backend doesn't provide real events
- **Countdown Display**: Shows countdown timer (days, hours, minutes)

**Status Endpoint** (`src/control_plane/api.py`):
- No `upcoming_news` field in `/api/status` response

### Feasibility Verdict

❌ **MISSING ENTIRELY** - No backend implementation

**Options**:
1. **Option A (Recommended)**: Implement "Calendar not configured" panel with explicit reason
2. **Option B**: Implement calendar provider integration (requires new provider + keys)
3. **Option C**: Remove UI countdown if backend doesn't provide real events (prevent fake countdowns)

### Next Actions

1. **Immediate**: Remove/fix UI synthetic event fallback (prevents fake countdowns)
2. **Decision**: Choose Option A (explicit "not configured") OR Option B (new provider)
3. **If Option A**: Add "Calendar not configured" panel with link to config docs
4. **If Option B**: Implement provider integration (e.g., Trading Economics, FXStreet, MarketWatch calendar API)

---

## Summary Matrix

| Capability | Backend Status | UI Status | Dependencies | Feasibility |
|------------|---------------|-----------|--------------|-------------|
| **Outlook** | ✅ Implemented (stub) | ✅ Wired | None | ✅ Feasible Now |
| **AI Insights** | ⚠️ Code exists, blocked | ⚠️ Referenced but blocked | API keys | ⚠️ Needs Keys |
| **Signals** | ✅ Implemented | ✅ Wired | None | ✅ Feasible Now |
| **News** | ✅ Implemented | ✅ Wired | Config + Provider keys | ⚠️ Needs Config + Keys |
| **Calendar** | ❌ Missing | ⚠️ Synthetic fallback | N/A | ❌ Missing |

---

## Recommendations

### Priority 1: Enable/Verify Existing (No New Code)
1. **Outlook**: Verify `/api/v1/outlook/daily` works when service running (should return stub)
2. **Signals**: Verify `/api/signals/pending` works (reads from status snapshot)

### Priority 2: Enable with Config (Paper Profile Only)
3. **News**: Enable `news_integration_enabled: true` in runtime config for ALPHA paper profile
4. **News**: If no provider keys, return explicit degraded state (not "disabled")

### Priority 3: Fix/Implement Missing
5. **Calendar**: Remove UI synthetic event fallback OR implement "not configured" panel
6. **AI Insights**: If keys available, enable `AI_INSIGHTS_ENABLED=1` OR remove UI references

---

## Verification Steps

After changes:

1. **VM Curl Tests**:
   ```bash
   curl http://127.0.0.1:8080/api/v1/outlook/daily
   curl http://127.0.0.1:8080/api/signals/pending
   curl http://127.0.0.1:8080/api/news/status
   curl http://127.0.0.1:8080/api/news
   ```

2. **Dashboard Probe**:
   ```bash
   python scripts/dashboard_probe.py --url https://alpha.fxgdesigns.co.uk
   ```

3. **UI Verification**: Check browser console for errors, verify tabs render correctly

---

**Next Owner**: Implementation tasks (A5) → Cursor
