# ⚠️ CRITICAL: SECRET ROTATION REQUIRED

## Security Alert

This repository contains **extensive hardcoded secrets exposure** in git history and tracked files.

### Exposed Secrets

1. **OANDA API Key**: Found in 150+ files and git history
2. **Telegram Bot Token**: Found in 130+ files and git history

### Immediate Actions Required

**ROTATE BOTH SECRETS IMMEDIATELY:**

1. **OANDA API Key**:
   - Log into https://www.oanda.com
   - Navigate to API Access
   - **REVOKE** the exposed key
   - Create a new API key
   - Store new key in environment variables (see docs/API_UPDATES_GUIDE.md)

2. **Telegram Bot Token**:
   - Contact @BotFather on Telegram
   - Use `/revoke` command
   - Create new bot or regenerate token
   - Store new token in environment variables (see docs/API_UPDATES_GUIDE.md)

### Current State

- ✅ Pre-commit hook installed (blocks future secret commits)
- ✅ .gitignore hardened (blocks 150+ files with secrets)
- ✅ .env.example template created
- ✅ Documentation added (docs/API_UPDATES_GUIDE.md)
- ⚠️ **Git history contains secrets** (history rewrite required for complete cleanup)
- ⚠️ **Many files still tracked with secrets** (being untracked in next commit)

### Post-Rotation Steps

1. Set environment variables with NEW rotated secrets:
   ```bash
   # Local development
   cp .env.example .env
   # Edit .env with NEW values
   set -a; source .env; set +a
   ```

2. Never commit the new secrets to git

3. Verify the system works with new secrets

4. Consider git history rewrite (advanced, see HARDENING_SUMMARY.md)

### Files Being Untracked

150+ files containing hardcoded secrets are being removed from git tracking.
They remain on disk for reference but won't be pushed to GitHub.

See .gitignore for complete list.
