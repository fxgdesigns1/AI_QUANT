# Auth-Free Tunnel Setup Runbook

**Date**: 2026-01-22  
**Phase**: ALPHA  
**Objective**: Create auth-free tunnel to ALPHA dashboard, wire Playwright, and verify end-to-end truthfulness

---

## Prerequisites

- Access to GCP VM: `fxg-quant-paper-e2-micro`
- Cloudflare account with Zero Trust (free tier supports tunnels)
- Domain managed by Cloudflare (or use `.internal` for private DNS)
- Dashboard running on VM port `8787`

---

## Step 1: Install Cloudflare Tunnel on VM

**SSH to VM:**
```bash
gcloud compute ssh fxg-quant-paper-e2-micro --zone us-east1-b --project fxg-ai-trading
```

**On VM, install cloudflared:**
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
cloudflared --version
```

**Expected Output:**
```
cloudflared version 2024.x.x
```

---

## Step 2: Authenticate Cloudflare Tunnel

**On VM, authenticate (one-time, opens browser):**
```bash
cloudflared tunnel login
```

**Expected:**
- Browser opens to Cloudflare login
- After login, certificate saved to `~/.cloudflared/cert.pem`

---

## Step 3: Create Tunnel

**On VM:**
```bash
cloudflared tunnel create fxg-alpha-dashboard
```

**Expected Output:**
```
Created tunnel fxg-alpha-dashboard with id <TUNNEL_UUID>
```

**Record the Tunnel UUID** (you'll need it for config).

---

## Step 4: Configure Tunnel

**On VM, create config directory:**
```bash
sudo mkdir -p /etc/cloudflared
sudo chmod 700 /etc/cloudflared
```

**Copy credentials:**
```bash
sudo cp ~/.cloudflared/<TUNNEL_UUID>.json /etc/cloudflared/credentials.json
sudo chmod 600 /etc/cloudflared/credentials.json
```

**Create config file:**
```bash
sudo tee /etc/cloudflared/config.yml <<EOF
tunnel: <TUNNEL_UUID>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: alpha-dashboard.fxg.internal
    service: http://127.0.0.1:8787
  - service: http_status:404
EOF
```

**Replace `<TUNNEL_UUID>` with the actual UUID from Step 3.**

---

## Step 5: Bind DNS (Optional - for .internal domains)

**For `.internal` domains, you may need:**
- WARP client on your local machine, OR
- Use a real domain managed by Cloudflare

**If using real domain:**
```bash
cloudflared tunnel route dns fxg-alpha-dashboard alpha-dashboard.yourdomain.com
```

**If using `.internal` (private DNS):**
- Ensure your network/DNS resolver can resolve `.internal` domains
- Or use WARP client to access private networks

---

## Step 6: Install and Start Service

**On VM:**
```bash
sudo cloudflared service install
sudo systemctl daemon-reload
sudo systemctl restart cloudflared
sudo systemctl enable cloudflared
```

**Verify service:**
```bash
sudo systemctl status cloudflared
```

**Expected:**
```
Active: active (running)
```

**Check logs:**
```bash
sudo journalctl -u cloudflared -f
```

**Expected:**
```
Connection established
```

---

## Step 7: Verify Tunnel

**From local machine (with WARP or DNS configured):**
```bash
curl -I https://alpha-dashboard.fxg.internal
```

**Expected:**
```
HTTP/2 200
```

**Or open in browser:**
```
https://alpha-dashboard.fxg.internal
```

**Expected:**
- Dashboard loads without Google OAuth redirect
- No login prompt
- Dashboard displays with data from truth sources

---

## Step 8: Update Playwright Configuration

**Local machine, verify `playwright.config.js`:**
```javascript
baseURL: process.env.DASHBOARD_URL || 'https://alpha-dashboard.fxg.internal',
```

**Set environment variable (optional):**
```bash
export DASHBOARD_URL=https://alpha-dashboard.fxg.internal
```

---

## Step 9: Run Playwright Tests

**Local machine:**
```bash
cd "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
npm run test:playwright
# or
npx playwright test tests/dashboard/dashboard_truth.spec.ts
```

**Expected:**
- All tests pass
- No auth redirects detected
- All network requests go to backend only
- Missing/stale indicators work correctly

---

## Step 10: Verify Dashboard Truth Sources

**On VM, verify truth files exist:**
```bash
ls -la runtime/status_snapshot.json
ls -la runtime/strategy_readiness.json
ls -la logs/runner.log
```

**Check dashboard reflects truth:**
- Visit `https://alpha-dashboard.fxg.internal`
- Verify execution_enabled matches `runtime/status_snapshot.json`
- Verify missing fields show `MISSING`
- Verify embargo state displays verbatim

---

## Troubleshooting

### Tunnel Not Connecting

**Check service status:**
```bash
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -n 50
```

**Common issues:**
- Credentials file path incorrect
- Tunnel UUID mismatch
- Port 8787 not accessible on localhost

### DNS Resolution Fails

**For `.internal` domains:**
- Install WARP client: https://developers.cloudflare.com/cloudflare-one/connections/connect-devices/warp/
- Or use a real domain managed by Cloudflare

**For real domains:**
- Ensure domain DNS is managed by Cloudflare
- Run: `cloudflared tunnel route dns fxg-alpha-dashboard <hostname>`

### Auth Redirect Still Occurs

**Check:**
- Tunnel config doesn't include Cloudflare Access rules
- Dashboard service doesn't have auth middleware enabled
- Browser cache cleared

### Playwright Tests Fail

**Check:**
- Tunnel URL accessible: `curl https://alpha-dashboard.fxg.internal`
- No firewall blocking tunnel
- DNS resolves correctly
- Set `DASHBOARD_URL` environment variable

---

## Verification Checklist

- [ ] `cloudflared` installed and authenticated
- [ ] Tunnel created: `fxg-alpha-dashboard`
- [ ] Config file created at `/etc/cloudflared/config.yml`
- [ ] Service running: `systemctl status cloudflared`
- [ ] Dashboard accessible: `curl https://alpha-dashboard.fxg.internal`
- [ ] No auth redirect in browser
- [ ] Playwright tests pass
- [ ] Dashboard shows truth sources only
- [ ] Missing fields show `MISSING`
- [ ] Stale data shows `STALE`
- [ ] No external API requests detected

---

## Security Notes

⚠️ **WARNING**: This tunnel is **auth-free** for Playwright testing only.

**For production:**
- Enable Cloudflare Access with Google OAuth
- Add IP allowlist if needed
- Use service tokens for automated access
- Monitor tunnel logs for unauthorized access

**Current setup:**
- Publicly accessible via tunnel URL
- No authentication required
- Suitable for testing only

---

## Quick Reference

**Tunnel Management:**
```bash
# List tunnels
cloudflared tunnel list

# Delete tunnel
cloudflared tunnel delete fxg-alpha-dashboard

# View tunnel info
cloudflared tunnel info fxg-alpha-dashboard
```

**Service Management:**
```bash
# Start
sudo systemctl start cloudflared

# Stop
sudo systemctl stop cloudflared

# Restart
sudo systemctl restart cloudflared

# View logs
sudo journalctl -u cloudflared -f
```

---

**Status**: ✅ **READY FOR EXECUTION**
