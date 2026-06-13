# AI Insights Operational Status

**Date**: 2026-01-13T02:00:00Z  
**Status**: ✅ CODE READY, ⚠️ KEYS REQUIRED  
**System**: ALPHA

---

## BRUTAL TRUTH: Current State

### ✅ Code Status
- **Backend**: ✅ Implemented (`src/ai/ai_insights.py`)
- **API Endpoint**: ✅ Implemented (`/api/news/assess` in `src/control_plane/api.py`)
- **Settings**: ✅ Configured (`src/core/settings.py`)
- **Secrets Script**: ✅ Updated (`deploy/gcp/secrets_to_env.sh`)

### ❌ Keys Status
- **GCP Secret Manager**: ❌ No AI secrets found (`ai-quant-openai-api-key`, `ai-quant-google-api-key`, `ai-quant-gemini-api-key` not found)
- **VM .env file**: ❓ Not readable (permission denied) - may or may not have keys
- **Local env**: ❌ No keys set (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY` not set)

### ⚠️ Configuration Status
- **AI_INSIGHTS_ENABLED**: ❌ `False` (needs to be `"1"`)
- **Systemd Service**: Uses `/etc/ai-quant/.env` file (NOT `secrets_to_env.sh`)

---

## What Works NOW

1. **Code**: All AI insights code exists and is ready
2. **Backend**: `get_ai_insight()` function works if keys are provided
3. **API**: `/api/news/assess` endpoint exists and calls AI insights
4. **Settings**: Code reads `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY` from env vars
5. **Secrets Script**: `deploy/gcp/secrets_to_env.sh` updated to load AI keys (if secrets exist)

---

## What's MISSING

1. **Keys in GCP Secret Manager**: Secrets don't exist yet
2. **Keys in VM .env file**: File exists but not readable (may or may not have keys)
3. **AI_INSIGHTS_ENABLED**: Not set to `"1"` (defaults to `False`)

---

## Options to Enable AI Insights

### Option 1: Use GCP Secret Manager (Recommended)

**Step 1**: Create secrets in GCP Secret Manager:
```bash
# Create OpenAI secret
gcloud secrets create ai-quant-openai-api-key \
  --project=fxg-ai-trading \
  --replication-policy=automatic

echo -n "YOUR_OPENAI_API_KEY" | \
  gcloud secrets versions add ai-quant-openai-api-key \
  --data-file=- \
  --project=fxg-ai-trading

# Create Google/Gemini secret
gcloud secrets create ai-quant-google-api-key \
  --project=fxg-ai-trading \
  --replication-policy=automatic

echo -n "YOUR_GOOGLE_API_KEY" | \
  gcloud secrets versions add ai-quant-google-api-key \
  --data-file=- \
  --project=fxg-ai-trading
```

**Step 2**: Update systemd service to use `secrets_to_env.sh`:
- Current: Uses `EnvironmentFile=/etc/ai-quant/.env`
- Needed: Use `secrets_to_env.sh` script OR update `.env` file to load secrets

**Step 3**: Enable AI_INSIGHTS_ENABLED:
- Add to `.env` file: `AI_INSIGHTS_ENABLED=1`
- OR set in `secrets_to_env.sh` (auto-enabled if keys present)

### Option 2: Use VM .env File (Simpler)

**Step 1**: SSH to VM and edit `.env` file:
```bash
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading

sudo nano /etc/ai-quant/.env
```

**Step 2**: Add keys to `.env` file:
```bash
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
GEMINI_API_KEY=your_gemini_key_here  # Alternative to GOOGLE_API_KEY
AI_INSIGHTS_ENABLED=1
AI_INSIGHTS_MODE=advisory
AI_PROVIDER=openai  # or "gemini" if only Google key
```

**Step 3**: Restart service:
```bash
sudo systemctl restart ai-quant-control-plane
sudo systemctl status ai-quant-control-plane
```

---

## Verification Commands

### Check if keys are loaded (on VM):
```bash
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading \
  --command="sudo systemctl show ai-quant-control-plane | grep -E 'OPENAI|GOOGLE|AI_INSIGHTS' | sed 's/=.*/=***/'"
```

### Check service logs:
```bash
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading \
  --command="sudo journalctl -u ai-quant-control-plane -n 100 | grep -E 'AI_INSIGHTS|OPENAI|GOOGLE'"
```

### Test API endpoint:
```bash
curl http://127.0.0.1:8080/api/news/assess
```

---

## Files Changed

1. **`deploy/gcp/secrets_to_env.sh`**: Updated to load AI keys from secrets
2. **`templates/dashboard_advanced.html`**: Fixed calendar synthetic fallback (already done)

---

## Calendar Fix (Already Complete)

✅ **Calendar synthetic fallback fixed** in `templates/dashboard_advanced.html`:
- Removed fake countdown event creation
- Shows explicit "⚠️ Economic Calendar Not Configured" message
- No placeholder data (per workspace rules)

---

## Next Steps

1. **User Action Required**: Add keys to GCP Secret Manager OR VM `.env` file
2. **Enable AI_INSIGHTS_ENABLED**: Set to `"1"` in environment
3. **Restart Service**: Restart control plane service
4. **Verify**: Test `/api/news/assess` endpoint
5. **Document**: Update status docs with verification results

---

## Evidence

- **Code**: `src/ai/ai_insights.py` (exists, ready)
- **API**: `src/control_plane/api.py:1915-2011` (endpoint exists)
- **Settings**: `src/core/settings.py:114-122` (reads env vars)
- **Secrets Script**: `deploy/gcp/secrets_to_env.sh` (updated)
- **Secrets Check**: No AI secrets found in GCP Secret Manager
- **VM .env**: File exists but not readable (permission denied)
- **Local Test**: Keys not set locally

---

**Status**: ✅ CODE READY, ⚠️ KEYS REQUIRED  
**Next Owner**: Add keys to secrets OR VM .env file → User
