# Monday Unlock Checklist (Paper-Safe)

**Date:** 2026-01-05  
**Branch:** `safety/savepoint-pre-lockin`  
**Commit:** `e5d079a`

---

## Pre-Flight Verification

Run these commands to verify system is ready:

```bash
# 1. Verify repo state
python3 scripts/verify_repo_state.py

# 2. Verify local bringup
bash scripts/verify_all_local.sh

# 3. Check control plane
curl -s http://127.0.0.1:8787/api/status | python3 -m json.tool
```

**Expected:** All verifiers pass, `execution_enabled: false`, `mode: paper`

---

## Unlock Sequence (Paper Execution Only)

### Step 1: Rotate Secrets (Out-of-Band)

**DO NOT** set secrets in the repo. Set them only as environment variables on the VM:

1. Rotate OANDA practice API key (if needed)
2. Rotate Telegram bot token (if needed)
3. Document new values in secure location (NOT in repo)

### Step 2: Set Environment Variables on VM

**On the VM**, set these environment variables (use Secret Manager or secure env file):

```bash
# OANDA Practice Account
export OANDA_API_KEY="<your-practice-api-key>"
export OANDA_ACCOUNT_ID="<your-practice-account-id>"
export OANDA_ENVIRONMENT="practice"

# Telegram (optional)
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
export TELEGRAM_CHAT_ID="<your-chat-id>"
```

**CRITICAL:** Never commit these values to the repo.

### Step 3: Unlock Gates (One at a Time)

#### A. Test Telegram (Optional)

```bash
export SECRETS_ROTATED_OK=true
export TELEGRAM_TEST_APPROVED=true
python3 scripts/telegram_health_check.py
```

**Expected:** `getMe OK: bot @<username>` and `sendMessage OK`

#### B. Deploy to VM

```bash
export DEPLOY_APPROVED=true
export VM_HOST="<your-vm-hostname-or-ip>"
export VM_USER="<your-vm-username>"
export VM_DIR="/opt/ai_quant"
bash scripts/vm_deploy_gated.sh
```

**Expected:** SSH preflight passes, code deployed, services NOT started (you must start them manually)

#### C. Enable Paper Execution (If Desired)

**ONLY** if you want paper execution (practice account trading):

```bash
export EXECUTION_UNLOCK_OK=true
# OANDA_ACCOUNT_ID and OANDA_API_KEY must be set (from Step 2)
```

**WARNING:** This enables paper execution. Live trading remains blocked.

---

## Verification After Unlock

### Check Execution Status

```bash
curl -s http://127.0.0.1:8787/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"mode={d['mode']}, execution_enabled={d['execution_enabled']}, accounts_loaded={d['accounts_loaded']}\")"
```

**Expected:**
- `mode=paper` (never `live`)
- `execution_enabled=true` (only if `EXECUTION_UNLOCK_OK=true` and account configured)
- `accounts_loaded=1` (if account configured)

### Check Scan Advancement

```bash
T0=$(curl -s http://127.0.0.1:8787/api/status | python3 -c "import sys,json; print(json.load(sys.stdin).get('last_scan_at',''))")
sleep 65
T1=$(curl -s http://127.0.0.1:8787/api/status | python3 -c "import sys,json; print(json.load(sys.stdin).get('last_scan_at',''))")
echo "T0=$T0"
echo "T1=$T1"
test "$T0" != "$T1" && echo "OK: scan advances" || echo "FAIL: scan not advancing"
```

**Expected:** `OK: scan advances` (T0 != T1)

---

## Safety Reminders

1. **Execution is OFF by default** - Must explicitly unlock with `EXECUTION_UNLOCK_OK=true`
2. **Live trading is BLOCKED** - Requires `TRADING_MODE=live` + `LIVE_TRADING=true` + `LIVE_TRADING_CONFIRM=true` (not covered in this checklist)
3. **Secrets are NEVER in repo** - All secrets must be set via environment variables
4. **Gates are LOCKED by default** - Each gate requires explicit approval
5. **Paper mode is SAFE** - Practice account only, no real money

---

## Rollback

To disable execution:

```bash
unset EXECUTION_UNLOCK_OK
# Restart runner
```

To disable all unlocks:

```bash
unset SECRETS_ROTATED_OK
unset TELEGRAM_TEST_APPROVED
unset DEPLOY_APPROVED
unset EXECUTION_UNLOCK_OK
```

---

## Troubleshooting

### Error: "EXECUTION_UNLOCK_OK=true requires OANDA_ACCOUNT_ID"

**Solution:** Set `OANDA_ACCOUNT_ID` environment variable or set `EXECUTION_UNLOCK_OK=false`

### Error: "VM_HOST appears to be a placeholder"

**Solution:** Use real VM hostname/IP, not placeholder values

### Error: "SSH preflight failed"

**Solution:** Check SSH key is authorized, VM is reachable, `VM_USER` and `VM_HOST` are correct

### Status shows `execution_enabled: false` after unlock

**Solution:** 
1. Verify `EXECUTION_UNLOCK_OK=true`
2. Verify `OANDA_ACCOUNT_ID` is set
3. Verify `PAPER_EXECUTION_ENABLED=true` (for paper mode)
4. Check runner logs for gate decisions

---

## Quick Reference

| Gate | Default | Unlock Command |
|------|---------|----------------|
| `EXECUTION_UNLOCK_OK` | `false` | `export EXECUTION_UNLOCK_OK=true` |
| `DEPLOY_APPROVED` | `false` | `export DEPLOY_APPROVED=true` |
| `SECRETS_ROTATED_OK` | `false` | `export SECRETS_ROTATED_OK=true` |
| `TELEGRAM_TEST_APPROVED` | `false` | `export TELEGRAM_TEST_APPROVED=true` |

**All gates are locked by default. Unlock only when ready.**
