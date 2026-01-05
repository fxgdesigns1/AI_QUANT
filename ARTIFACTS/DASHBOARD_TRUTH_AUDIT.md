# Dashboard Truth-Only Audit

**Date:** 2026-01-05T01:30:00Z  
**Purpose:** Inventory of dashboard panels and their data sources  
**Goal:** Make dashboard truth-only (no hardcoded/demo data)

---

## Executive Summary

**Current State:** Dashboard contains **hardcoded demo trades** and performance data  
**Target State:** All panels backed by real API endpoints or show "NOT WIRED" placeholder  
**Strategy Source:** Static Python code in `src/control_plane/strategy_registry.py` (requires restart to change)

---

## UI Panel Inventory

### templates/forensic_command.html (Primary Dashboard)

| Panel | Current Source | Status | Proposed API | Action Required |
|-------|---------------|--------|--------------|-----------------|
| **Journal Tab - Trade List** | Hardcoded HTML (trade1, trade2, trade3) | ❌ DEMO | `GET /api/journal/trades` | **CREATE** endpoint + remove hardcoded trades |
| **Journal Tab - Trade Details** | Hardcoded HTML (f92-kx, a11-zy, b54-mn) | ❌ DEMO | Same as above | Remove hardcoded HTML |
| **Performance Tab** | Hardcoded metrics (if any) | ❓ UNKNOWN | `GET /api/performance/summary` | **CREATE** endpoint |
| **Terminal Tab** | `GET /api/logs/stream` (SSE) | ✅ REAL | N/A | No change needed |
| **Mesh Tab** | `GET /api/status` | ✅ REAL | N/A | No change needed |
| **Strategies Tab** | `GET /api/strategies` | ✅ REAL | N/A | No change needed |
| **News Tab** | `GET /api/news` | ✅ REAL | N/A | No change needed |
| **Status Indicators** | `GET /api/status` | ✅ REAL | N/A | No change needed |
| **Account IDs in UI** | Various (need to check) | ❓ UNKNOWN | Redact last 4 only | **AUDIT** and redact |

### templates/dashboard_advanced.html (Fallback Dashboard)

| Panel | Current Source | Status | Proposed API | Action Required |
|-------|---------------|--------|--------------|-----------------|
| **Active Trades & Signals** | `GET /api/trades/pending` | ✅ REAL | N/A | Verify shows empty when no trades |
| **Trade Manager** | `GET /api/trades/pending` | ✅ REAL | N/A | Verify shows empty when no trades |
| **Performance Metrics** | Unknown (need to audit) | ❓ UNKNOWN | `GET /api/performance/summary` | **AUDIT** + create if needed |
| **Strategy Performance** | Hardcoded (need to verify) | ❓ UNKNOWN | `GET /api/performance/summary` | **AUDIT** + create if needed |

---

## Hardcoded Data Found

### templates/forensic_command.html

**Location:** Lines 417-797 (Journal Tab)

**Hardcoded Trades:**
1. **Trade 1** (f92-kx):
   - Trade ID: `f92-kx` (hardcoded)
   - Instrument: XAUUSD
   - P&L: +$120.50 (hardcoded)
   - Entry: 2042.85, Exit: 2055.12 (hardcoded)
   - Timestamps: 21:12:34 UTC, 21:15:08 UTC, 21:42:15 UTC (hardcoded)

2. **Trade 2** (a11-zy):
   - Trade ID: `a11-zy` (hardcoded)
   - Instrument: EURUSD
   - P&L: -$45.20 (hardcoded)
   - Entry: 1.0875, Exit: 1.0920 (hardcoded)
   - Timestamps: 18:58:12 UTC, 19:02:45 UTC, 19:08:33 UTC (hardcoded)

3. **Trade 3** (b54-mn):
   - Trade ID: `b54-mn` (hardcoded)
   - Instrument: GBPUSD
   - P&L: +$87.30 (hardcoded)
   - Entry: 1.2745, Exit: 1.2818 (hardcoded)
   - Timestamps: 17:32:08 UTC, 17:38:22 UTC, 18:15:44 UTC (hardcoded)

**Action Required:**
- ❌ **REMOVE** all hardcoded trade HTML
- ✅ **REPLACE** with API call to `GET /api/journal/trades`
- ✅ **SHOW** "No trades" message when `last_executed_count=0`

---

## Strategy Loading Analysis

### Canonical Source

**Location:** `src/control_plane/strategy_registry.py`  
**Type:** Static Python dictionary (hardcoded in code)  
**Current Strategies:**
- momentum
- gold
- range
- eur_usd_5m_safe
- momentum_v2

