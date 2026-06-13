# ALPHA Account Behavior Probe Guide

**Date:** 2026-01-22  
**Phase:** ALPHA  
**Mode:** read_only_probe

## Overview

This probe analyzes account behavior using only log and transaction truth sources. No code changes, no config mutations, no execution overrides.

## Questions Addressed

1. **Why are accounts 001 and 003 statistically similar?**
2. **Why are accounts 004 and 006 not trading?**
3. **How can account 002 be optimized without increasing risk?**

## Usage

```bash
python3 scripts/alpha_account_behavior_probe.py
```

## Output Files

The probe generates the following reports:

1. **`logs/ALPHA_ACCOUNT_BEHAVIOR_PROBE.json`** - Consolidated report with all findings
2. **`logs/account_004_dormancy.json`** - Detailed analysis of account 004 dormancy
3. **`logs/account_006_dormancy.json`** - Detailed analysis of account 006 dormancy
4. **`logs/account_002_optimization.json`** - Optimization recommendations for account 002

## Analysis Methodology

### 1. Account 001 vs 003 Comparison

**Method:**
- Compare strategy assignments (strategy_key, instruments, risk_level, session_preference)
- Compare transaction patterns (trade count, PnL, win rate, instruments traded)
- Calculate similarity score based on config overlap

**Possible Conclusions:**
- `CONFIG_CLONE_BEHAVIOR` - Identical configs leading to identical behavior
- `HIGH_CONFIG_SIMILARITY` - Similar configs leading to similar behavior
- `DIFFERENT_CONFIG` - Different configs, different behavior

**Evidence Sources:**
- Runtime config (`runtime/config.yaml`)
- Strategy registry
- OANDA transaction API (last 7 days)
- Journalctl logs (last 168 hours)

### 2. Account 004 Dormancy Analysis

**Method:**
- Check strategy assignment configuration
- Parse journalctl logs for error patterns
- Analyze transaction history
- Classify root cause

**Possible Root Causes:**
- `CONFIG_ERROR` - Missing instruments or invalid config
- `REGIME_BLOCK` - Session/regime gate blocking all entries
- `NO_SIGNALS` - Strategy not generating signals
- `DISABLED_ASSIGNMENT` - Strategy assignment disabled
- `NO_TRADES_EXECUTED` - Signals generated but not executed

**Error Patterns Detected:**
- "missing instruments"
- "strategy registry missing"
- "STRICT MODE: No instruments defined"
- "SESSION_REGIME_GATE blocked"
- "no signals"
- "disabled assignment"

### 3. Account 006 Dormancy Analysis

**Method:**
- Check strategy assignment (likely `session_execution`)
- Parse journalctl logs for regime gate patterns
- Check session_regime_gate audit logs
- Analyze transaction history

**Possible Root Causes:**
- `REGIME_LOCKED` - Roadmap misaligned or daily/weekly neutral
- `REGIME_GATE_BLOCKED` - Session regime gate blocking entries
- `DISABLED_ASSIGNMENT` - Strategy assignment disabled
- `NO_TRADES_EXECUTED` - Signals generated but not executed

**Regime Patterns Detected:**
- "roadmap_misaligned"
- "daily_or_weekly_neutral"
- "session_regime_gate_blocked"
- "no_signals"

### 4. Account 002 Optimization Analysis

**Method:**
- Analyze ORDER_FILL transactions (last 7 days)
- Compute metrics:
  - Trades per hour
  - Average PnL per trade
  - Win rate
  - Stop size distribution
- Identify profile:
  - `HIGH_FREQUENCY_LOW_EDGE` - High frequency + low avg PnL
  - `HIGH_FREQUENCY` - High frequency only
  - `LOW_EXPECTANCY` - Low avg PnL only
  - `NORMAL` - Normal trading profile

**Optimization Recommendations (Non-Risk-Increasing):**

1. **Increase Signal Cooldown**
   - Add minimum time between signals (15-30 minutes)
   - Reduces churn while maintaining edge

2. **Require Higher Confidence Threshold**
   - Raise minimum confidence threshold for signal generation
   - Filters out lower-quality signals

3. **Restrict to Best Session Window**
   - Limit trading to highest-performing session (analyze by hour)
   - Focus on best-performing time windows

4. **Widen Stop Slightly OR Reduce Frequency**
   - Either widen stop loss slightly (5-10% more) OR reduce trade frequency
   - Small stops may be getting hit by noise

5. **Review Stop Loss Logic**
   - Review stop loss placement if win rate < 50%
   - May be too tight or poorly positioned

**Thresholds:**
- High Frequency: > 2.0 trades per hour
- Low Expectancy: < $0.50 avg PnL per trade

## Truth Sources

All conclusions are traceable to:

1. **Runtime Config** - `runtime/config.yaml`
   - Strategy assignments
   - Account configurations
   - Risk limits

2. **Strategy Registry** - `src/control_plane/strategy_registry.py`
   - Strategy metadata
   - Instrument lists
   - Risk levels

3. **OANDA Transaction API** - Direct API calls
   - ORDER_FILL transactions
   - Transaction PL fields
   - Trade timestamps
   - Instruments traded

4. **Journalctl Logs** - System logs
   - Runner activity
   - Error patterns
   - Block reasons
   - Signal generation

5. **Status Snapshot** - `runtime/status.json` (if available)
   - Last scan time
   - Signals generated
   - Trades executed

## Success Criteria

✅ Each conclusion traceable to logs or transactions  
✅ No speculation without evidence  
✅ Clear, actionable optimization steps for account 002  
✅ No system changes performed (read-only)

## Example Output

```json
{
  "probe_timestamp": "2026-01-22T12:00:00Z",
  "account_001_vs_003": {
    "conclusion": "CONFIG_CLONE_BEHAVIOR",
    "explanation": "Accounts 001 and 003 have identical configurations..."
  },
  "account_004_dormancy": {
    "root_cause": "CONFIG_ERROR",
    "explanation": "Account 004 is dormant due to: CONFIG_ERROR..."
  },
  "account_006_dormancy": {
    "root_cause": "REGIME_LOCKED",
    "explanation": "Account 006 is dormant due to: REGIME_LOCKED..."
  },
  "account_002_optimization": {
    "analysis": {
      "profile": "HIGH_FREQUENCY_LOW_EDGE",
      "avg_trades_per_hour": 3.5,
      "avg_pnl_per_trade": 0.25
    },
    "recommendations": [...]
  }
}
```

## Notes

- All analysis is read-only
- No code changes are made
- No configuration is modified
- No execution is overridden
- All findings are evidence-based
- Recommendations focus on throttling and quality, not increased risk
