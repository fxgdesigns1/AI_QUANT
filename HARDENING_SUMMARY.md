# AI_QUANT Repository Hardening Summary

## Completed Actions

### 1. Secret Detection & Removal
- Removed hardcoded OANDA API key from `working_trading_system.py` and `working_auto_scanner.py`
- Files now require `OANDA_API_KEY` environment variable (fail-fast if missing)
- Untracked multiple files containing hardcoded secrets (kept on disk for reference)

### 2. .gitignore Hardening
- Comprehensive rules blocking:
  - `.env*` files (except `.env.example`)
  - Secret/token/credential patterns
  - Key files (`.pem`, `.key`)
  - Data directories (runtime/, reports/, backups/, archives/)
  - Node modules and large local folders
  - Forensic/diagnostic artifacts

### 3. Pre-commit Hook
- Repo-committed hook at `scripts/git-hooks/pre-commit`
- Installer script at `scripts/install_git_hooks.sh`
- Blocks commits containing secret patterns
- Excludes itself from scanning (avoids false positives)

### 4. Documentation
- `.env.example`: Safe template for environment variables
- `docs/API_UPDATES_GUIDE.md`: Complete guide for safe secret management
  - Local .env approach
  - VM/systemd approach
  - GCP Secret Manager approach (recommended)

## CRITICAL: Manual Actions Required

### ⚠️ ROTATE EXPOSED SECRETS IMMEDIATELY

**Telegram Bot Token (EXPOSED IN GIT HISTORY):**
- Token: `bot[REDACTED - see git history for old value, MUST rotate]`
- Action: Contact @BotFather, revoke and regenerate
- Update in environment variables (NOT in git)

**OANDA API Key (EXPOSED IN GIT HISTORY):**
- Key: `[REDACTED - see git history for old value, MUST rotate]`
- Action: Log into OANDA dashboard, revoke and create new key
- Update in environment variables (NOT in git)

### Git History Consideration

The exposed secrets are in git history. Options:

1. **RECOMMENDED (Simple):** 
   - Rotate secrets immediately
   - Current commit removes them from active code
   - History remains but secrets are invalidated

2. **ADVANCED (Destructive):**
   - Use `git-filter-repo` to rewrite history
   - Requires force-push to GitHub
   - Team needs to re-clone
   - High risk, only if absolutely necessary

## How to Use Rotated Secrets

### Local Development
```bash
# Create .env (ignored by git)
cat > .env <<'ENVEOF'
OANDA_API_KEY=<YOUR_NEW_KEY>
OANDA_ACCOUNT_ID=<YOUR_ACCOUNT>
TELEGRAM_BOT_TOKEN=<YOUR_NEW_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
ENVEOF

# Load and run
set -a; source .env; set +a
python working_trading_system.py
```

### VM/Production (systemd)
```bash
# Create /etc/fxg/ai_trading.env (root-only)
sudo mkdir -p /etc/fxg
sudo nano /etc/fxg/ai_trading.env
# Add real values

# Update service file
EnvironmentFile=/etc/fxg/ai_trading.env

# Restart
sudo systemctl daemon-reload
sudo systemctl restart ai_trading
```

### GCP Secret Manager (Recommended)
```bash
# Create secrets
gcloud secrets create OANDA_API_KEY --replication-policy=automatic
printf "%s" "<NEW_KEY>" | gcloud secrets versions add OANDA_API_KEY --data-file=-

gcloud secrets create TELEGRAM_BOT_TOKEN --replication-policy=automatic
printf "%s" "<NEW_TOKEN>" | gcloud secrets versions add TELEGRAM_BOT_TOKEN --data-file=-

# Grant runtime access
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Verification

- ✅ Pre-commit hook installed and active
- ✅ .gitignore blocking secrets, credentials, and artifacts
- ✅ Working tree clean (no hardcoded secrets in tracked files)
- ✅ Safe templates and documentation in place
- ⚠️ Git history contains old secrets (ROTATE IMMEDIATELY)

## Branch

Current branch: `hardening/no-secrets-20260101_155914`

To merge:
```bash
git checkout main
git merge hardening/no-secrets-20260101_155914
git push origin main
```

## Team Onboarding

When others clone/pull:
```bash
# Install pre-commit hook
./scripts/install_git_hooks.sh

# Create local .env from template
cp .env.example .env
# Edit .env with real values (NEVER commit)
```
