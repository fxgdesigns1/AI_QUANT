# Strategy Discipline Upgrades - Implementation Complete

**Date:** January 23, 2026  
**Status:** ✅ STAGED AND READY FOR VERIFICATION  
**Execution Mode:** SAFE / PAPER ONLY

---

## Overview

Stage-safe changes for accounts 003, 002, and 006 with discipline upgrades and enhanced observability. All changes are **observable-only** (Stage 1) or **paper-trading safe** (Stages 2-4).

---

## Stage 1: Instrumentation + Observability ✅

**Goal:** Make all strategy decisions explainable before changing behavior

### Changes Applied

1. **DecisionReason Enum** (in `momentum_trading.py`):
   - `COOLDOWN_ACTIVE`, `LOW_VOLATILITY`, `OUTSIDE_SESSION`, `CONFIDENCE_LOW`
   - `SPREAD_TOO_HIGH`, `REGIME_MISMATCH`, `MISSING_DATA`, `INDICATORS_MISSING`
   - `RISK_TOO_HIGH`, `NO_SIGNAL`, `EARNED_PYRAMIDING_BLOCKED`, `ENTRY_CONFIRMATION_FAILED`

2. **Structured Logging** (`_log_decision` method):
   - Logs: `account_id`, `strategy`, `instrument`, `timestamp`, `decision`, `reason`, `metadata`
   - Format: `DECISION_SKIP` or `DECISION_FIRE` with JSON payload
   - Applied to all three strategies

3. **Files Modified:**
   - `src/strategies/momentum_trading.py`
   - `src/strategies/gold_scalping.py`
   - `src/strategies/session_execution_strategy.py`

### Verification Command
```bash
grep -E "DECISION_SKIP|DECISION_FIRE" logs/*.log | tail -50
```

**Expected:** Every non-trade decision has a reason logged with structured format.

---

## Stage 2: Account 003 (Momentum Trading) ✅

**Account:** 003  
**Strategy:** `MomentumTradingStrategy`

### Changes Implemented

1. **Per-Symbol Cooldown** ✅
   - Blocks new entries on same symbol for 45 minutes after entry
   - Implementation: `self.last_entry_time[instrument]` tracking
   - Reason logged: `COOLDOWN_ACTIVE`

2. **Volatility Gate** ✅
   - Requires ATR(14) > rolling ATR median (last 20 periods)
   - Implementation: Calculates TR series, then ATR series, compares current to median
   - Reason logged: `LOW_VOLATILITY`

3. **Entry Confirmation** ✅
   - Requires candle close beyond breakout level (EMA fast)
   - For BUY signals: `last_close > breakout_level`
   - Reason logged: `ENTRY_CONFIRMATION_FAILED`

4. **Earned Pyramiding** ⚠️
   - **Status:** Requires execution-level check
   - **Note:** Position state (unrealized PnL) not available in `analyze_market()`
   - **Action Required:** Implement in order manager / execution gate
   - **Rule:** Block additional entries if existing position unrealized PnL <= 0

### Explicit Non-Changes
- Stop loss logic (unchanged)
- Take profit logic (unchanged)
- Directional bias (unchanged)
- Risk caps (unchanged)

### Expected Impact
- Trades per symbol decreases
- Margin spikes reduced
- TP hit rate unchanged or improved

---

## Stage 3: Account 002 (Gold Scalping) ✅

**Account:** 002  
**Strategy:** `GoldScalpingStrategy`

### Changes Implemented

1. **Session Filter** ✅
   - Allows trades only during London (7-16 UTC) and NY (12-21 UTC) sessions
   - Combined window: 7-21 UTC
   - Implementation: `_is_trading_session()` method
   - Reason logged: `OUTSIDE_SESSION`

2. **Volatility/Spread Gate** ✅
   - ATR must exceed minimum (0.15% of price)
   - Spread must be < 20% of TP distance
   - Implementation: Dual check before signal generation
   - Reasons logged: `LOW_VOLATILITY`, `SPREAD_TOO_HIGH`

3. **Max Trades Per Session** ✅
   - Maximum 1 trade per session
   - Session state resets daily
   - Implementation: `self.session_trade_count` tracking
   - Reason logged: `RISK_TOO_HIGH` ("Max trades per session reached")

4. **Stop After First Loss** ⚠️
   - **Status:** Requires external position monitoring
   - **Note:** `self.last_trade_loss` flag exists but needs to be updated by external system
   - **Action Required:** Update flag when position closes at loss
   - **Rule:** Block trading after first loss in session

