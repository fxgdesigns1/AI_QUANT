# AI Insights Setup Required

**Date**: 2026-01-13T02:00:00Z  
**Status**: Code Ready, Secrets Required  
**System**: ALPHA

## Summary

AI Insights code exists and is ready. **Keys must be created in GCP Secret Manager** for it to work.

---

## Secrets Required

Create the following secrets in GCP Secret Manager (project: `fxg-ai-trading`):

### Option 1: OpenAI Only
```bash
gcloud secrets create ai-quant-openai-api-key --project=fxg-ai-trading --replication-policy=automatic
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets versions add ai-quant-openai-api-key --data-file=- --project=fxg-ai-trading
```

### Option 2: Gemini/Google Only
```bash
gcloud secrets create ai-quant-google-api-key --project=fxg-ai-trading --replication-policy=automatic
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets versions add ai-quant-google-api-key --data-file=- --project=fxg-ai-trading
```

**OR** (alternative name):
```bash
gcloud secrets create ai-quant-gemini-api-key --project=fxg-ai-trading --replication-policy=automatic
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets versions add ai-quant-gemini-api-key --data-file=- --project=fxg-ai-trading
```

### Option 3: Both (Recommended)
Create both secrets above. The system will use OpenAI by default, with Gemini as fallback.

---

## Code Changes Applied

**File**: `deploy/gcp/secrets_to_env.sh`

**Changes**:
1. Added `OPENAI_API_KEY` loading from `ai-quant-openai-api-key` secret
2. Added `GOOGLE_API_KEY` / `GEMINI_API_KEY` loading from `ai-quant-google-api-key` or `ai-quant-gemini-api-key` secrets
3. Auto-enable `AI_INSIGHTS_ENABLED=1` if at least one key is present
4. Set default provider (`openai` or `gemini` based on available keys)

**Behavior**:
- **Fail-soft**: AI keys are optional (won't break startup if missing)
- **Auto-enable**: `AI_INSIGHTS_ENABLED=1` is set automatically if keys are present
- **Provider selection**: Uses OpenAI if both are present, otherwise uses available key

---

## Verification Steps

### 1. Create Secrets (if not already done)
```bash
# Check if secrets exist
gcloud secrets list --project=fxg-ai-trading | grep -E "openai|google|gemini"

# Create if missing (use one of the options above)
```

### 2. Update VM (if using secrets_to_env.sh)
If your systemd service uses `secrets_to_env.sh`, push updated script:
```bash
# Push updated secrets_to_env.sh to VM
gcloud compute scp deploy/gcp/secrets_to_env.sh \
  fxg-quant-paper-e2-micro:/opt/ai-quant/deploy/gcp/secrets_to_env.sh \
  --zone=us-east1-b --project=fxg-ai-trading
```

### 3. OR: Update .env File (if using EnvironmentFile)
If your systemd service uses `/etc/ai-quant/.env` file, add:
```bash
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
AI_INSIGHTS_ENABLED=1
AI_INSIGHTS_MODE=advisory
AI_PROVIDER=openai
```

### 4. Restart Service
```bash
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading \
  --command="sudo systemctl restart ai-quant-control-plane"
```

### 5. Verify
```bash
# Check env vars are loaded
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading \
  --command="sudo systemctl show ai-quant-control-plane | grep -E 'OPENAI|GOOGLE|AI_INSIGHTS'"

# Check logs
gcloud compute ssh --zone=us-east1-b fxg-quant-paper-e2-micro --project=fxg-ai-trading \
  --command="sudo journalctl -u ai-quant-control-plane -n 50 | grep -E 'AI_INSIGHTS|OPENAI|GOOGLE'"
```

### 6. Test API Endpoint
```bash
# Test /api/news/assess endpoint (uses AI insights)
curl http://127.0.0.1:8080/api/news/assess
```

---

## Current Status

✅ **Code Ready**: `deploy/gcp/secrets_to_env.sh` updated to load AI keys  
❌ **Secrets Missing**: Secrets not found in GCP Secret Manager  
⚠️ **Service**: Systemd service uses `/etc/ai-quant/.env` (not `secrets_to_env.sh`)  

**Action Required**: 
1. Create secrets in GCP Secret Manager (see above)
2. OR update `/etc/ai-quant/.env` on VM with keys
3. Enable `AI_INSIGHTS_ENABLED=1`
4. Restart service

---

## Endpoints Using AI Insights

1. **`/api/news/assess`**: Uses `get_ai_insight()` to analyze news sentiment
2. **Future**: Other endpoints can use `get_ai_insight()` from `src.ai.ai_insights`

---

## Evidence

- **Code**: `deploy/gcp/secrets_to_env.sh` (updated)
- **Backend**: `src/ai/ai_insights.py` (exists, requires keys)
- **API**: `src/control_plane/api.py:1915-2011` (`/api/news/assess` endpoint)
- **Settings**: `src/core/settings.py:114-122` (AI insights config)

---

**Next Owner**: Create secrets in GCP Secret Manager OR update VM .env file → User
