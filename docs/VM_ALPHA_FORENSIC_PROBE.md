# VM_ALPHA Forensic Probe Report
**Date:** 2026-01-21
**Scope:** VM_ALPHA (Live/Paper)
**Status:** BLOCKED

## Executive Summary
The system is operational (running loops) but **functionally blinded** due to missing OANDA credentials in the application environment. This causes the Outlook Engine to fail, defaulting to a NEUTRAL bias, which in turn triggers the SessionRegimeGate to block all trading.

## Probe Findings

| Step | Check | Status | Evidence |
|------|-------|--------|----------|
| 1 | Runner Liveness | ✅ PASS | Processes active, `logs/runner.log` updating every 30s. |
| 2 | Execution Switches | ❓ UNKNOWN | Cannot inspect running process env directly, but `status.json` shows `mode: "paper"`. |
| 3 | OANDA Credentials | ❌ FAIL | `probe_full_decision_trace.py` failed with `MarketDataError: Missing required env var: OANDA_ACCOUNT_ID`. `outlook_daily.json` contains same error. |
| 4 | Outlook Bias | ❌ FAIL | `outlook_daily.json` shows `"bias": "NEUTRAL"` and error messages. |
| 5 | Signal Generation | ❌ FAIL | 0 signals generated in recent logs. |
| 6 | News Embargo | ✅ PASS | News is flowing (`status.json`), embargo is lifted or not active, but blocked by Neutral bias. |
| 7 | Session Regime Gate | ❌ FAIL | Blocked. Reason: `daily_or_weekly_neutral`. |
| 8 | Execution Guard | ✅ PASS | Enabled (`execution_enabled: true`), but never reached. |
| 9 | End-to-End Trace | ❌ FAIL | Crashed on Market Data fetch due to missing credentials. |

## Root Cause Analysis
**Primary Blocker:** `OUTLOOK_ENGINE_BLINDED`
The `OANDA_ACCOUNT_ID` and `OANDA_API_KEY` environment variables are not accessible to the running python processes (both the background runner and the probe scripts).

**Secondary Blocker:** `SESSION_GATE_ROADMAP_NEUTRAL`
The Outlook Engine defaults to `NEUTRAL` bias when it encounters an error (fail-safe). The `SessionRegimeGate` correctly blocks trading when the bias is Neutral or Unknown.

## Remediation Plan
1.  **Stop System:** `kill` active runner processes.
2.  **Inject Credentials:** Export `OANDA_ACCOUNT_ID` and `OANDA_API_KEY` in the shell or service definition.
3.  **Restart System:** Run `scripts/run_control_plane.sh` (or appropriate starter) with the env vars loaded.
4.  **Verify:** Re-run `scripts/probes/probe_full_decision_trace.py`.
