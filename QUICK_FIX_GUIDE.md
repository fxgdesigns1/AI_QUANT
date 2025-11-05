# 🚀 Quick Fix Guide - Trade Execution Issues

## Immediate Actions

### 1. **Clear Stale Halts (Most Common Issue)**

**Problem:** News halts or sentiment throttles from weekend are blocking trades.

**Quick Fix:**
```python
from ai_trading_system import AITradingSystem

system = AITradingSystem()
system.news_halt_until = None
system.throttle_until = None
system.risk_per_trade = system.base_risk
```

**Or run:**
```bash
python3 startup_recovery.py
```

### 2. **Enable Trading**

**Check if trading is enabled:**
```python
system.trading_enabled  # Should be True
```

**Enable if disabled:**
```python
system.trading_enabled = True
```

**Or via Telegram:**
```
/start_trading
```

### 3. **Check Monday Morning Recovery**

**On Monday mornings, the system should automatically:**
- ✅ Clear stale halts from weekend
- ✅ Clear stale throttles
- ✅ Restore risk settings

**If it doesn't, manually run:**
```bash
python3 startup_recovery.py
```

## Common Blocking Conditions

### 1. News Halt Active
**Symptom:** No trades executing, halt message in logs

**Fix:**
```python
system.news_halt_until = None
```

### 2. Sentiment Throttle Active
**Symptom:** Risk reduced, trades blocked

**Fix:**
```python
system.throttle_until = None
system.risk_per_trade = system.base_risk
```

### 3. Outside Trading Hours
**Symptom:** XAU trades blocked outside London session (OLD - FIXED)

**Fix Applied:** Now allows trading during London/NY/overlap, only blocks Asian session (0-8 UTC)

### 4. Position Limits Reached
**Symptom:** "Max concurrent trades reached" in logs

**Fix:** Close some positions or increase `max_concurrent_trades`

### 5. Daily Trade Limit Reached
**Symptom:** "Daily trade limit reached" in logs

**Fix:** Wait for reset or increase `max_daily_trades`

### 6. Spread Too Wide
**Symptom:** "Spread too wide" in logs

**Fix:** Wait for tighter spreads or increase spread limits

## Diagnostic Commands

### Run Full Diagnostic
```bash
python3 comprehensive_trade_diagnostic.py
```

### Check System Status
```python
from ai_trading_system import AITradingSystem

system = AITradingSystem()

# Check all blocking conditions
print(f"Trading enabled: {system.trading_enabled}")
print(f"News halt active: {system.is_news_halt_active()}")
print(f"Throttle active: {system.is_throttle_active()}")
print(f"London session: {system.in_london_session()}")
print(f"Daily trades: {system.daily_trade_count}/{system.max_daily_trades}")

# Check positions
live = system.get_live_counts()
print(f"Live positions: {live['positions'] + live['pending']}/{system.max_concurrent_trades}")
```

## Strategy Switching Issues

**If strategy switching doesn't work smoothly:**

1. **Check if positions are closing:**
   - Strategy switch requires positions to close first
   - Wait for positions to close or close manually

2. **Verify accounts.yaml updated:**
   ```bash
   cat accounts.yaml | grep -A 5 "account_id"
   ```

3. **Check config reloader:**
   - Config reloader should pick up changes
   - If not, restart may be needed

4. **Check graceful restart:**
   - System should gracefully restart after strategy switch
   - Check logs for restart messages

## Weekend/Monday Issues

### Before Weekend
- System may set halts for weekend
- These should clear automatically on Monday

### Monday Morning
- Run `startup_recovery.py` if trades aren't executing
- System should auto-clear stale halts, but manual check helps

### After Weekend
- Check if stale halts are cleared
- Verify trading is enabled
- Check if risk is restored

## Verification Steps

1. ✅ **Check trading enabled:** `system.trading_enabled == True`
2. ✅ **Check no halts:** `system.news_halt_until is None`
3. ✅ **Check no throttle:** `system.throttle_until is None`
4. ✅ **Check position limits:** Not at max
5. ✅ **Check daily limits:** Not at max
6. ✅ **Check market hours:** Not weekend, appropriate session
7. ✅ **Check spreads:** Within limits
8. ✅ **Check signals generated:** Run `analyze_market()` and check for signals

## Emergency Reset

If nothing works, reset everything:

```python
from ai_trading_system import AITradingSystem

system = AITradingSystem()

# Clear all halts
system.news_halt_until = None
system.throttle_until = None

# Restore defaults
system.risk_per_trade = 0.01  # 1%
system.trading_enabled = True

# Reset daily counter (if needed)
# system.daily_trade_count = 0  # Only if you want to reset daily limit

print("✅ System reset complete")
```

## Monitoring

**Watch for these log messages:**
- ✅ `🧹 Clearing stale news halt` - Good, system is auto-fixing
- ✅ `🧹 Clearing expired sentiment throttle` - Good, system is auto-fixing
- ❌ `News halt active; skipping new entry` - Halt is blocking trades
- ❌ `Sentiment throttle active` - Throttle is blocking trades
- ❌ `XAU entry blocked: outside London session` - OLD (shouldn't see this anymore)
- ✅ `XAU entry blocked: Asian session (low liquidity)` - NEW (only blocks 0-8 UTC)

## Files to Check

1. **System logs:** Check for error messages
2. **ai_trading_system.py:** Main trading system
3. **accounts.yaml:** Strategy configurations
4. **Telegram commands:** Use `/status` to check system state

---

**Remember:** The system now automatically clears stale halts on startup and during trading cycles. If issues persist after fixes, check the diagnostic output for specific blocking conditions.
