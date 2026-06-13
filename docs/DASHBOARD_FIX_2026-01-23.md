# Dashboard Fix - January 23, 2026

## Problem
Dashboard at `alpha.fxgdesigns.co.uk` was showing `{"detail":"Not Found"}` (404 error).

## Root Cause Analysis

### Issues Identified:
1. **Dashboard Root Endpoint**: The React dashboard build may not be properly mounted or deployed on the VM
2. **Cloudflare Tunnel Configuration**: Tunnel may not be configured for `alpha.fxgdesigns.co.uk` domain
3. **Cloudflare Access**: Domain returns 302 redirect, indicating Cloudflare Access is blocking requests

### Verification Results:
- ✅ Control plane API is running on VM (port 8787)
- ✅ Health endpoint accessible: `/health` returns 200
- ✅ Status endpoint accessible: `/api/status` returns 200
- ❌ Dashboard root (`/`) returns 404 or connection error
- ⚠️  Domain `alpha.fxgdesigns.co.uk` returns 302 (Cloudflare Access redirect)

## Solution Implemented

### 1. Created Fix Scripts

**`scripts/fix_dashboard_tunnel.sh`**
- Comprehensive diagnostic and fix script
- Checks VM service status
- Sets up local IAP tunnel
- Tests all endpoints
- Runs Playwright verification

**`scripts/complete_dashboard_fix.sh`**
- Complete end-to-end fix
- Deploys React build to VM if missing
- Sets up local tunnel
- Tests all endpoints
- Runs Playwright tests
- Checks Cloudflare tunnel status

**`scripts/fix_cloudflare_tunnel_domain.sh`**
- Fixes Cloudflare tunnel configuration
- Updates tunnel to use `alpha.fxgdesigns.co.uk`
- Verifies React build deployment

### 2. Created Playwright Test

**`tests/dashboard/dashboard_accessibility.spec.ts`**
- Tests dashboard root accessibility
- Verifies health and status endpoints
- Confirms React app is served (not 404)

### 3. Immediate Access Solution

**Local IAP Tunnel** (Working):
```bash
bash scripts/quick_tunnel.sh
# Or
bash scripts/complete_dashboard_fix.sh
```

Dashboard accessible at: `http://127.0.0.1:28787`

## Fix Steps

### Step 1: Verify Local Access
```bash
# Start local tunnel
bash scripts/complete_dashboard_fix.sh

# Or manually:
gcloud compute ssh fxg-quant-paper-e2-micro \
  --zone us-east1-b \
  --project fxg-ai-trading \
  --tunnel-through-iap \
  -- -N -L 28787:127.0.0.1:8787
```

Then open: `http://127.0.0.1:28787`

### Step 2: Deploy React Build (if needed)
The script automatically deploys the React build if it's missing on the VM.

Manual deployment:
```bash
# Build locally
cd frontend/fxg-dashboard
npm run build

# Deploy to VM
gcloud compute scp --recurse \
  --zone us-east1-b \
  --project fxg-ai-trading \
  --tunnel-through-iap \
  dist/ \
  fxg-quant-paper-e2-micro:~/gcloud-system/frontend/fxg-dashboard/dist
```

### Step 3: Fix Cloudflare Tunnel (for public access)

**On VM:**
```bash
# SSH to VM
gcloud compute ssh fxg-quant-paper-e2-micro \
  --zone us-east1-b \
  --project fxg-ai-trading

# Check tunnel config
sudo cat /etc/cloudflared/config.yml

# Update config to include alpha.fxgdesigns.co.uk
sudo nano /etc/cloudflared/config.yml
```

Config should include:
```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: alpha.fxgdesigns.co.uk
    service: http://127.0.0.1:8787
  - hostname: alpha-dashboard.fxg.internal
    service: http://127.0.0.1:8787
  - service: http_status:404
```

Then:
```bash
# Restart tunnel
sudo systemctl restart cloudflared

# Route DNS
cloudflared tunnel route dns fxg-alpha-dashboard alpha.fxgdesigns.co.uk
```

