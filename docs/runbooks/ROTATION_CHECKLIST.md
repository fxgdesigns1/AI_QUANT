# Credential Rotation Checklist

## ⚠️ IMPORTANT

This document provides procedures for rotating API credentials **outside the repository**. Never store rotated credentials in git - use environment variables or secret managers.

## Pre-Rotation Checklist

- [ ] Backup current working `.env` file (if exists)
- [ ] Document which credentials are being rotated
- [ ] Schedule rotation during low-activity period
- [ ] Notify team members if applicable

---

## OANDA API Key Rotation

### When to Rotate
- Key found in git history or quarantined files
- Suspected unauthorized access
- Regular security rotation (recommended: quarterly)

### Steps

1. **Log into OANDA**
   - Demo account: https://www.oanda.com/demo-account/
   - Live account: https://www.oanda.com/account/

2. **Generate New API Token**
   - Navigate to: Account → Manage API Access
   - Click "Generate" or "Revoke and Create New"
   - **IMPORTANT**: Copy new token immediately (shown only once)

3. **Update Environment**
   ```bash
   # VM
   sudo nano /etc/ai-quant/ai-quant.env
   # Update: OANDA_API_KEY=REDACTED
   
   # Local
   nano .env
   # Update: OANDA_API_KEY=REDACTED
   ```

4. **Restart Services**
   ```bash
   sudo systemctl restart ai-quant-control-plane.service
   ```

5. **Verify**
   ```bash
   curl -s http://127.0.0.1:8787/api/status | jq '{mode, accounts_loaded}'
   # Should show accounts_loaded > 0 if key is valid
   ```

---

## Telegram Bot Token Rotation

### When to Rotate
- Token found in git history
- Bot behavior is compromised
- Regular security rotation

### Steps

1. **Open Telegram**
   - Message [@BotFather](https://t.me/BotFather)

2. **Revoke Current Token**
   ```
   /mybots → Select your bot → API Token → Revoke current token
   ```

3. **Generate New Token**
   ```
   /token
   ```
   Copy the new token (format: `123456789:ABCdefGHI...`)

4. **Update Environment**
   ```bash
   sudo nano /etc/ai-quant/ai-quant.env
   # Update: TELEGRAM_BOT_TOKEN=REDACTED
   ```

5. **Test**
   ```bash
   # Send test message (requires TELEGRAM_SEND_TEST=1)
   TELEGRAM_SEND_TEST=1 bash scripts/audit_cloud_readiness_complete.sh
   ```

---

## OpenAI API Key Rotation

### When to Rotate
- Key found in git history (sk-...)
- Unusual API usage detected
- Regular rotation

### Steps

1. **Go to OpenAI Dashboard**
   - https://platform.openai.com/api-keys

2. **Delete Old Key**
   - Click trash icon next to exposed key

3. **Create New Key**
   - Click "Create new secret key"
   - Name it (e.g., "ai-quant-prod-2026-01")
   - Copy immediately (shown only once)

4. **Update Environment**
   ```bash
   sudo nano /etc/ai-quant/ai-quant.env
   # Update: OPENAI_API_KEY=sk-new-key-here
   ```

5. **Verify** (if AI insights enabled)
   ```bash
   # Check AI endpoint responds (should not error)
   curl -s http://127.0.0.1:8787/api/status | jq '.ai_configured'
   ```

---

## Google API Key Rotation

### When to Rotate
- Key found in git history (AIza...)
- Unexpected API quota usage
- Regular rotation

### Steps

1. **Go to Google Cloud Console**
   - https://console.cloud.google.com/apis/credentials

2. **Delete or Restrict Old Key**
   - Click on exposed key → Delete
   - Or: Add API restrictions to limit damage

3. **Create New Key**
   - Click "Create Credentials" → "API key"
   - Add restrictions (recommended: IP, API, referrer)

4. **Update Environment**
   ```bash
   sudo nano /etc/ai-quant/ai-quant.env
   # Update: GOOGLE_API_KEY=AIza-new-key-here
   ```

---

## Control Plane Token Rotation

### When to Rotate
- Token compromised
- After team member offboarding
- Regular rotation

### Steps

1. **Generate New Token**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update Environment**
   ```bash
   sudo nano /etc/ai-quant/ai-quant.env
   # Update: CONTROL_PLANE_TOKEN=new-token-here
   ```

3. **Restart Service**
   ```bash
   sudo systemctl restart ai-quant-control-plane.service
   ```

4. **Update Dashboard**
   - Open dashboard → Settings → Update token

---

## Post-Rotation Verification

Run full verification after any rotation:

```bash
# 1. Check service health
sudo systemctl status ai-quant-control-plane.service

# 2. Check API status
curl -s http://127.0.0.1:8787/api/status | jq

# 3. Verify no secrets in repo
bash scripts/security/verify_repo_no_secrets.sh
```

## Rotation Schedule (Recommended)

| Credential | Rotation Frequency | Last Rotated |
|------------|-------------------|--------------|
| OANDA_API_KEY | Quarterly | ____-__-__ |
| TELEGRAM_BOT_TOKEN | Annually | ____-__-__ |
| OPENAI_API_KEY | Quarterly | ____-__-__ |
| GOOGLE_API_KEY | Annually | ____-__-__ |
| CONTROL_PLANE_TOKEN | After incidents | ____-__-__ |

---

**Last Updated**: 2026-01-04
**Owner**: Security/DevOps
