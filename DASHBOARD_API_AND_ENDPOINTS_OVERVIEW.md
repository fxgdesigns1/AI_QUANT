## Dashboard API & Endpoints Overview

**Purpose**: Single reference file with all key API endpoints, data sources, and dependencies you need to rebuild the dashboard (e.g. in Claude) against the existing FastAPI control plane.

---

## 1. High‑Level Architecture

- **Control Plane API (`src/control_plane/api.py`)**
  - FastAPI app exposing all dashboard endpoints.
  - Reads from:
    - `runtime/status_snapshot.json` (runner status + signals + metrics).
    - `logs/*.jsonl` (audit logs, gate decisions, journal).
    - Config and strategy metadata in `src/core` and `src/control_plane`.
- **Runner (`working_trading_system.py`)**
  - Produces:
    - `runtime/status_snapshot.json`
    - `logs/session_regime_gate_audit.jsonl`
    - `logs/session_execution_strategy_audit.jsonl`
    - Trade / error logs, etc.
- **Dashboard Panels (`src/dashboard/panels/*.py`)**
  - Example: `session_regime_gate_panel` reads gate audit log and provides aggregate statistics and a “snapshot” view.
- **Truth Envelope**
  - Most JSON responses are wrapped in a standard “truth” envelope (`_truth_wrap` in `api.py`) with fields like:
    - `data`: payload.
    - `source`: where it came from (e.g. `status_snapshot`).
    - `complete`: whether data is complete.
    - `warnings`: list of strings.
    - `ts_utc`: ISO timestamp.

---

## 2. How to Run the Control Plane API

- **Primary entry**
  - See `src/control_plane/api.py` for the FastAPI app (`app = FastAPI(...)`).
  - Typically run via `uvicorn` (exact command may be in `scripts` or systemd unit files under `systemd/` or `scripts/systemd/`).
- **Auth**
  - Many endpoints require a bearer token via `Authorization: Bearer <CONTROL_PLANE_TOKEN>`.
  - Token is read from environment (`CONTROL_PLANE_TOKEN`).

For dashboard development in Claude, assume you are calling an already running FastAPI service and only need to know **URL paths**, **methods**, and **JSON shapes**.

---

## 3. Core Endpoint Groups (What the Dashboard Can Show)

Below is grouped by “dashboard panel / feature”. For each group:
- **Path / Method**
- **Description**
- **Key fields in response**
- **Internal dependency / data source**

### 3.1. Health & Version

- **`GET /`**
  - **Description**: Basic home / health check (often returns a tiny JSON or redirect).
  - **Deps**: None.

- **`GET /health`**
  - **Description**: Simple health endpoint (used by uptime checks).
  - **Deps**: May read nothing or a minimal status from the app.

- **`GET /api/ui/version`**
  - **Description**: Returns API / UI version info.
  - **Useful fields**: `version`, `build`, `ts_utc`.
  - **Deps**: Static constants in `api.py` or nearby module.

### 3.2. System Status (Top‑Level Dashboard Banner)

- **`GET /api/status`**
  - **Description**: Main status summary for the trading system.
  - **Key fields (inside `data`)**:
    - `runner_state` (e.g. `running`, `stopped`).
    - `last_heartbeat_ts`.
    - `accounts` with per‑account state.
    - `strategies` with per‑strategy state.
  - **Deps**:
    - `runtime/status_snapshot.json` via `get_status_snapshot()` in `src/control_plane/status_snapshot.py`.

- **`GET /api/truth/status`**
  - **Description**: Same as `/api/status` but explicitly truth‑wrapped with extra metadata.
  - **Key fields**:
    - `data`: status payload.
    - `complete`, `warnings`, `ts_utc`.
  - **Deps**:
    - Same as `/api/status`.

### 3.3. Market Overview & Prices

- **`GET /api/market/overview`**
  - **Description**: High‑level view of key instruments (e.g. EUR/USD, XAU/USD).
  - **Key fields** (per instrument):
    - `instrument`, `bid`, `ask`, `mid`, `spread`, `change_pct`, `session`, `regime` (if present).
  - **Deps**:
    - Market data provider (`src/control_plane/market_data_provider.py`).
    - Possibly `MarketRegimeDetector` (`src/core/market_regime.py`).

- **`GET /api/market/prices`**
  - **Description**: More detailed price snapshot for selected instruments.
  - **Key fields**:
    - `prices`: list of instruments with `bid`, `ask`, `spread`, and timestamps.
  - **Deps**:
    - Same as `market/overview`.