### Step 4: Fix Cloudflare Access (if blocking)

**Option A: Disable Access Temporarily**
1. Go to Cloudflare Dashboard → Zero Trust → Access → Applications
2. Find `alpha.fxgdesigns.co.uk`
3. Toggle "Enabled" OFF
4. Save

**Option B: Add Bypass Rule**
1. Go to Zero Trust → Access → Applications → `alpha.fxgdesigns.co.uk`
2. Go to Policies tab
3. Add new policy:
   - Policy name: "Bypass All"
   - Action: Allow
   - Include: Everyone
   - Save
4. Make this policy FIRST (top priority)

## Verification

### Local Access
```bash
# Test health
curl http://127.0.0.1:28787/health

# Test status
curl http://127.0.0.1:28787/api/status

# Test root
curl -I http://127.0.0.1:28787/
```

### Playwright Tests
```bash
export DASHBOARD_URL="http://127.0.0.1:28787"
npx playwright test tests/dashboard/dashboard_accessibility.spec.ts
```

### Public Domain
```bash
# Test domain
curl -I https://alpha.fxgdesigns.co.uk/health
```

## Files Created/Modified

### New Scripts:
- `scripts/fix_dashboard_tunnel.sh` - Diagnostic and fix script
- `scripts/complete_dashboard_fix.sh` - Complete fix automation
- `scripts/fix_cloudflare_tunnel_domain.sh` - Tunnel domain fix

### New Tests:
- `tests/dashboard/dashboard_accessibility.spec.ts` - Playwright accessibility tests

### Documentation:
- `docs/DASHBOARD_FIX_2026-01-23.md` - This document

## Status

### ✅ FIXED - Dashboard is Working!

**Verification:**
- ✅ Dashboard root returns HTTP 200
- ✅ React app loads correctly
- ✅ Page title: "AI-QUANT | TOTAL COMMAND"
- ✅ All UI components rendering
- ✅ API version endpoint confirms React build found
- ✅ System status showing all components UP

**Root Cause:**
The React build was deployed to `~/gcloud-system/frontend/fxg-dashboard/dist` but the systemd service runs from `/opt/ai-quant/`, so it was looking for the build at `/opt/ai-quant/frontend/fxg-dashboard/dist`.

**Fix Applied:**
1. Deployed React build to `/opt/ai-quant/frontend/fxg-dashboard/dist`
2. Restarted systemd service: `sudo systemctl restart ai-quant-control-plane`
3. Verified dashboard is accessible

### ✅ Completed:
- [x] Local IAP tunnel setup script
- [x] React build deployment to correct location
- [x] Systemd service restart
- [x] Dashboard root endpoint fixed
- [x] Playwright test suite
- [x] Comprehensive fix scripts
- [x] Documentation

### ⚠️  Requires Manual Action (for public access):
- [ ] Cloudflare tunnel configuration update (if public access needed)
- [ ] Cloudflare Access bypass (if domain access needed)

## Quick Reference

**Immediate Access:**
```bash
bash scripts/complete_dashboard_fix.sh
# Opens: http://127.0.0.1:28787
```

**Public Access:**
1. Update Cloudflare tunnel config on VM
2. Route DNS: `cloudflared tunnel route dns fxg-alpha-dashboard alpha.fxgdesigns.co.uk`
3. Fix Cloudflare Access (disable or add bypass)

**Verification:**
```bash
# Run Playwright tests
export DASHBOARD_URL="http://127.0.0.1:28787"
npx playwright test tests/dashboard/dashboard_accessibility.spec.ts
```

## Next Steps

1. **Immediate**: Use local tunnel (`http://127.0.0.1:28787`) - already working
2. **Short-term**: Deploy React build to VM if missing
3. **Long-term**: Configure Cloudflare tunnel for public access with proper security

---

**Status**: ✅ **FIXED** - Local access working via IAP tunnel  
**Public Access**: ⚠️  Requires Cloudflare tunnel configuration update
