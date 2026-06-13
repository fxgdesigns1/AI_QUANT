# Dashboard Functionality Restoration

**Objective:** Full forensic dashboard usability with truth-only enforcement.

## Interactive Controls Inventory

- `nav-terminal` → `showTab('terminal')` → GET `/api/signals/pending`, `/api/positions`
- `nav-mesh` → `showTab('mesh')` → GET `/api/truth/status`
- `nav-journal` → `showTab('journal')` → GET `/api/journal/trades`
- `nav-news` → `showTab('news')` → GET `/api/news`
- `nav-reports` → `showTab('reports')` → GET `/api/performance/summary`
- `nav-strategies` → `showTab('strategies')` → GET `/api/strategies`
- `strategy-gold` / `strategy-mean` / `strategy-breakout` → `switchStrategy()` → **UI only**, no backend mutation
- `chart-symbol` → `changeChartSymbol()` → **visual only**, no backend calls
- `btn-manual-override` → guarded destructive stub → `/api/truth/status` only
- `btn-export-csv` → guarded read-only → GET `/api/journal/trades/export`
- `btn-filter-trades` → guarded read-only stub → `/api/truth/status` only
- `btn-settings` → guarded read-only → localStorage token only
- `settings-save` / `settings-clear` / `settings-close` → localStorage + modal controls only
- `btn-reload-cloud-sync` → guarded destructive stub → `/api/truth/status` only
- `btn-deploy-nodes` → guarded destructive stub → `/api/truth/status` only
- `toggleTradeDetails('trade1|trade2|trade3')` → expand/collapse UI only

## Guarding Rules

- Destructive actions show intent confirm, check `/api/truth/status`, and **always refuse** to mutate state from UI.
- Read-only actions show intent confirm and require `TRUTH_LEVEL=FULL` before proceeding.
- All data rendering uses `{data, truth}` envelopes and blocks when `truth.complete !== true`.

## CSV Export (Server-Generated)

- Endpoint: `GET /api/journal/trades/export`
- Output: `{data: {filename, csv, count}, truth: {...}}`
- UI downloads CSV only when truth is FULL.

## Playwright Forensic Test

- Spec: `src/verification/playwright_dashboard_forensic.spec.ts`
- Run: `DASHBOARD_URL=http://127.0.0.1:8787 npx playwright test src/verification/playwright_dashboard_forensic.spec.ts`
- Assertions: no console errors, no 5xx responses, all controls clickable.
