# Dashboard Probe Report
**Run ID:** 20260113T011857Z
**Timestamp (UTC):** 2026-01-13T01:18:57.892126Z
**Base URL:** http://127.0.0.1:8787

---
## Summary
- Endpoints OK: **13**/**13** (100.0%)
- Tabs OK: **10**/**10** (100.0%)
- Console errors: **0**
- Page errors: **0**
- Network request failures: **1**

## Issues (Derived)
- **WARNING** `scanner:insufficient_history` — Structural scanner reports insufficient history
  - Likely candle history fetch/requirements mismatch.

## Endpoint Results
- ✅ `/api/status` — 200
- ✅ `/api/market/prices` — 200
- ✅ `/api/news/status` — 200
- ✅ `/api/news` — 200
- ✅ `/api/trades/active` — 200
- ✅ `/api/trades/pending` — 200
- ✅ `/api/signals/pending` — 200
- ✅ `/api/strategies/overview` — 200
- ✅ `/api/performance/summary` — 200
- ✅ `/api/v1/outlook/daily` — 200
- ✅ `/api/v1/scanner/structural` — 200
- ✅ `/api/v1/audit` — 200
- ✅ `/api/journal/trades` — 200

## Tab Results + Screenshots
- ✅ `terminal`
  - UI Errors: ['NEWS ITEMS\n\n9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_terminal.png`
- ✅ `outlook`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_outlook.png`
- ✅ `scanner`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_scanner.png`
- ✅ `mesh`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_mesh.png`
- ✅ `journal`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_journal.png`
- ✅ `audit`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_audit.png`
- ✅ `news`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_news.png`
- ✅ `reports`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_reports.png`
- ✅ `strategies`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_strategies.png`
- ✅ `trades`
  - UI Errors: ['News Items\n                                9', 'ERROR', 'ERROR', '⚠️ Price Integrity Blocked', '⚠️ Price Integrity Blocked']
  - Screenshot: `artifacts/dashboard_probe/20260113T011857Z/tab_trades.png`

## Evidence Artifacts
- Raw JSON: `artifacts/dashboard_probe/20260113T011857Z/dashboard_probe_results.json`

## Console + Network
- Console errors captured: 0
- Console warnings captured: 2
- Page errors captured: 0
- Request failures captured: 1
