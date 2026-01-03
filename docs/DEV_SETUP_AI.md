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

## Paper Mode Configuration

### Paper Broker (No Network by Default)

- `PAPER_ALLOW_OANDA_NETWORK` - Set to `true` to allow OANDA network calls in paper mode (default: `false`)
- Paper mode uses `PaperBroker` by default, which provides synthetic data without network calls
- This enables uninterrupted strategy testing without requiring valid OANDA credentials or account IDs

## Verification Playbook

### T1: Live Mode Gate Verification

**Verify live mode cannot execute trades without dual-confirm:**

```bash
# Should show NO trade execution markers
MAX_ITERATIONS=1 TRADING_MODE=live LIVE_TRADING=true python -m runner_src.runner.main 2>&1 | \
  rg -n "place_market_order|Submitting|MARKET_ORDER|ORDER_CREATE|TRADE_OPEN|TRADE_CLOSE|Filled|EXECUTED [1-9]"
# Expected: ✅ No trade execution markers found

# Check for gate messaging (JSON logs may contain execution_gate_decision events)
MAX_ITERATIONS=1 TRADING_MODE=live LIVE_TRADING=true python -m runner_src.runner.main 2>&1 | \
  rg -n "execution_gate_decision|paper_order_simulated|live_requested_but_not_dual_enabled"
# Expected: Should show execution_gate_decision with reason indicating paper fallback
```

**Note:** The execution gate logs JSON events. Look for `execution_gate_decision` events with `reason: "live_requested_but_not_dual_enabled"` when only `LIVE_TRADING=true` is set.

### T2: Paper Mode Network Verification

**Verify paper mode makes zero HTTP calls:**

```bash
MAX_ITERATIONS=1 TRADING_MODE=paper PAPER_ALLOW_OANDA_NETWORK=false python -m runner_src.runner.main 2>&1 | \
  rg -n "api-fxpractice|api\.oanda\.com|oanda_client|requests\."
# Expected: ✅ No OANDA URLs or requests calls found
```

**Expected behavior:** Paper mode with `PAPER_ALLOW_OANDA_NETWORK=false` uses `PaperBroker` which never makes network calls. All prices and account data are synthetic.

### T3: Secret Leakage Verification

**Verify no secret-like patterns in logs:**

```bash
# Manually inspect logs for any secret-like patterns (key values, tokens, etc.)
MAX_ITERATIONS=1 TRADING_MODE=paper PAPER_ALLOW_OANDA_NETWORK=false python -m runner_src.runner.main 2>&1 | \
  tee /tmp/paper_run.log
# Then manually review /tmp/paper_run.log for any secret-like content
# Expected: ✅ No secret-like patterns found
# Note: Logs may mention "API keys" in context of service names (e.g., 'marketaux', 'fmp', 'polygon'),
#       but should never print actual key values or prefixes
```

**Note:** Logs may mention "API keys" in the context of service names (e.g., "Loaded 3 real API keys: ['marketaux', 'fmp', 'polygon']"), but should never print actual key values or prefixes.

### T4: PaperBroker Verification

**Verify PaperBroker is used and OANDA client is NOT initialized:**

```bash
MAX_ITERATIONS=1 TRADING_MODE=paper PAPER_ALLOW_OANDA_NETWORK=false python -m runner_src.runner.main 2>&1 | \
  rg -n "PAPER BROKER|OANDA client initialized"
# Expected: Should show "PAPER BROKER" lines, should NOT show "OANDA client initialized"
```

**Expected output:**
```
📄 Using PAPER BROKER for all accounts (no network calls)
📄 PAPER BROKER initialized for account 001
```

### T5: Uninterrupted Multi-Iteration Scanning

**Verify paper mode can run multiple iterations without crashing:**

```bash
MAX_ITERATIONS=5 TRADING_MODE=paper PAPER_ALLOW_OANDA_NETWORK=false python -m runner_src.runner.main 2>&1 | \
  rg -n "SCANNING FOR OPPORTUNITIES|Total signals generated|Reached max iterations|api-fxpractice|requests\."
# Expected: Should show 5 "SCANNING FOR OPPORTUNITIES" lines, 5 "Total signals generated" lines, 
#           one "Reached max iterations (5)" line, and NO network markers
```

**Expected output:**
```
🔍 SCANNING FOR OPPORTUNITIES...
📊 Total signals generated: 0
[... repeats 5 times ...]
🛑 Reached max iterations (5), stopping.
```

### T6: Dual-Confirm Live Mode Verification

**Verify live mode requires both confirms:**

```bash
# Without both confirms - should NOT execute
MAX_ITERATIONS=1 TRADING_MODE=live LIVE_TRADING=true python -m runner_src.runner.main 2>&1 | \
  rg -n "live_order_executed|EXECUTED [1-9]"
# Expected: ✅ No matches (no trades executed)

# With both confirms - should execute (if broker available)
MAX_ITERATIONS=1 TRADING_MODE=live LIVE_TRADING=true LIVE_TRADING_CONFIRM=true python -m runner_src.runner.main 2>&1 | \
  rg -n "execution_gate_decision"
# Expected: Should show execution_gate_decision with reason: "live_dual_enabled"
```

## Rollback

If you need to revert these changes:

```bash
git reset --hard savepoint/pre-lockin
git clean -fd
```

**Warning:** This will discard all uncommitted changes and remove untracked files.
