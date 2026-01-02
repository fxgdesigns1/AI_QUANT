# Developer Setup & AI Trading System

## Canonical Runner (Lock-in)

**Run (paper default):**

```bash
python -m runner_src.runner.main
```

**Safe one-iteration verification (paper):**

```bash
MAX_ITERATIONS=1 TRADING_MODE=paper python -m runner_src.runner.main
```

**Enable live (requires dual enable; otherwise falls back to paper):**

```bash
TRADING_MODE=live LIVE_TRADING=true LIVE_TRADING_CONFIRM=true python -m runner_src.runner.main
```

**Kill switch (blocks execution):**

```bash
KILL_SWITCH=true python -m runner_src.runner.main
```

## Environment Variables

### Execution Gate

- `TRADING_MODE` - `paper` (default) or `live`
- `LIVE_TRADING` - Must be `true` for live trading
- `LIVE_TRADING_CONFIRM` - Second confirmation, must be `true` for live trading
- `KILL_SWITCH` - Set to `true` to block all execution
- `RUN_ID` - Optional run identifier for logs (auto-generated if not set)
- `MAX_ITERATIONS` - Optional limit for testing (0 = infinite, default)

### Legacy Runners

- `ALLOW_LEGACY_RUNNERS` - Must be `true` to run `automated_trading_system.py` directly

### Dashboard Background Loops

- `ENABLE_DASHBOARD_BACKGROUND_LOOPS` - Must be `true` to enable dashboard background processing

## Safety Features

1. **Paper Mode by Default** - System runs in paper mode unless explicitly enabled for live trading
2. **Dual Enable Required** - Live trading requires BOTH `LIVE_TRADING=true` AND `LIVE_TRADING_CONFIRM=true`
3. **Kill Switch** - `KILL_SWITCH=true` blocks all execution immediately
4. **Structured Logging** - All execution decisions logged as JSON with run_id
5. **Legacy Runner Guard** - Old runners blocked by default to prevent accidental execution

## Architecture

- `runner_src/runner/main.py` - Canonical entrypoint
- `runner_src/core/execution_gate.py` - Centralized execution control (copied to google-cloud-trading-system/src/core/)
- `working_trading_system.py` - Main trading logic (imports from google-cloud-trading-system)
- `google-cloud-trading-system/` - Core trading system modules

## Rollback

If you need to revert these changes:

```bash
git reset --hard savepoint/pre-lockin
git clean -fd
```

**Warning:** This will discard all uncommitted changes and remove untracked files.
