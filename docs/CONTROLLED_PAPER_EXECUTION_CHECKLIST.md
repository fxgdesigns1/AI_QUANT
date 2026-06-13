# Controlled Paper Execution Checklist

**Goal**: Execute paper trades in a controlled, safe manner with full observability.
**Mode**: PAPER ONLY
**Safety**: Fail-Closed

## 1. Pre-Flight Checks

| Check | Requirement | Verification Method | Status |
|---|---|---|---|
| **Trading Mode** | Must be `PAPER` | Check `api/status` or `api/config` | ⬜ |
| **Execution Enabled** | Must be `TRUE` | `TRADING_MODE=paper PAPER_EXECUTION_ENABLED=true` | ⬜ |
| **Kill Switch** | Must be `OFF` | `KILL_SWITCH=false` in env | ⬜ |
| **Session** | Must be London, NY, or Asia | Dashboard: "Current Session" | ⬜ |
| **Regime** | Must be `TRENDING` (or policy allowed) | Dashboard: "Regime" != UNKNOWN | ⬜ |
| **News** | No Embargo Active | Dashboard: "News Status" | ⬜ |
| **Roadmap** | Daily & Weekly Bias Aligned | Dashboard: "Roadmap Aligned" = True | ⬜ |

## 2. GO / NO-GO Decision Table

| Condition | Action | Log Evidence |
|---|---|---|
| **Embargo Active** | **NO-GO** | `session_regime_gate_audit.jsonl` reason: `news_embargo` |
| **Regime UNKNOWN** | **NO-GO** | `session_regime_gate_audit.jsonl` reason: `policy_not_found` |
| **Roadmap Misaligned** | **NO-GO** | `session_regime_gate_audit.jsonl` reason: `roadmap_misaligned` |
| **Bias Neutral** | **NO-GO** | `session_regime_gate_audit.jsonl` reason: `daily_or_weekly_neutral` |
| **All Checks Pass** | **GO** | `session_regime_gate_audit.jsonl` reason: `policy_allow` |

## 3. Verification Steps

1. **Run Probe**: `python3 scripts/lifecycle_probe.py`
2. **Check Logs**: `tail -f logs/session_regime_gate_audit.jsonl`
3. **Monitor Dashboard**: Verify "Why Trades Are Blocked" panel clears.
4. **Confirm OANDA**: Verify trade appears in OANDA practice account.

## 4. Emergency Stop

If behavior is unexpected:
1. Set `KILL_SWITCH=true` in `.env`.
2. Restart runner: `sudo systemctl restart ai-quant-runner` (or equivalent).
3. Verify `api/status` shows `execution_guard.allowed = false`.
