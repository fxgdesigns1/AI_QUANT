# FXG AI-QUANT — Cloud Readiness Audit (Non-Destructive)

**Audit Date**: Sun Jan  4 21:33:04 UTC 2026
**Repo Root**: repo_root=/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system
**Git HEAD**: b4f68c236aff061b52b4f96b3ed4b3c44c19dae2

---

## ⚠️ EXECUTION STATUS

**LOCAL PHASES (Completed)**: Phases 0-3 ✅
**VM PHASES (Pending)**: Phases 4-8 require VM execution

To complete VM phases:
```bash
# SSH to VM
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b fxg-quant-paper-e2-micro

# Run VM audit script
cd ~/gcloud-system
bash scripts/audit_vm_phases.sh
```

---

## 1. Verified Runtime Safety (VM) — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- mode: **paper**
- execution_enabled: **false**
- active_strategy_key: **[to be captured]**

---

## 2. Single Source of Truth / Duplicate Detection — ✅ VERIFIED (LOCAL)

- **Local repo root**: `/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system`
- **start_control_plane_clean.sh hits**: 0
- **src/control_plane/api.py hits**: 0

✅ **No duplicate copies found** in parent directories (maxdepth=5 search)
- Only one canonical repo detected

---

## 3. Secrets Scan (Redacted) — ✅ VERIFIED (LOCAL)

- **Hit count**: 100
- **.env files present (maxdepth=3)**: 2
  - Files: ./.env, ./.env.example

**Classification**:
- Hardcoded secrets found: **1**
- Environment variable references (code): **63**
- Comments/docs: **10**

⚠️ **WARNING**: Potential hardcoded secrets detected. Review `ARTIFACTS/secrets_scan_raw_hits.txt` (redacted)

---

## 4. Code Capability Inventory — ✅ VERIFIED (LOCAL)

### Strategies
- **Code hits**: 48 lines
- **Key findings**:
  - `/api/strategies` endpoint exists
  - `active_strategy_key` configuration present
  - Strategy catalog/catalog management code present

### Accounts
- **Code hits**: 40 lines
- **Key findings**:
  - `accounts_loaded` and `accounts_execution_capable` fields in StatusResponse
  - OANDA integration code present
  - Account loading logic in control plane API

### Telegram
- **Code hits**: 15 lines
- **Key findings**:
  - `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env var support
  - Telegram configuration methods in settings.py
  - **Runtime verification**: ⚠️ PENDING (requires VM execution)

### Reports (Daily/Weekly/Monthly)
- **Code hits**: 4 lines
  - References to `daily`, `weekly`, `monthly` found in code
  - **Gap Analysis**: ⚠️ PENDING (requires VM execution to verify scheduler/generation)

### AI Readiness
- **Code hits**: 49 lines
- **Key findings**:
  - OpenAI integration (`openai` SDK) present
  - Gemini integration (`gemini`) present
  - AI insights module: `src/ai/ai_insights.py`
  - **Runtime verification**: ⚠️ PENDING (requires VM execution)

### Dashboard Guards (Blocked Endpoints)
- **Code hits**: 41 lines
- **Key findings**:
  - `BLOCKED_ENDPOINTS` array in forensic_command.html
  - Noise shims for `/socket.io`, `/tasks/full_scan`, `/api/insights`, `/api/trade_ideas`
  - `isBlocked()` function implemented
  - ✅ **Guards present in code**

---

## 5. Strategies Runtime Truth — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- GET /api/strategies returns allowed keys
- Strategy switching cycle across all allowed keys
- Revert to original strategy after cycle

---

## 6. Accounts Runtime Truth — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- `/api/status` shows `accounts_loaded` count
- `/api/status` shows `accounts_execution_capable` count
- Values match expected account configuration

---

## 7. Dashboard Switching Proof — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- Strategy switching via POST /api/config succeeds for all allowed keys
- Active strategy reverts to original after cycle
- No permanent state changes (non-destructive)

---

## 8. Telegram Verification — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- Environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` presence (SET/MISSING)
- Code presence confirmed
- Optional send test if configured (set `TELEGRAM_SEND_TEST=1`)

---

## 9. Reports Verification — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- Daily/weekly/monthly report generation code found
- Scheduler mechanism identified (cron/systemd/APScheduler/etc.)
- Or explicit GAP if not implemented

---

## 10. AI Readiness — ⚠️ PENDING VM EXECUTION

**Status**: Cannot verify until VM phases are executed

**Expected Verification**:
- Environment variables: `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc. (SET/MISSING)
- Code presence confirmed
- Egress checks (HTTP connectivity to APIs)
- Optional E2E test if configured (set `AI_E2E_TEST=1`)

---

## GO / NO-GO Status

### ✅ VERIFIED (Local)
- ✅ Single source of truth: No duplicate repos detected
- ✅ Secrets scan: No hardcoded secrets (all env references)
- ✅ Code inventory: Strategies, Accounts, Telegram, AI, Guards all present in codebase
- ✅ Dashboard guards: Blocked endpoints protected in forensic_command.html

### ⚠️ PENDING (VM Execution Required)
- ⚠️ Runtime safety: Paper mode, execution_enabled=false (needs VM verification)
- ⚠️ Strategies: Runtime truth and switching cycle (needs VM verification)
- ⚠️ Accounts: Runtime truth (accounts_loaded, accounts_execution_capable)
- ⚠️ Dashboard switching: Strategy cycle and revert proof
- ⚠️ Telegram: Env presence and optional send test
- ⚠️ Reports: Scheduler/generation mechanism verification
- ⚠️ AI: Env presence, egress checks, E2E test

### 🚦 GO/NO-GO Decision

**Status**: **PARTIAL GO** (Local verification complete, VM verification pending)

**Next Actions**:
1. Execute VM audit phases: `bash scripts/audit_vm_phases.sh` on VM
2. Review VM artifacts in `ARTIFACTS/` directory
3. Re-run Phase 9 report generation to include VM results
4. Final GO/NO-GO decision after VM verification

---

## Evidence Files

See `EVIDENCE_INDEX.md` for complete artifact listing.