5. **Confidence Threshold** ✅
   - Raised minimum confidence from 0.40 to 0.55
   - Implementation: `self.confidence_threshold = max(self.confidence_threshold, 0.55)`
   - Reason logged: `CONFIDENCE_LOW`

### Expected Impact
- Trades per day reduced significantly
- Higher average trade quality
- Lower churn and commission drag

---

## Stage 4: Account 006 (Session Execution) ✅

**Account:** 006  
**Strategy:** `SessionExecutionStrategy`

### Changes Implemented

1. **Enhanced Logging** ✅
   - Session window evaluation with UTC timestamps
   - Readiness score and blocking reason every cycle
   - Explicit `TRADE_BLOCKED` reasons for all gates
   - `WOULD_EXECUTE=true` flag when signal would fire (dry run probe)

2. **Session Diagnostics** ✅
   - Logs: `SESSION_ACTIVE=true/false`, `SESSION_READY=true/false` with reason
   - All blocking reasons logged: `outside_session`, `news_embargo`, `roadmap_misaligned`, `regime_not_trending`, `direction_unclear`

3. **Dry Run Probe** ✅
   - If signal would fire, logs `WOULD_EXECUTE=true` without placing trade
   - Proves strategy logic is reachable

### Verification Expected Logs
- `SESSION_ACTIVE=true/false`
- `SESSION_READY=true/false with reason`
- `WOULD_EXECUTE=true` when conditions met

### Success Criteria
Account 006 inactivity is fully explainable or corrected.

---

## Safety Guards

✅ **Paper trading only** - No live execution  
✅ **No duplicate logic** - Single source of truth per strategy  
✅ **Fail-fast** - Missing env or account wiring will error clearly  
✅ **Observable** - All decisions logged with structured format

---

## Files Modified

1. `src/strategies/momentum_trading.py`
   - Added `DecisionReason` enum
   - Added `_log_decision()` method
   - Added cooldown tracking (`self.last_entry_time`)
   - Added volatility gate (ATR median check)
   - Added entry confirmation (candle close check)

2. `src/strategies/gold_scalping.py`
   - Added `DecisionReason` import
   - Added `_log_decision()` method
   - Added session filter (`_is_trading_session()`)
   - Added session state tracking (`session_trade_count`, `last_trade_loss`)
   - Added volatility/spread gate
   - Raised confidence threshold to 0.55

3. `src/strategies/session_execution_strategy.py`
   - Added `DecisionReason` import
   - Added `_log_decision()` method
   - Enhanced session logging with UTC timestamps
   - Added `WOULD_EXECUTE` flag to signal metadata
   - Fixed import syntax error

---

## Verification Steps

### 1. Check Logging Output
```bash
grep -E "DECISION_SKIP|DECISION_FIRE" logs/*.log | tail -50
```

### 2. Verify Account 003 Behavior
- Check for `COOLDOWN_ACTIVE` logs after trades
- Check for `LOW_VOLATILITY` logs when ATR is low
- Check for `ENTRY_CONFIRMATION_FAILED` when close <= breakout

### 3. Verify Account 002 Behavior
- Check for `OUTSIDE_SESSION` logs outside 7-21 UTC
- Check for `RISK_TOO_HIGH` logs after first trade
- Check for `CONFIDENCE_LOW` logs with confidence < 0.55

### 4. Verify Account 006 Behavior
- Check for `SESSION_ACTIVE` logs with UTC hour
- Check for `WOULD_EXECUTE=true` in signal metadata
- Check for explicit blocking reasons in logs

### 5. Run System
```bash
bash scripts/start_runner_clean.sh && tail -f logs/*.log
```

---

## Outstanding Items

1. **Earned Pyramiding (Account 003)**
   - Requires execution-level position check
   - Implement in `src/core/execution_gate.py` or `src/core/order_manager.py`
   - Check: `if existing_position.unrealized_pnl <= 0: block_entry()`

2. **Stop After First Loss (Account 002)**
   - Requires external position monitoring
   - Update `self.last_trade_loss = True` when position closes at loss
   - Implement in position monitoring / trade ledger

---

## Next Steps

1. ✅ **Code Complete** - All staged changes implemented
2. ⏳ **Verification** - Run system and check logs
3. ⏳ **Outstanding Items** - Implement earned pyramiding and loss tracking
4. ⏳ **Metrics** - Monitor trade count reduction and quality improvement

---

## Notes

- All changes are **backward compatible** - existing logic preserved
- All changes are **observable** - every decision is logged
- All changes are **safe** - paper trading only, no live execution
- No duplicate logic introduced - single source of truth maintained