- **`GET /api/market/chart`**
  - **Description**: Candlestick data for charting.
  - **Query params**:
    - `instrument`, `granularity` (e.g. `M5`, `H1`, `D`), `count`.
  - **Key fields**:
    - `candles`: list of `{time, o, h, l, c, volume}`.
  - **Deps**:
    - Market data provider.

- **`GET /api/sidebar/live-prices`**
  - **Description**: Lightweight price snapshot for sidebar ticker.
  - **Key fields**:
    - `instruments`: small subset with `mid` / `change_pct`.
  - **Deps**:
    - Market data provider.

### 3.4. News, Embargo, and Macro Panel

- **`GET /api/news`**
  - **Description**: Latest news items.
  - **Key fields (per item)**:
    - `source`, `title`, `impact`, `category`, `symbol`, `ts_utc`.
  - **Deps**:
    - `src/control_plane/news_provider.py` or similar.

- **`GET /api/news/status`**
  - **Description**: News subsystem health + embargo status.
  - **Key fields**:
    - `status`: e.g. `normal`, `embargo`, `degraded`.
    - `is_embargo`: boolean.
    - `embargo_triggers`: list of high‑impact or central‑bank items (mirrors what we appended in `working_trading_system.py`).
  - **Deps**:
    - News provider.
    - `news_context_for_gate` in `working_trading_system.py`.

- **`POST /api/news/assess`**
  - **Description**: On‑demand evaluation of a given news item or set of items.
  - **Body**:
    - `items`: list of news dictionaries.
  - **Key fields (response)**:
    - `is_embargo`, `reasons`, `score`.
  - **Deps**:
    - News assessment logic (same criteria as gate).

- **`GET /api/economic_calendar`**
  - **Description**: Upcoming economic events (macro calendar).
  - **Key fields (per event)**:
    - `title`, `country`, `impact`, `time_utc`, `actual`, `forecast`, `previous`.
  - **Deps**:
    - Macro provider (`src/control_plane/macro_provider.py` if present).

### 3.5. Outlook / Roadmap Panel

- **`GET /api/v1/outlook/{horizon}`**
  - **Description**: Market outlook for a given horizon: `daily`, `weekly`, `monthly`.
  - **Path params**:
    - `horizon`: `"daily" | "weekly" | "monthly"`.
  - **Key fields**:
    - `outlooks`: list of `{instrument, bias, confidence, change_pct, notes}`.
  - **Deps**:
    - `OutlookEngine` in `src/control_plane/outlook_engine.py`.
    - Daily bias logic (reactive price move using short lookback).

- **`POST /api/v1/outlook/recompute`**
  - **Description**: Force recomputation of outlooks (admin).
  - **Body**:
    - Optional filters (instrument list, horizons).
  - **Key fields (response)**:
    - `status`, `recomputed_horizons`, `ts_utc`.
  - **Deps**:
    - Outlook engine recompute logic.

### 3.6. Strategies & Config Panels

- **`GET /api/config`**
  - **Description**: Effective runtime config (accounts, risk, assignments).
  - **Key fields**:
    - `accounts`: list of `{account_id, strategy_key, mode}`.
    - `risk_limits`: per‑account.
    - `feature_flags`.
  - **Deps**:
    - `ConfigStore` and `runtime/config.yaml`.

- **`GET /api/accounts`**
  - **Description**: Dashboard‑compat accounts list and execution capability.
  - **Key fields**:
    - `accounts`: array from `status_snapshot` (per‑account state).
    - `execution_capable`: count of accounts that can execute.
    - `mode`, `execution_enabled`.
  - **Deps**:
    - `status_snapshot.read()`.

- **`GET /api/strategies`**
  - **Description**: List of all registered strategies.
  - **Key fields (per strategy)**:
    - `key`, `name`, `description`, `default_instruments`, `risk_profile`, `session_preference`.
  - **Deps**:
    - `src/control_plane/strategy_registry.py` (`STRATEGIES` dict; includes `session_execution`).

- **`GET /api/strategies/overview`**
  - **Description**: High‑level strategy status for dashboard.
  - **Key fields**:
    - `strategies`: list with `key`, `active_accounts`, `instruments`, `mode`, `pending_signals`.
  - **Deps**:
    - Strategy registry.
    - Status snapshot (for runtime info).

- **`POST /api/strategy/activate`**
  - **Description**: Activate/deactivate a strategy for an account (admin control).
  - **Body**:
    - `account_id`, `strategy_key`, `enabled: bool`.
  - **Key fields (response)**:
    - `status`, `message`, updated assignment.
  - **Deps**:
    - Config store and validation against `strategy_registry`.

### 3.7. Trades, Positions, Signals, and Journal

