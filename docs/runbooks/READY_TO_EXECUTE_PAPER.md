# Paper Execution Readiness Checklist

**Purpose:** Verify the system is ready for paper trading execution without placing any orders.

**Safety:** This checklist only verifies configuration. It does NOT enable execution or place orders.

---

## Execution Gates (Authoritative)

The system uses the following environment variables to determine execution capability:

### Paper Mode Execution

**Required variables:**
- `TRADING_MODE=paper` (default, safe)
- `PAPER_EXECUTION_ENABLED=true` (must be explicitly set to enable paper execution)
- `OANDA_API_KEY=<your-key>` (required for account loading)
- `OANDA_ACCOUNT_ID=<your-account-id>` (required for account loading)

**How it works:**
- If `TRADING_MODE=paper` and `PAPER_EXECUTION_ENABLED=true`, execution is enabled in paper mode
- If `PAPER_EXECUTION_ENABLED` is unset or `false`, system runs in signals-only mode (safe default)
- The runner must load accounts from OANDA for `accounts_loaded > 0`

### Live Mode Execution (NOT COVERED IN THIS CHECKLIST)

**Required variables (for reference only - do not enable without explicit approval):**
- `TRADING_MODE=live`
- `LIVE_TRADING=true` (first gate)
- `LIVE_TRADING_CONFIRM=true` (second gate - dual confirmation required)
- `KILL_SWITCH` must NOT be set to `true` (blocks all execution)

**Note:** Live trading requires explicit dual confirmation and is outside the scope of this paper readiness checklist.

### Additional Execution Gates

- `EXECUTION_UNLOCK_OK=true` - Some components check this (legacy compatibility)
- `KILL_SWITCH=true` - Hard blocks ALL execution (paper and live)

---

## Verification Checklist

### Step 1: Environment Configuration

```bash
# Verify .env format
python3 scripts/env_sanity_check.py --env .env

# Verify environment variables are loaded (presence/length only)
ENV_FILE=.env bash scripts/local_preflight.sh
```

**Expected:** All required keys show "loaded: True" with length > 0

### Step 2: Control Plane Health

```bash
# Check if control plane is running
curl -s http://127.0.0.1:8787/health | python3 -m json.tool

# Get status
curl -s http://127.0.0.1:8787/api/status | python3 -m json.tool
```

**Expected:**
- `/health` returns `{"status": "ok"}`
- `/api/status` returns JSON with `mode`, `execution_enabled`, `accounts_loaded`

### Step 3: Paper Readiness Verification

```bash
# Run automated verification script
bash scripts/verify_paper_readiness.sh
```

**Expected output:**
```
✅ PASS: Paper execution is ready

System is configured for paper trading:
   - Mode: paper
   - Execution: enabled
   - Accounts: N loaded, M execution-capable
```

**If FAIL:**
The script will list exactly what's missing:
- `mode is 'X' (expected 'paper')`
- `execution_enabled is false (expected true)`
- `accounts_loaded is 0 (expected > 0)`

### Step 4: Manual Verification (Optional)

```bash
# Parse status manually
STATUS=$(curl -s http://127.0.0.1:8787/api/status)

# Check mode
echo "$STATUS" | python3 -c "import sys, json; print('Mode:', json.load(sys.stdin)['mode'])"

# Check execution_enabled
echo "$STATUS" | python3 -c "import sys, json; print('Execution:', json.load(sys.stdin)['execution_enabled'])"

# Check accounts_loaded
echo "$STATUS" | python3 -c "import sys, json; print('Accounts:', json.load(sys.stdin)['accounts_loaded'])"
```

---

## Common Issues and Solutions

### Issue: `execution_enabled` is `false`

**Causes:**
1. `PAPER_EXECUTION_ENABLED` is not set to `true` in `.env`
2. `TRADING_MODE` is set to something other than `paper`
3. Runner has not loaded accounts yet

**Solution:**
```bash
# Edit .env and ensure:
TRADING_MODE=paper
PAPER_EXECUTION_ENABLED=true

# Restart control plane and runner
bash scripts/stop_control_plane.sh
ENV_FILE=.env bash scripts/start_control_plane_clean.sh
```

### Issue: `accounts_loaded` is `0`

**Causes:**
1. OANDA credentials missing or invalid
2. Runner not running or not connected to control plane
3. Account loading failed

**Solution:**
```bash
# Verify OANDA credentials are present (length only, never values)
ENV_FILE=.env bash scripts/local_preflight.sh | grep OANDA

# Check runner logs for account loading errors
tail -f logs/ai_quant.log | grep -i account

# Verify OANDA credentials are valid (test connection)
# (Use OANDA API directly to verify, not through this system)
```

### Issue: Control plane not running

**Solution:**
```bash
# Start control plane
ENV_FILE=.env bash scripts/start_control_plane_clean.sh

# Or in background
ENV_FILE=.env CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh
```

---

## Security Notes

**⚠️ CRITICAL:**
- Never print actual API keys or tokens in logs or terminal output
- Only print presence/length: `✓ OANDA_API_KEY: present (length=65)`
- All secrets must be in `.env` (gitignored, never committed)
- If a key was ever pasted into chat/logs, rotate it immediately

**Zsh History Expansion:**
If you see errors like `zsh: event not found` when using `!` in commands:
- Run `set +H` to disable history expansion temporarily
- Or quote/escape the `!` character: `'!'` or `\!`
- This is a zsh feature that expands `!` as history references

---

## Complete Verification Sequence

```bash
# 1. Environment check
python3 scripts/env_sanity_check.py --env .env
ENV_FILE=.env bash scripts/local_preflight.sh

# 2. Start control plane (if not running)
bash scripts/stop_control_plane.sh || true
ENV_FILE=.env CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh

# 3. Wait for startup
sleep 5

# 4. Verify paper readiness
bash scripts/verify_paper_readiness.sh
```

**Expected final output:**
```
✅ PASS: Paper execution is ready
```

---

## What This Checklist Does NOT Do

- ❌ Does NOT enable execution (you must set `PAPER_EXECUTION_ENABLED=true` in `.env`)
- ❌ Does NOT place any orders
- ❌ Does NOT verify live trading readiness
- ❌ Does NOT test actual order placement
- ❌ Does NOT verify account balances or positions

This checklist only verifies that the system is **configured** for paper execution. Actual execution requires:
1. Passing this checklist
2. Runner process running and connected
3. Market hours (FX markets open)
4. Valid trading signals generated

---

## Local Full Bringup

**One-command startup:** Start control plane + runner + verify everything:

```bash
ENV_FILE=.env bash scripts/bringup_local_full.sh
```

**What it does:**
1. Loads `.env` safely (presence/length only)
2. Stops any existing services
3. Starts control plane in background
4. Starts runner in background
5. Waits for accounts to load
6. Verifies control plane, live prices, Telegram (if configured)
7. Runs paper readiness check

**Expected output:**
```
✅ Full Local Bringup Complete

📋 Services:
   Control Plane: http://127.0.0.1:8787
   Runner: Running (PID: <pid>)

📊 Status:
   Mode: paper
   Execution: false (or true if PAPER_EXECUTION_ENABLED=true)
   Accounts: N
```

**Manual startup (if needed):**

```bash
# Start control plane
ENV_FILE=.env CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh

# Start runner (in another terminal or background)
ENV_FILE=.env RUNNER_BG=1 bash scripts/start_runner_clean.sh

# Verify
bash scripts/verify_paper_readiness.sh
```

---

**Last Updated:** 2026-01-06  
**Status:** ✅ Verified Working
