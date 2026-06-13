# Implementation Notes: AI Insights, News, Signals, Calendar

**Generated**: 2026-01-13T01:47:25Z  
**Target**: ALPHA VM (fxg-quant-paper-e2-micro, us-east1-b)  
**Status**: Inventory Complete, Calendar Fix Applied

---

## Summary

Completed capability inventory for AI Insights, Trade Signals, News Headlines, and Economic Calendar. Implemented fix for calendar synthetic fallback.

---

## Changes Applied

### 1. Calendar Synthetic Fallback Fix

**File**: `templates/dashboard_advanced.html`  
**Lines**: 3117-3120, 3205-3219  
**Change**: Removed synthetic event creation, replaced with explicit "not configured" message

**Before**:
- Created fake countdown events when no real events found
- Displayed "No major releases in next 24 hours" (misleading)

**After**:
- Sets `nextMajorEvent = null` explicitly (no synthetic events)
- Displays "⚠️ Economic Calendar Not Configured" message
- Shows explicit reason: "Calendar provider integration required"
- Includes note: "To enable: Configure calendar provider API keys in runtime config"

**Rationale**: Per workspace rules (No Placeholder Rule), no fake data. Calendar not implemented, so UI must show explicit "not configured" state.

---

## Capability Status

See `docs/CAPABILITY_INVENTORY_AI_NEWS_SIGNALS.md` for full inventory.

| Capability | Status | Action Taken |
|------------|--------|--------------|
| **Outlook** | ✅ Implemented (stub) | No action (works without keys) |
| **AI Insights** | ⚠️ Code exists, requires keys | Documented (needs `AI_INSIGHTS_ENABLED=1` + API key) |
| **Signals** | ✅ Implemented | No action (reads from status snapshot) |
| **News** | ✅ Implemented (already enabled) | No action (enabled in previous session per SYSTEM_STATUS_AND_PLAN_2026.md) |
| **Calendar** | ❌ Missing (backend) | Fixed UI synthetic fallback → "not configured" message |

---

## Verification Steps

### VM Endpoint Tests (When Service Running)

```bash
# Outlook
curl http://127.0.0.1:8080/api/v1/outlook/daily

# Signals
curl http://127.0.0.1:8080/api/signals/pending

# News Status
curl http://127.0.0.1:8080/api/news/status

# News Items
curl http://127.0.0.1:8080/api/news
```

### Dashboard Probe

```bash
python scripts/dashboard_probe.py --url https://alpha.fxgdesigns.co.uk
```

### UI Verification

1. **Outlook Tab**: Should show stub outlook data (no keys required)
2. **Signals**: Should show signals from status snapshot (if any)
3. **News Tab**: Should show news items (already enabled per previous session)
4. **Calendar Countdown** (dashboard_advanced.html only): Should show "not configured" message (no synthetic events)

---

## Next Steps (If Needed)

1. **AI Insights**: If API keys available, enable via `AI_INSIGHTS_ENABLED=1` + provider key
2. **Calendar**: Implement backend provider integration OR remove UI references entirely
3. **Verification**: Run dashboard probe when service is running to verify all endpoints

---

## Evidence

- **Inventory**: `docs/CAPABILITY_INVENTORY_AI_NEWS_SIGNALS.md`
- **VM Probe**: `artifacts/capability_inventory/20260113T014720Z/vm_endpoints_*.json` (service was down)
- **Repo Scan**: `artifacts/capability_inventory/20260113T014725Z/`
- **Code Changes**: `templates/dashboard_advanced.html` (calendar synthetic fallback fix)

---

**Next Owner**: Verification tasks → Cursor
