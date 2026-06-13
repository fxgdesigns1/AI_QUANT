# Why Trades Don't Execute

**Transparency Report on System Decisions**

The AI Trading System operates on a **Fail-Closed** basis. This means it defaults to *not* trading unless strict conditions are met. Silence is often a valid and safe outcome.

## Common Blockers (Visible in Dashboard)

### 1. News Embargo (`news_embargo`)
*   **Cause**: High-impact news event is imminent or recently occurred.
*   **Duration**: Typically 60 mins before to 60 mins after event.
*   **Resolution**: Wait for embargo to expire. System auto-clears.

### 2. Roadmap Misaligned (`roadmap_misaligned`)
*   **Cause**: Daily and Weekly biases do not agree (e.g., Daily Bullish, Weekly Bearish).
*   **Resolution**: Market must align on multiple timeframes. No manual override.

### 3. Regime Unknown (`policy_not_found`)
*   **Cause**: Insufficient price data to determine market regime (e.g., need 60+ candles).
*   **Resolution**: Ensure `lifecycle_probe.py` or runner has been running long enough to build history.

### 4. Policy Score Low (`policy_score_too_low`)
*   **Cause**: Even if aligned, the confidence score for the current setup is below threshold (0.6).
*   **Resolution**: Market conditions must improve (stronger trend, better volatility).

### 5. Execution Disabled (`execution_disabled`)
*   **Cause**: Global kill switch or paper execution disabled in config.
*   **Resolution**: Check `.env` for `PAPER_EXECUTION_ENABLED=true` or `KILL_SWITCH=false`.

## Log Reference

All decisions are logged in `logs/session_regime_gate_audit.jsonl`.

**Example Blocked Entry:**
```json
{
  "timestamp": "2024-01-20T09:00:00+00:00",
  "allowed": false,
  "symbol": "EUR_USD",
  "reason": "roadmap_misaligned",
  "roadmap_aligned": false,
  "daily_bias": "BULLISH",
  "weekly_bias": "NEUTRAL"
}
```

**Example Allowed Entry:**
```json
{
  "timestamp": "2024-01-20T09:00:00+00:00",
  "allowed": true,
  "symbol": "EUR_USD",
  "reason": "policy_allow",
  "roadmap_aligned": true,
  "regime": "TRENDING"
}
```
