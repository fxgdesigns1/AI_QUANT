# Monday Unlock Sequence (Paper-Safe)

**Date:** 2026-01-05  
**Status:** Paper mode by default, execution disabled

---

## Overview

This document describes the safe, explicit path to enable **paper execution** (practice account) without enabling live trading. Live trading remains blocked by design.

---

## Current State (Default)

- `EXECUTION_UNLOCK_OK` = not set (or `false`)
- `OANDA_ACCOUNT_ID` = not required (system runs in signals-only mode)
- `execution_enabled` = `false` (from `/api/status`)
- System scans markets and generates signals but does NOT execute trades

---

## Step 1: Enable Paper Execution (Practice Account)

### Prerequisites

1. **OANDA Practice Account**: You must have a valid OANDA practice account ID
2. **OANDA API Key**: Valid practice API key (starts with `...` for practice accounts)
3. **Environment**: `OANDA_ENVIRONMENT=practice` (default)

### Required Environment Variables

```bash
# Unlock execution (paper mode only)
export EXECUTION_UNLOCK_OK=true

# OANDA Practice Account (required when EXECUTION_UNLOCK_OK=true)
export OANDA_ACCOUNT_ID="your-practice-account-id"
export OANDA_API_KEY="your-practice-api-key"

# Confirm paper mode
export OANDA_ENVIRONMENT=practice
export TRADING_MODE=paper

# Enable paper execution
export PAPER_EXECUTION_ENABLED=true
```

### Validation

The system will:
- ✅ **Fail closed** if `EXECUTION_UNLOCK_OK=true` but `OANDA_ACCOUNT_ID` is missing
- ✅ **Allow** paper execution when all prerequisites are met
- ✅ **Block** live trading (requires additional gates)

---

## Step 2: Verify Paper Execution

### Check Status

```bash
curl http://127.0.0.1:8787/api/status | jq
```

Expected response:
```json
{
  "mode": "paper",
  "execution_enabled": true,
  "accounts_loaded": 1,
  "accounts_execution_capable": 1,
  ...
}
```

### Verify Execution Gate

The `ExecutionGate` class enforces:
- `TRADING_MODE=paper` → allows paper execution if `PAPER_EXECUTION_ENABLED=true`
- `TRADING_MODE=live` → requires `LIVE_TRADING=true` AND `LIVE_TRADING_CONFIRM=true` (dual-confirm)

---

## Step 3: Live Trading (Blocked by Design)

**Live trading is NOT enabled by this sequence.**

To enable live trading, you must:
1. Set `TRADING_MODE=live`
2. Set `LIVE_TRADING=true`
3. Set `LIVE_TRADING_CONFIRM=true` (dual-confirm gate)
4. Ensure `OANDA_ENVIRONMENT` is NOT `practice`

**This sequence does NOT enable live trading.**

---

## Safety Gates

### Gate 1: EXECUTION_UNLOCK_OK

- **Default**: `false` or unset → execution disabled
- **When `true`**: Requires `OANDA_ACCOUNT_ID` or system fails closed

### Gate 2: Account Manager

- **When `EXECUTION_UNLOCK_OK=false`**: Missing `OANDA_ACCOUNT_ID` is OK (signals-only)
- **When `EXECUTION_UNLOCK_OK=true`**: Missing `OANDA_ACCOUNT_ID` → `RuntimeError`

### Gate 3: Execution Gate

- **Paper mode**: Requires `PAPER_EXECUTION_ENABLED=true`
- **Live mode**: Requires `LIVE_TRADING=true` AND `LIVE_TRADING_CONFIRM=true`

### Gate 4: Kill Switch

- `KILL_SWITCH=true` → blocks ALL execution (paper and live)

---

## Troubleshooting

### Error: "EXECUTION_UNLOCK_OK=true requires OANDA_ACCOUNT_ID"

**Solution**: Set `OANDA_ACCOUNT_ID` or set `EXECUTION_UNLOCK_OK=false` for signals-only mode.

### Error: "Execution blocked by gate"

**Solution**: Check:
- `PAPER_EXECUTION_ENABLED=true` for paper mode
- `LIVE_TRADING=true` AND `LIVE_TRADING_CONFIRM=true` for live mode
- `KILL_SWITCH` is not set to `true`

### Status shows `execution_enabled: false`

**Solution**: 
1. Verify `EXECUTION_UNLOCK_OK=true`
2. Verify `OANDA_ACCOUNT_ID` is set
3. Verify `PAPER_EXECUTION_ENABLED=true` (for paper mode)
4. Check runner logs for gate decisions

---

## Notes

- **No secrets in repo**: All API keys and account IDs must be set via environment variables
- **Paper mode default**: System defaults to paper mode even when execution is enabled
- **Live trading blocked**: This sequence does NOT enable live trading
- **Fail closed**: System fails closed (raises errors) when gates are not satisfied

---

## Verification

After unlocking, verify:
1. `/api/status` shows `execution_enabled: true`
2. Runner logs show "Execution enabled (paper_execution_enabled)"
3. No `RuntimeError` about missing `OANDA_ACCOUNT_ID`
4. Orders are simulated (paper mode) or executed (if live mode is explicitly enabled)