- **`GET /api/trades/active`**
  - **Description**: Currently open trades.
  - **Key fields (per trade)**:
    - `id`, `account_id`, `instrument`, `side`, `size`, `entry_price`, `sl`, `tp`, `unrealized_pnl`, `opened_at`.
  - **Deps**:
    - Runner / broker adapter (`src/core/paper_broker.py` or live broker in future).

- **`GET /api/positions`**
  - **Description**: Net positions per instrument / account.
  - **Key fields**:
    - `positions`: list of `{account_id, instrument, net_units, avg_price, pnl}`.
  - **Deps**:
    - Broker / status snapshot.

- **`GET /api/signals/pending`**
  - **Description**: Pending trade signals not yet executed.
  - **Key fields**:
    - `signals`: list of `{strategy, instrument, side, size, sl, tp, reason, ts_utc}`.
  - **Deps**:
    - `TradeSignal` data from strategies (e.g. `SessionExecutionStrategy`).

- **`GET /api/trade_selection/preview`**
  - **Description**: Preview of current trade selection pool (what the system is “thinking” before execution).
  - **Query params**:
    - `limit` (optional): top‑N candidates, max 50.
  - **Key fields**:
    - `candidates`: list of trade‑selection candidates from `status_snapshot.trade_selection_pool`.
    - `count`, `limit`, `ts_utc`.
  - **Deps**:
    - `status_snapshot.read(max_age_seconds=120)`.

- **`GET /api/trades/pending`**
  - **Description**: Pending orders at broker.
  - **Key fields**:
    - Similar to `trades/active`, but not yet filled.
  - **Deps**:
    - Broker / status snapshot.

- **`GET /api/journal/trades`**
  - **Description**: Trade journal (historical).
  - **Query params**:
    - `limit`, `account_id`, `strategy_key`, date filters.
  - **Key fields (per entry)**:
    - `trade_id`, `account_id`, `strategy`, `instrument`, `side`, `entry`, `exit`, `pnl`, `tags`, `notes`.
  - **Deps**:
    - Journal storage (likely JSONL or DB).

- **`GET /api/journal/trades/export`**
  - **Description**: Export trade journal as CSV for download.
  - **Deps**:
    - Same as `journal/trades`.

### 3.8. Performance Panels

- **`GET /api/performance/summary`**
  - **Description**: High‑level PnL and risk metrics.
  - **Key fields**:
    - `equity_curve`, `max_drawdown`, `win_rate`, `sharpe`, `trade_count`.
  - **Deps**:
    - Performance module (aggregates journal + broker data).

- **`GET /api/performance/strategies`**
  - **Description**: Performance broken down by strategy.
  - **Key fields**:
    - For each strategy: `total_pnl`, `win_rate`, `drawdown`, `average_r`.

- **`GET /api/performance/accounts`**
  - **Description**: Performance by account.
  - **Key fields**:
    - For each account: `equity_start`, `equity_now`, `pnl`, `risk_used`.

- **`GET /api/performance/ai-evaluation`**
  - **Description**: AI evaluation / commentary on performance (if enabled).
  - **Key fields**:
    - `summary`, `warnings`, `opportunities`, `ts_utc`.
  - **Deps**:
    - AI insights subsystem (can be disabled / gated).

### 3.9. Session‑Regime Gate (Key for 006 & Telegram Alerts)

These map closely to `src/dashboard/panels/session_regime_gate_panel.py` and the gate audit log.

- **`GET /api/session-regime-gate/decisions`**
  - **Description**: Recent gate decisions (raw events).
  - **Key fields (per event)**:
    - `ts_utc`, `symbol`, `session`, `regime`, `roadmap_aligned`, `news_state`, `is_embargo`, `embargo_triggers`, `reason`, `allowed`, `daily_bias`, `weekly_bias`, `monthly_bias`.
  - **Deps**:
    - `logs/session_regime_gate_audit.jsonl` read via `load_recent_gate_events()` in `session_regime_gate_panel`.

- **`GET /api/session-regime-gate/statistics`**
  - **Description**: Aggregated gate statistics.
  - **Key fields** (returned by `get_gate_statistics()`):
    - `total_decisions`
    - `allowed_count`
    - `blocked_count`
    - `allow_rate`
    - `by_reason` (dict: reason → count)
    - `by_session` (dict: session → count)
    - `by_regime` (dict: regime → count)
  - **Deps**:
    - Same as above, uses last ~1000 events.

- **`GET /api/session-regime-gate/snapshot`**
  - **Description**: Current session/regime snapshot and last policy key.
  - **Key fields** (from `get_current_session_regime_snapshot()`):
    - `current_session` (derived from current UTC hour).
    - `current_time_utc`.
    - `last_known_regime`.
    - `last_policy_key` (format: `"session|regime|news_state|bias_alignment"`).
    - `has_recent_events`.
  - **Deps**:
    - Gate audit log (last event).

