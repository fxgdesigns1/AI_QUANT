# Runner and Accounts Architecture

**Purpose:** Document how account loading, price polling, and signal scanning work in the AI_QUANT system.

---

## Component Ownership

### 1. Account Loading

**Owner:** `src/core/dynamic_account_manager.py` → `SimpleAccountManager`

**How it works:**
- Reads `OANDA_ACCOUNT_ID` from environment
- Creates `SimpleAccount` objects for each account ID
- Validates account IDs are not placeholders
- Provides account list to runner via `get_account_manager()`

**Entrypoint:** Called during `WorkingTradingSystem.__init__()`

**Status:** Accounts are loaded at runner startup. The runner writes account count to status snapshot as `accounts_total` and `accounts_loaded` (both set to the number of successfully loaded accounts).

### 2. Price Polling/Cache

**Owner:** `working_trading_system.py` → `WorkingTradingSystem.scan_and_execute()`

**How it works:**
- Runner calls `client.get_current_prices(instruments)` for each account during scan
- Prices are fetched from OANDA API via `src/control_plane/market_data_provider.py`
- Latest prices are stored in status snapshot as `live_prices` map
- Control plane reads from snapshot via `/api/sidebar/live-prices`

**Polling interval:** Controlled by `scan_interval_seconds` (default 30s, configurable via dashboard)

**Status snapshot field:** `live_prices: {INSTRUMENT: {bid, ask, mid, time}}`

### 3. Signals Scan Loop

**Owner:** `working_trading_system.py` → `WorkingTradingSystem.run_forever()`

**How it works:**
- Runner runs in infinite loop (or until `MAX_ITERATIONS` reached)
- Each iteration:
  1. Checks for config changes (hot-reload)
  2. Calls `scan_and_execute()` which:
     - Gets market data for all instruments
     - Runs active strategy on each account
     - Generates trading signals
     - Executes trades (if `PAPER_EXECUTION_ENABLED=true` and execution gates pass)
  3. Writes status snapshot with latest state
  4. Sleeps for `scan_interval_seconds`

**Entrypoint:** `python -m runner_src.runner.main` (canonical)

**Status:** Runner writes to `runtime/status.json` atomically after each scan.

---

## Inter-Process Communication

### Status Snapshot (File-Based IPC)

**Path:** `runtime/status.json` (0600 permissions)

**Writer:** Runner (`working_trading_system.py`)

**Reader:** Control Plane API (`src/control_plane/api.py`)

**Format:**
```json
{
  "timestamp_utc": 1234567890.123,
  "timestamp_iso": "2026-01-06T12:34:56.123Z",
  "mode": "paper",
  "execution_enabled": false,
  "accounts_total": 1,
  "accounts_loaded": 1,
  "accounts_execution_capable": 0,
  "live_prices": {
    "EUR_USD": {"bid": 1.0850, "ask": 1.0852, "mid": 1.0851, "time": 1234567890.123},
    "GBP_USD": {"bid": 1.2650, "ask": 1.2652, "mid": 1.2651, "time": 1234567890.123}
  },
  "active_strategy_key": "momentum",
  "last_scan_iso": "2026-01-06T12:34:56.123Z",
  "last_signals_generated": 0,
  "last_executed_count": 0
}
```

**Atomic writes:** Uses temp file + atomic rename to prevent corruption.

**Freshness:** Control plane only reads snapshots < 120 seconds old (configurable via `max_age_seconds`).

---

## Starting the Runner

### Canonical Entrypoint

```bash
python -m runner_src.runner.main
```

**Environment:**
- Loads `.env` file automatically (via `python-dotenv`)
- Requires `OANDA_API_KEY`, `OANDA_ACCOUNT_ID` for account loading
- Optional: `PAPER_EXECUTION_ENABLED=true` to enable paper execution
- Optional: `MAX_ITERATIONS=N` to run N scans then exit (for testing)

### Start Script

```bash
bash scripts/start_runner_clean.sh
```

**Features:**
- Loads `.env` safely (presence/length only)
- Validates OANDA credentials
- Starts runner in foreground (or background with `RUNNER_BG=1`)
- Single-instance lock (prevents multiple runners)

---

## Account Validation

**OANDA Account ID Format:**
- Practice: `101-004-XXXXXXXXX-XXX`
- Live: `001-004-XXXXXXXXX-XXX`

**Validation:**
- Must not be placeholder (no `test-`, `demo-`, `placeholder-` prefixes)
- Must be > 3 characters
- Runner validates account exists by calling OANDA `/v3/accounts/{id}/summary`

**Error handling:**
- Invalid account ID → Runner fails to start with clear error
- Missing account ID → Runner runs in signals-only mode (no accounts loaded)

---

## Price Data Flow

1. **Runner scan loop** → `scan_and_execute()`
2. **Get market data** → `client.get_current_prices(instruments)`
3. **Store in snapshot** → `_write_status_snapshot()` includes `live_prices` map
4. **Control plane reads** → `/api/sidebar/live-prices` reads from snapshot
5. **Dashboard displays** → Frontend polls `/api/sidebar/live-prices` every 5-10s

**If runner not running:**
- Snapshot becomes stale (> 120s old)
- `/api/sidebar/live-prices` returns `success: true, prices: {}, warning: "runner_not_running"`

---

## Execution Gates

**Paper execution:**
- `TRADING_MODE=paper` (default)
- `PAPER_EXECUTION_ENABLED=true` (must be explicitly set)
- `OANDA_ACCOUNT_ID` must be valid (not placeholder)

**Live execution:**
- `TRADING_MODE=live`
- `LIVE_TRADING=true` (first gate)
- `LIVE_TRADING_CONFIRM=true` (second gate - dual confirmation)
- `KILL_SWITCH` must NOT be `true`

**Signals-only (default):**
- All execution gates fail → `execution_enabled=false`
- Runner still scans and generates signals
- Signals are NOT executed

---

## Troubleshooting

### Issue: `accounts_loaded` is 0

**Causes:**
1. `OANDA_ACCOUNT_ID` not set in `.env`
2. Runner not running
3. Account ID is invalid/placeholder

**Solution:**
```bash
# Check env vars
ENV_FILE=.env bash scripts/local_preflight.sh | grep OANDA

# Check runner is running
ps aux | grep "runner_src.runner.main"

# Check status snapshot
cat runtime/status.json | python3 -m json.tool
```

### Issue: `live_prices` is empty

**Causes:**
1. Runner not running
2. Runner hasn't completed first scan yet
3. OANDA API error (check runner logs)

**Solution:**
```bash
# Check runner logs
tail -f logs/ai_quant.log

# Check if runner is writing snapshots
ls -la runtime/status.json
cat runtime/status.json | python3 -c "import sys, json; d=json.load(sys.stdin); print('Prices:', len(d.get('live_prices', {})))"
```

### Issue: Runner won't start

**Causes:**
1. Another runner instance already running (lock file exists)
2. Invalid OANDA credentials
3. Missing dependencies

**Solution:**
```bash
# Check for lock file
ls -la /tmp/ai_quant_runner.lock

# Kill existing runner
pkill -f "runner_src.runner.main"

# Verify credentials
ENV_FILE=.env bash scripts/local_preflight.sh
```

---

**Last Updated:** 2026-01-06  
**Status:** ✅ Architecture Documented