**Loading Mechanism:**
1. Registry is a Python dict: `STRATEGIES: Dict[str, StrategyInfo] = {...}`
2. Loaded at module import time (when API starts)
3. Accessed via `get_strategy_registry()` function
4. **NOT** reloadable at runtime (Python code doesn't change dynamically)

**Hot Reload Considerations:**
- ⚠️ **Cannot hot-reload** Python code safely
- ✅ **CAN** add new strategies to registry code, then restart API
- ✅ **CAN** validate strategy keys via `validate_strategy_key()` function
- ✅ **CAN** activate strategies via `POST /api/config` or `POST /api/strategy/activate`

**Recommendation:**
- Document that strategies are static and require code change + restart
- **DO NOT** implement `POST /api/strategies/reload` (Python code can't be safely reloaded)
- **DO** document how to add strategies (edit `strategy_registry.py` + restart)

---

## Trade Ledger Status

### Current State

**Existing Databases Found:**
- `./Sync folder MAC TO PC/.../trading_data.db` (old, not in use)
- `./Sync folder MAC TO PC/.../trading_system.db` (old, not in use)

**Active Ledger:** ❌ **NONE**

### Required Implementation

**Create JSONL Trade Ledger:**
- **Location:** `data/trade_ledger.jsonl`
- **Format:** One JSON object per line (append-only)
- **Written by:** Executor when trades are executed
- **Read by:** `GET /api/journal/trades` endpoint

**Trade Record Schema:**
```json
{
  "trade_id": "generated-uuid",
  "instrument": "XAU_USD",
  "side": "buy",
  "units": 100,
  "entry_price": 2042.85,
  "exit_price": null,
  "stop_loss": 2038.20,
  "take_profit": 2055.00,
  "entry_time": "2026-01-05T01:30:00Z",
  "exit_time": null,
  "pnl": null,
  "pnl_pips": null,
  "status": "open|closed|cancelled",
  "strategy_key": "gold",
  "account_id_redacted": "****-****-****-001",
  "signal_id": "signal-uuid-if-available"
}
```

---

## Missing Endpoints

### Required Endpoints

1. **`GET /api/journal/trades`**
   - **Purpose:** Return list of executed trades from ledger
   - **Parameters:** `?limit=N` (default: 50)
   - **Response:** `{ "ok": true, "trades": [...], "total": N, "limit": 50 }`
   - **Source:** `data/trade_ledger.jsonl`

2. **`GET /api/performance/summary`**
   - **Purpose:** Compute performance metrics from trade ledger
   - **Parameters:** `?days=N` (default: 30)
   - **Response:** `{ "ok": true, "period_days": 30, "total_trades": N, "win_rate": 0.XX, "total_pnl": X.XX, "profit_factor": X.XX, "max_drawdown": X.XX, ... }`
   - **Source:** Computed from `data/trade_ledger.jsonl`

### Optional Endpoints

3. **`POST /api/strategies/reload`**
   - **Status:** ❌ **NOT IMPLEMENTED** (Python code can't be safely reloaded)
   - **Reason:** Strategies are static Python code, not external config
   - **Alternative:** Document how to add strategies (edit code + restart)

---

## Existing Endpoints Status

| Endpoint | Method | Status | Validates Strategy Key | Notes |
|----------|--------|--------|------------------------|-------|
| `/api/config` | POST | ✅ EXISTS | ✅ YES (via schema validation) | Already validates `active_strategy_key` |
| `/api/strategy/activate` | POST | ✅ EXISTS | ✅ YES (via `validate_strategy_key()`) | Validates strategy key exists |
| `/api/strategies` | GET | ✅ EXISTS | N/A | Returns registry |
| `/api/status` | GET | ✅ EXISTS | N/A | Returns `active_strategy_key` |
| `/api/journal/trades` | GET | ❌ MISSING | N/A | **NEED TO CREATE** |
| `/api/performance/summary` | GET | ❌ MISSING | N/A | **NEED TO CREATE** |

---

## Implementation Plan

### Phase 1: Create Trade Ledger Module
- [ ] Create `src/control_plane/trade_ledger.py`
- [ ] Implement `TradeLedger` class with append-only JSONL writing
- [ ] Add account ID redaction (show last 4 only)

### Phase 2: Add Missing Endpoints
- [ ] Implement `GET /api/journal/trades` in `src/control_plane/api.py`
- [ ] Implement `GET /api/performance/summary` in `src/control_plane/api.py`
- [ ] Add validation and error handling

### Phase 3: Update Dashboard HTML
- [ ] Remove hardcoded trades from `templates/forensic_command.html`
- [ ] Add JavaScript to fetch `/api/journal/trades`
- [ ] Show "No trades" when `last_executed_count=0`
- [ ] Add "NOT WIRED" placeholder if API fails

### Phase 4: Wire Executor to Ledger
- [ ] Update executor to write to trade ledger on trade execution
- [ ] Test with paper execution
- [ ] Verify ledger writes correctly

### Phase 5: Documentation
- [ ] Document strategy loading mechanism
- [ ] Create `STRATEGY_LOADING.md`
- [ ] Update API docs

### Phase 6: Verification Script
- [ ] Create `scripts/verify_truth_only_dashboard.sh`
- [ ] Test all acceptance criteria

---

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| If `last_executed_count=0` then journal UI shows 'No trades' | ❌ NOT MET | Hardcoded trades still present |
| `/api/strategies` includes new strategy after reload | ❌ NOT APPLICABLE | Strategies are static Python code (require restart) |
| Activating strategy changes `active_strategy_key` | ✅ MET | `POST /api/config` and `POST /api/strategy/activate` both work |
| No panel displays numbers not backed by API | ❌ NOT MET | Journal tab has hardcoded P&L |
| No secrets or full account IDs in UI | ❓ UNKNOWN | Need to audit |

---

**Next Steps:** Begin implementation with Phase 1 (Trade Ledger Module)