### 3.10. Audit Log & Observability

- **`GET /api/v1/audit`**
  - **Description**: Generic audit log viewer.
  - **Query params**:
    - `source` (e.g. `session_execution`, `gate`), `limit`, `strategy`, `symbol`.
  - **Key fields**:
    - Each entry is a JSON dict as written by `append_audit` in `src/core/audit_logger.py`.
  - **Deps**:
    - `logs/*_audit.jsonl` files.

---

## 4. Dependencies & Connectors (What the Dashboard Relies On)

- **Status Snapshot**
  - File: `runtime/status_snapshot.json`
  - Producer: `working_trading_system.py` (runner).
  - Consumer: `src/control_plane/status_snapshot.py` → multiple `/api/...` endpoints.

- **Gate Audit Log**
  - File: `logs/session_regime_gate_audit.jsonl`
  - Producer: `SessionRegimeAlignedStrategy` (`src/strategies/session_regime_aligned.py`).
  - Consumers:
    - `session_regime_gate_panel` (`load_recent_gate_events`, `get_gate_statistics`, `get_current_session_regime_snapshot`).
    - `/api/session-regime-gate/*` endpoints.

- **Session Execution Audit**
  - File: `logs/session_execution_strategy_audit.jsonl`
  - Producer: `SessionExecutionStrategy` (`src/strategies/session_execution_strategy.py`).
  - Consumers:
    - Generic audit endpoint (`/api/v1/audit`).
    - Any dashboard views showing 006 decisions.

- **Outlook Engine**
  - Module: `src/control_plane/outlook_engine.py`
  - Produces:
    - In‑memory outlooks for daily/weekly/monthly (roadmap).
  - Consumers:
    - `/api/v1/outlook/{horizon}`, `/api/v1/outlook/recompute`.
    - Session‑regime gate and `SessionExecutionStrategy` via roadmap alignment.

- **Market Data Provider**
  - Modules: `src/control_plane/market_data_provider.py`, `src/core/constants.py` (symbols).
  - Producer: external broker / price feed.
  - Consumers:
    - `/api/market/*` endpoints.

- **News & Macro Providers**
  - Modules: `src/control_plane/news_provider.py`, `src/control_plane/macro_provider.py` (names may vary but are imported in `api.py`).
  - Producers: external news / calendar APIs.
  - Consumers:
    - `/api/news*`, `/api/economic_calendar`, news embargo logic in runner and gate.

- **Strategy Registry**
  - File: `src/control_plane/strategy_registry.py`
  - Defines:
    - `STRATEGIES` dict with metadata; includes `session_execution`.
  - Consumers:
    - `/api/strategies`, `/api/strategies/overview`, `/api/strategy/activate`.
    - Config validation in `ConfigStore`.

---

## 5. Suggested Dashboard Panels & Which Endpoints to Use

This section is here so you can map panels directly in Claude.

- **System Header**
  - Use: `GET /api/truth/status`, `GET /api/ui/version`, `GET /health`.

- **Market Overview**
  - Use: `GET /api/market/overview`, `GET /api/sidebar/live-prices`, `GET /api/market/chart` (for charts).

- **News & Embargo**
  - Use: `GET /api/news`, `GET /api/news/status`, `GET /api/economic_calendar`.

- **Roadmap / Outlook**
  - Use: `GET /api/v1/outlook/daily`, `GET /api/v1/outlook/weekly`, `GET /api/v1/outlook/monthly`.

- **Session‑Regime Gate Panel**
  - Use: `GET /api/session-regime-gate/snapshot`, `GET /api/session-regime-gate/statistics`, `GET /api/session-regime-gate/decisions`.

- **Account 006 / Strategy View**
  - Use: `GET /api/strategies/overview` (filter for `session_execution`), `GET /api/trades/active`, `GET /api/positions`, `GET /api/signals/pending`, `GET /api/v1/audit` (source `session_execution`).

- **Performance**
  - Use: `GET /api/performance/summary`, `/api/performance/strategies`, `/api/performance/accounts`, `/api/performance/ai-evaluation`.

---

## 6. How to Use This File in Claude

- Paste this file or sections of it into Claude as **system / reference context**.
- Have Claude:
  - Build the React/Vue/Svelte/HTML dashboard layout.
  - Wire each panel to the specified endpoints and fields.
  - Respect truth envelopes (`data`, `complete`, `warnings`).
  - Render **empty states** when arrays are empty or `complete` is `False` (no fake data).

This file is designed to be the single source of truth for dashboard‑side integration against your existing control plane.

