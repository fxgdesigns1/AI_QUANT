# 🚨 CRITICAL: ROTATE COMPROMISED SECRETS IMMEDIATELY

## SECURITY BREACH DETECTED
Multiple secrets have been leaked in this repository's working tree and git history. **ALL LISTED SECRETS MUST BE ROTATED BEFORE ANY DEPLOYMENT.**

## COMPROMISED SECRETS REQUIRING IMMEDIATE ROTATION

### 1. OANDA API Key
- **Status**: 🔴 COMPROMISED - Found in 35+ files and git history
- **Current Key Pattern**: `c01de9eb4d79*` (REDACTED)
- **Action Required**: 
  1. Log into OANDA Practice Account
  2. Revoke existing API key immediately
  3. Generate new Practice API key (PAPER TRADING ONLY)
  4. Record new key in secure location (NOT in this repo)
- **Rotation Deadline**: BEFORE any code deployment
- **Rotation Completed**: ❌ PENDING

### 2. Telegram Bot Token  
- **Status**: 🔴 COMPROMISED - Found in git history
- **Current Token Pattern**: `7248728383:*` (REDACTED)
- **Action Required**:
  1. Contact @BotFather on Telegram
  2. Use `/revoke` command to invalidate current token
  3. Generate new bot token
  4. Record new token in secure location (NOT in this repo)
- **Rotation Deadline**: BEFORE any code deployment  
- **Rotation Completed**: ❌ PENDING

## POST-ROTATION CHECKLIST

After rotating secrets, update the following:

### Environment Variables (VM/Local)
```bash
# Update these environment variables with NEW values
export OANDA_API_KEY="<NEW_PRACTICE_KEY>"
export TELEGRAM_BOT_TOKEN="<NEW_BOT_TOKEN>"
```

### GCP Secret Manager (Production)
```bash
# Update GCP secrets with NEW values
gcloud secrets versions add OANDA_API_KEY --data-file=- <<< "<NEW_PRACTICE_KEY>"
gcloud secrets versions add TELEGRAM_BOT_TOKEN --data-file=- <<< "<NEW_BOT_TOKEN>"
```

### Verification Commands
```bash
# Verify old keys no longer work
curl -H "Authorization: Bearer <OLD_OANDA_KEY>" https://api-fxpractice.oanda.com/v3/accounts
# Should return 401 Unauthorized

# Verify new keys work  
curl -H "Authorization: Bearer <NEW_OANDA_KEY>" https://api-fxpractice.oanda.com/v3/accounts
# Should return account data
```

## DEPLOYMENT BLOCKER

**🚫 DEPLOYMENT IS BLOCKED UNTIL:**
1. ✅ OANDA API key rotated and verified
2. ✅ Telegram bot token rotated and verified  
3. ✅ Old secrets confirmed revoked
4. ✅ New secrets tested and working
5. ✅ This checklist marked complete

## ROTATION COMPLETION LOG

| Secret | Rotated Date/Time | Verified By | Notes |
|--------|------------------|-------------|-------|
| OANDA_API_KEY | ❌ PENDING | - | Must be Practice/Paper key only |
| TELEGRAM_BOT_TOKEN | ❌ PENDING | - | Bot notifications only |

**⚠️ DO NOT COMMIT NEW SECRETS TO THIS REPOSITORY**
**⚠️ ONLY USE ENVIRONMENT VARIABLES OR SECRET MANAGER**

---
*This rotation checklist was generated automatically by security audit on 2026-01-05*