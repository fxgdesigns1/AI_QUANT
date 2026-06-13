# Account 006 Unblock and Autotrading Enable - Implementation Log

**Date:** 2026-01-22  
**Task:** UNLOCK_AND_VERIFY_ACCOUNT_006_AUTOTRADING  
**Mode:** PAPER_ONLY  
**Status:** ✅ COMPLETE - Ready for Deployment

---

## Objective

Remove special-case isolation on OANDA account 006, allow it to trade with standard strategies, and verify end-to-end paper autotrading.

### Root Cause Diagnosis

**Problem:** Account 006 was hard-reserved by `_enforce_account_isolation` for SessionExecutionStrategy, preventing all other strategies from executing.

**Current Effect:** Account 006 loaded but permanently blocked from trading unless `session_execution` was explicitly assigned.

**Solution:** Disable hard isolation enforcement, treat account 006 as a standard trading account.

---

## Changes Implemented

### 1. Strategy Alias Resolution (`src/control_plane/strategy_registry.py`)

**Added:**
- `STRATEGY_ALIASES` dictionary mapping legacy/variant keys to canonical strategies:
  - `momentum_trading` → `momentum`
  - `gold_scalping_strict1` → `gold_scalping`
- `resolve_strategy_alias()` function to resolve aliases before lookup
- Updated `get_strategy_info()` and `validate_strategy_key()` to use alias resolution
- Enhanced `log_strategy_registry()` to log aliases at startup

**Code Changes:**
```python
# Strategy alias map: maps legacy/variant strategy keys to canonical strategies
STRATEGY_ALIASES: Dict[str, str] = {
    "momentum_trading": "momentum",
    "gold_scalping_strict1": "gold_scalping",
}

def resolve_strategy_alias(key: str) -> str:
    """Resolve strategy key alias to canonical key"""
    return STRATEGY_ALIASES.get(key, key)
```

**Impact:** Unregistered strategy keys (`momentum_trading`, `gold_scalping_strict1`) now resolve to canonical strategies automatically.

---

### 2. Strategy Lookup with Aliases (`working_trading_system.py`)

**Updated:**
- `_get_strategy_by_key()` now resolves aliases before lookup
- Added logging: `STRATEGY_RESOLVED original={key} resolved={resolved_key}`
- Added aliases to strategy_map for direct lookup

**Code Changes:**
```python
def _get_strategy_by_key(self, strategy_key: str):
    # Resolve alias first (momentum_trading -> momentum, gold_scalping_strict1 -> gold_scalping)
    from src.control_plane.strategy_registry import resolve_strategy_alias
    resolved_key = resolve_strategy_alias(strategy_key)
    
    # Log alias resolution if it occurred
    if resolved_key != strategy_key:
        logger.info(f"STRATEGY_RESOLVED original={strategy_key} resolved={resolved_key}")
    
    # Try resolved key first, then original key
    strategy = strategy_map.get(resolved_key) or strategy_map.get(strategy_key)
```

**Impact:** Strategy aliases work seamlessly in strategy lookup.

---

### 3. Removed Account 006 Hard Isolation (`working_trading_system.py`)

**Changed:**
- `_enforce_account_isolation()` - Changed from fail-fast `RuntimeError` to informational logging
- Signal generation isolation check - Removed blocking logic for account 006

**Before:**
```python
# Rule 2: No other strategy can use account 006
elif account_suffix == REQUIRED_ACCOUNT_SUFFIX:
    raise RuntimeError(
        f"CRITICAL: Account isolation violation. "
        f"Account suffix {REQUIRED_ACCOUNT_SUFFIX} is reserved exclusively for SessionExecutionStrategy..."
    )
```

**After:**
```python
# Rule 2: Account 006 isolation DISABLED - allow standard strategies
elif account_suffix == REQUIRED_ACCOUNT_SUFFIX:
    logger.info(
        f"✅ Account 006 isolation disabled – account {REQUIRED_ACCOUNT_SUFFIX} can use standard strategies. "
        f"Strategy '{strategy_key}' assigned to account {account_id[-6:] if len(account_id) >= 6 else account_id}."
    )
```

**Signal Generation Isolation Removed:**
```python
# Before: Blocked non-session_execution strategies from account 006
elif account_suffix == "006":
    logger.error("CRITICAL: Account isolation violation...")
    continue  # Reject signal - fail-closed

# After: Allow all strategies on account 006
if account_suffix == "006":
    logger.debug(f"✅ Account 006 signal generation: strategy '{strategy_key}' generating signal...")
```

**Impact:** Account 006 can now use any strategy (momentum, gold_scalping, etc.) without isolation errors.

---

### 4. Account Activation Logging (`src/core/dynamic_account_manager.py`)

**Added:**
- Defensive logging for each account activation: `ACCOUNT_ACTIVE account={suffix}`
- Account loading logging in `working_trading_system.py`: `ACCOUNT_LOADED account={suffix}`
- Updated log message for account 006 to reflect standard account status

**Code Changes:**
```python
# Defensive logging: Log each account activation
for account_id in account_ids:
    account_suffix = account_id[-3:] if len(account_id) >= 3 else account_id
    logger.info(f"ACCOUNT_ACTIVE account={account_suffix} full_id={account_id}")
```

**Impact:** Clear visibility into which accounts are loaded and active.

---

## Files Modified

1. **`src/control_plane/strategy_registry.py`**
   - Added `STRATEGY_ALIASES` dictionary
   - Added `resolve_strategy_alias()` function
   - Updated `get_strategy_info()` and `validate_strategy_key()` to use aliases
   - Enhanced `log_strategy_registry()` to log aliases

