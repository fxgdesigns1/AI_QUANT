# Secrets Quarantine Notes — NON-DESTRUCTIVE

## ⚠️ CRITICAL FINDINGS

### Historical Forensic Files with Hardcoded Credentials

**Files identified:**
- `FORENSIC_AUDIT_REPORT.json` — Contains hardcoded OANDA API key and account IDs
- `forensic_snapshot/FXG_FORENSIC_REPORT.json` — Contains account IDs in code snippets
- `forensic_snapshot/FXG_ARCH_EVIDENCE.json` — Contains account IDs in code snippets

**Action Required (NON-DESTRUCTIVE):**
1. **DO NOT DELETE** these files (non-destructive audit)
2. Create redacted copies with `_REDACTED.json` suffix
3. Rotate affected credentials (OANDA API keys, account access)
4. Migrate runtime code to use environment variables or secret manager only
5. Update `.gitignore` to exclude these files if not already excluded

### Service Files with Hardcoded Credentials

**Files identified:**
- `ai_trading.service`
- `ai_trading_service_CORRECT.service`
- `ai_trading_service_FINAL.service`
- `ai_trading_service_ORIGINAL.service`
- `ai_trading_FIXED.service`
- `ai_trading_service_GROUND_TRUTH.service`
- `automated_trading.service`

**Action Required:**
- These systemd service files should use environment files or secret manager
- Replace hardcoded `Environment=` directives with `EnvironmentFile=`
- Rotate affected credentials

### SSH Private Keys

**Files identified:**
- `cloud_declutter_v2/Oracle/ssh-key-2025-12-15.key`
- `cloud_declutter_v2/Oracle/ssh-key-2025-12-01 (2).key`

**Action Required:**
- These should NOT be in the repository
- Ensure they are in `.gitignore`
- Rotate SSH keys if they are in use
- If archived, move to secure storage outside repo

### YAML Configuration Files

**Files identified:**
- `google-cloud-trading-system/app.yaml` and variants
- Various `*.yaml` files in `google-cloud-trading-system/` directory

**Action Required:**
- Use GCP Secret Manager or environment variables
- Remove hardcoded values from YAML files
- Use template files with placeholders

## ✅ SAFE FILES (No Action Required)

- `.env` — Local environment file (should be in `.gitignore`)
- `.env.example` — Example file with placeholders
- Documentation files (`.md`) with example values
- `SETUP_GUIDE.md` — Contains example placeholders only

## 🔒 RECOMMENDATIONS

1. **Immediate (NO-GO until addressed):**
   - Rotate all OANDA API keys found in historical files
   - Rotate Telegram bot tokens if exposed
   - Rotate Google API keys if exposed
   - Create redacted copies of historical forensic files

2. **Short-term:**
   - Audit `.gitignore` to ensure `.env`, `*.key`, and historical forensic files are excluded
   - Migrate all hardcoded credentials to environment variables or secret manager
   - Update service files to use `EnvironmentFile=` instead of `Environment=`

3. **Long-term:**
   - Implement pre-commit hooks to prevent committing secrets
   - Use secret scanning tools in CI/CD
   - Document credential rotation procedures

## 📋 VERDICT

**Status**: ⚠️ **REQUIRES IMMEDIATE ACTION**

Hardcoded credentials found in historical forensic files and service files require rotation and quarantine before production deployment.
