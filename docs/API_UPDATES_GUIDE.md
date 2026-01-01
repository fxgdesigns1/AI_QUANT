# Secrets & API Updates (SAFE)

## Goal
Keep secrets out of git. Update API keys/tokens without committing them.

## Option A (Simple): environment variables / local env file
1) Create a local file (NOT tracked by git): `.env`
2) Put real values there
3) Export for the process (examples):

### macOS/Linux
```bash
set -a; source .env; set +a
```

## Option B (VM/systemd): external env file
Store secrets at: `/etc/fxg/ai_trading.env` (NOT in git)
Example systemd unit should reference it:
- `EnvironmentFile=/etc/fxg/ai_trading.env`

## Option C (Recommended on GCP): Secret Manager
Store each secret in GCP Secret Manager and inject at runtime.

### Create secrets (example)
```bash
gcloud secrets create OANDA_API_KEY --replication-policy=automatic
printf "%s" "<REAL_VALUE>" | gcloud secrets versions add OANDA_API_KEY --data-file=-
```

### Access secrets (example)
```bash
gcloud secrets versions access latest --secret=OANDA_API_KEY
```

## Required variables
- OANDA_API_KEY
- OANDA_ACCOUNT_ID
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## Safety
- Never commit `.env` or any credentials JSON/key files.
- If a secret leaks: rotate it, then verify git history is clean.