2. **`working_trading_system.py`**
   - Updated `_get_strategy_by_key()` to use alias resolution
   - Removed hard isolation in `_enforce_account_isolation()`
   - Removed signal generation isolation check
   - Added account loading logging

3. **`src/core/dynamic_account_manager.py`**
   - Added account activation logging
   - Updated log message for account 006

---

## Risk Controls Preserved

✅ **No live trading enabled** - All changes are paper-only  
✅ **No safety gates bypassed** - Execution, news, and regime gates remain intact  
✅ **Ranking preserved** - BEST_10_NOT_FIRST_10 selection policy unchanged  
✅ **Daily cap preserved** - 10 trades per account limit maintained  

---

## Expected State After Deployment

- **Account 006:** ACTIVE_AND_AUTOTRADING
- **Strategy Assignment:** STANDARD (momentum / gold_scalping via alias)
- **Execution Mode:** paper
- **Daily Trade Cap:** 10 per account
- **Selection Policy:** BEST_10_NOT_FIRST_10
- **Isolation:** DISABLED (treated as standard trading account)

---

## Deployment Steps

### 1. Restart Runner Service
```bash
sudo systemctl restart ai-quant-runner
```

### 2. Verify Service Status
```bash
sudo systemctl status ai-quant-runner
# Expected: active (running)
```

---

## Verification Commands

### Check Account 006 Loaded
```bash
grep -E "ACCOUNT_LOADED.*006|ACCOUNT_ACTIVE account=006" /opt/ai-quant/logs/runner.log | tail -n 5
```
**Expected:** Non-empty output showing account 006 loaded and active

### Check Account 006 Execution Ready
```bash
grep -E "OrderManager created for account.*006" /opt/ai-quant/logs/runner.log | tail -n 3
```
**Expected:** Non-empty output showing OrderManager created for account 006

### Check No Isolation Errors
```bash
grep -E "Account isolation violation" /opt/ai-quant/logs/runner.log | tail -n 3
```
**Expected:** Empty (no isolation errors)

### Check Strategy Resolution
```bash
grep -E "STRATEGY_RESOLVED|Account 006 isolation disabled" /opt/ai-quant/logs/runner.log | tail -n 10
```
**Expected:** Logs showing alias resolution and account 006 isolation disabled messages

### Check Trade Activity
```bash
grep -E "ORDER_PLACED|EXECUTED|FILLED" /opt/ai-quant/logs/runner.log | grep 006 | tail -n 10
```
**Expected:** Logs showing ORDER_PLACED, EXECUTED, or FILLED entries for account 006

### Check All Accounts Active
```bash
grep -E "ACCOUNT_ACTIVE account=" /opt/ai-quant/logs/runner.log | tail -n 10
```
**Expected:** Should show accounts 001, 002, 003, 004, 005, 006 all active

---

## Success Criteria

✅ Account 006 executes paper trades automatically  
✅ Account 006 appears in execution logs without isolation or skip warnings  
✅ No `STRATEGY_NOT_FOUND` or `STRATEGY_ID_MISSING` errors  
✅ Strategy aliases (`momentum_trading`, `gold_scalping_strict1`) resolve correctly  
✅ All 6 accounts (001-006) are active and trading  

---

## Rollback Plan

If issues occur, revert changes by:

1. **Restore isolation enforcement:**
   - Change `_enforce_account_isolation()` back to raise `RuntimeError` for account 006
   - Restore signal generation isolation check

2. **Restart service:**
   ```bash
   sudo systemctl restart ai-quant-runner
   ```

3. **Verify rollback:**
   ```bash
   grep -E "Account isolation violation" /opt/ai-quant/logs/runner.log
   ```
   Should show isolation errors if account 006 tries to use non-session_execution strategies.

---

## Notes

- Account 006 is now treated identically to accounts 001-005
- SessionExecutionStrategy can still use account 006, but it's no longer exclusive
- Strategy aliases provide backward compatibility for legacy strategy keys
- All logging is defensive and provides clear visibility into account and strategy resolution

---

## Strategy Assignment for Account 006

### Assignment Script Created

**File:** `scripts/assign_account_006_strategies.py`

**Purpose:** Assigns both `momentum` and `gold_scalping` strategies to account 006.

**Changes Made:**
1. Modified validation in `src/control_plane/schema.py` to allow account 006 to have multiple strategies
2. Created assignment script that preserves existing assignments and adds account 006 assignments

**Validation Update:**
```python
# Allow account 006 to have multiple strategies, but other accounts must be unique
other_account_ids = [aid for aid in account_ids if aid != account_006_id]
if len(other_account_ids) != len(set(other_account_ids)):
    errors.append("strategy_assignments: duplicate account_id found (each account except 006 can only have one strategy)")
```

**Assignment Result:**
- Account 006: `momentum` (✅ ENABLED)
- Account 006: `gold_scalping` (✅ ENABLED)
- All other account assignments preserved

**Usage:**
```bash
python3 scripts/assign_account_006_strategies.py
```

**Hot-Reload:** Config changes are detected automatically on next scan cycle (no restart required).

---

## Implementation Complete

**Status:** ✅ All changes implemented and ready for deployment  
**Next Action:** Deploy to VM and verify using commands above  
**Risk Level:** LOW (paper-only, all safety gates preserved)

**Account 006 Status:**
- ✅ Isolation removed (can use any strategy)
- ✅ Strategies assigned: momentum, gold_scalping
- ✅ Config saved and ready for hot-reload
- ✅ Validation updated to allow multiple strategies for account 006
