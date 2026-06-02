# Dashboard API Endpoints Expected

**Source**: `templates/dashboard_advanced.html`  
**Generated**: 2026-01-03  
**Purpose**: Document all `/api/*` endpoints the existing dashboard calls

## Core Endpoints

### Status & System
- `GET /api/status` - System status, accounts, execution state
- `GET /api/health` - Health check

### Accounts
- `GET /api/accounts` - Account list with balances, execution capability

### Strategies
- `GET /api/strategies` - Strategy list (control plane uses this)
- `GET /api/strategies/overview` - Detailed strategy overview (dashboard expects this)
- `POST /api/strategy/activate` - Activate strategy (control plane has this)

### Positions & Trades
- `GET /api/positions` - Open positions
- `GET /api/trades/pending` - Pending trade orders
- `GET /api/signals/pending` - Trading signals waiting execution

### Market Data & Context
- `GET /api/contextual/{instrument}` - Contextual data for instrument
- `GET /api/news` - News feed
- `GET /api/sidebar/live-prices` - Live price updates

### AI & Insights (Optional)
- `GET /api/insights` - AI insights
- `GET /api/trade_ideas` - AI trade ideas
- `GET /api/opportunities` - Trade opportunities
- `POST /api/opportunities/approve` - Approve opportunity
- `POST /api/opportunities/dismiss` - Dismiss opportunity

### Configuration
- `GET /api/config` - Runtime config (control plane has this)
- `POST /api/config` - Update config (control plane has this)

### Logs
- `GET /api/logs/stream` - SSE log stream (control plane has this)

## Truth Semantics

### Signals-Only Mode
When `PAPER_EXECUTION_ENABLED=false` (default):
- `/api/positions` returns `[]` with `execution_enabled: false`
- `/api/trades/pending` returns `[]` with reason
- `/api/signals/pending` returns signals but `execution_enabled: false`
- `/api/accounts` shows `execution_capable: 0`

### Live Mode (Gated)
Requires `LIVE_TRADING=true` + `LIVE_TRADING_CONFIRM=true`:
- All endpoints still return real data
- Execution-capable account count > 0 only if valid brokers

### Never Fabricate
- Empty arrays for missing data
- Explicit `reason` fields explaining why empty
- Timestamp fields for freshness verification
