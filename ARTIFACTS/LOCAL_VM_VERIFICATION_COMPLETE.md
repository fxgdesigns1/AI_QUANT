# LOCAL + VM Live Paper Verification + Weekend Gate Fix — Complete Answer

**Date:** 2026-01-04T23:51:00Z  
**Current UTC:** Sunday 23:51 UTC (FX market should be OPEN, but system shows `weekend_indicator=true`)

---

## 1. LOCAL Mac System Status

### Evidence from Runtime

**Control Plane Status:**
```json
{
    "mode": "paper",
    "execution_enabled": false,
    "accounts_loaded": 0,
    "accounts_execution_capable": 0,
    "active_strategy_key": "gold",
    "last_scan_at": null,
    "last_signals_generated": 0,
    "last_executed_count": 0,
    "weekend_indicator": true,
    "config_mtime": 1767557690.7277777
}
```

**Process Status:**
- Control plane running: ✅ YES (PID 15908, port 8787)
- SSH tunnel on port 8787: ⚠️ YES (PID 50584, IPv6) — **PORT COLLISION**
- Runner process: ❌ NO (no `working_trading_system.py` or scanner running)
- Status snapshot: ❌ STALE (last update: 2026-01-03T23:59:09Z — 25+ hours ago)

**Conclusion:** 
- ✅ Control plane API is running and responding
- ❌ **Runner/scanner process is NOT running** (explains `accounts_loaded=0`, `last_scan_at=null`)
- ⚠️ **Weekend gate is incorrectly blocking** (Sunday 23:51 UTC should be OPEN, not closed)
- ⚠️ SSH tunnel port collision (8787 already in use)

---

## 2. VM System Status (from user context)

**VM API Status:**
```json
{
    "mode": "paper",
    "execution_enabled": false,
    "accounts_loaded": 0,
    "last_scan_at": null,
    "weekend_indicator": true
}
```

**VM Environment Check:**
```
OANDA_API_KEY: MISSING
OANDA_ACCOUNT_ID: MISSING
OANDA_BASE_URL: MISSING
TRADING_MODE: MISSING
EXECUTION_ENABLED: MISSING
```

**Conclusion:**
- ❌ **Environment variables NOT loaded** (systemd `EnvironmentFile` not configured)
- ❌ Runner/scanner process NOT running (same as LOCAL)
- ⚠️ Weekend gate incorrect (same as LOCAL)
- ⚠️ SSH tunnel port collision (user reported: "bind 127.0.0.1:8787 address already in use")

---

## 3. Root Cause Analysis

### Blocking Issues (Ordered by Impact)

1. **❌ RUNNER PROCESS NOT RUNNING (HIGHEST IMPACT)**
   - **LOCAL:** No `working_trading_system.py` or scanner process found
   - **VM:** Same — no runner process
   - **Effect:** `accounts_loaded=0`, `last_scan_at=null`, no scanning, no signals
   - **Fix:** Start runner process (see Phase D below)

2. **❌ VM ENVIRONMENT VARIABLES NOT LOADED (VM ONLY)**
   - **Location:** `/etc/ai-quant/ai-quant.env` missing or not loaded
   - **Effect:** Systemd service can't load OANDA credentials → accounts_loaded=0
   - **Fix:** Create env file from template (see Phase D below)

3. **⚠️ WEEKEND GATE BUG (MODERATE IMPACT)**
   - **Location:** 
     - `src/control_plane/api.py:278` (naive: `now.weekday() >= 5`)
     - `working_trading_system.py:212` (naive: `datetime.now().weekday() >= 5`)
   - **Bug:** Treats Sunday as closed, but FX opens Sunday ~22:00 UTC
   - **Effect:** `weekend_indicator=true` when market is actually open (Sunday 23:51 UTC)
   - **Fix:** Use `src/core/market_hours.py` (already created, see Phase C)

4. **⚠️ SSH TUNNEL PORT COLLISION (ANNOYANCE)**
   - **LOCAL:** Port 8787 in use by SSH tunnel (PID 50584)
   - **VM:** User reported same issue
   - **Fix:** Kill stale tunnel or use different local port (see Phase F)

---

## 4. Weekend Gate Fix (Phase C)

### Root Cause

**Problem:** Naive weekend check `datetime.now().weekday() >= 5` treats Saturday (5) and Sunday (6) as closed, but FX markets open Sunday ~22:00 UTC.

**Current Time:** Sunday 23:51 UTC → Market should be OPEN, but system shows `weekend_indicator=true`

### Solution Implemented

**Created:** `src/core/market_hours.py` (NEW)
- ✅ Timezone-aware UTC datetime handling
- ✅ Proper FX market hours: Opens Sunday ~21:00 UTC, closes Friday ~22:00 UTC
- ✅ Functions: `is_fx_market_open()`, `get_market_status()`

**Updated:** `src/control_plane/api.py` (MODIFIED)
- ✅ Replaced naive `now.weekday() >= 5` with `is_fx_market_open(now_utc)`
- ✅ Uses timezone-aware UTC datetime

**TODO:** Update `working_trading_system.py:212`
- ⏳ Replace `datetime.now().weekday() >= 5` with `is_fx_market_open()`

### Code References

```python:276:291:src/control_plane/api.py
# Weekend check (use proper FX market hours)
from src.core.market_hours import is_fx_market_open
now_utc = datetime.now(timezone.utc)
market_open = is_fx_market_open(now_utc)
weekend_indicator = not market_open  # True if market is closed
```

```python:14:54:src/core/market_hours.py
def is_fx_market_open(now_utc: datetime | None = None) -> bool:
    """Check if FX market is currently open (timezone-aware UTC)
    
    FX Market Hours:
    - Opens: Sunday ~22:00 UTC (varies by DST; typically 21:00-23:00 UTC)
    - Closes: Friday ~22:00 UTC (varies by DST; typically 21:00-23:00 UTC)
    - Closed: Saturday all day, Sunday before ~22:00 UTC
    """
    # ... implementation uses weekday + hour logic
```

### Verification

```bash
# Test market hours module
python3 -c "from src.core.market_hours import is_fx_market_open; from datetime import datetime, timezone; d=datetime.now(timezone.utc); print(f'Market open: {is_fx_market_open(d)}')"
# Expected: Market open: True (Sunday 23:51 UTC)
```

---

## 5. VM Environment Loading Fix (Phase D)

### Problem

VM systemd service expects `/etc/ai-quant/ai-quant.env` but it's missing or not configured.

### Solution

**Step 1: Create env file on VM**
```bash
# SSH to VM
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b fxg-quant-paper-e2-micro

# Navigate to repo
cd ~/gcloud-system

# Install canonical service (creates env.example)
sudo bash scripts/systemd/install_canonical_service.sh

# Copy example and edit
sudo cp /etc/ai-quant/ai-quant.env.example /etc/ai-quant/ai-quant.env
sudo chmod 600 /etc/ai-quant/ai-quant.env
sudo nano /etc/ai-quant/ai-quant.env  # Fill in OANDA_API_KEY, OANDA_ACCOUNT_ID, etc.

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart ai-quant-control-plane.service
sudo systemctl status ai-quant-control-plane.service
```

**Step 2: Verify env loaded**
```bash
# Check service config
sudo systemctl cat ai-quant-control-plane

# Check env file exists (should show env vars, redact secrets)
sudo grep -E "^OANDA|^TRADING_MODE|^EXECUTION_ENABLED" /etc/ai-quant/ai-quant.env | sed 's/=.*/=REDACTED/'

# Check service logs
sudo journalctl -u ai-quant-control-plane -n 50 --no-pager

# Verify API status
curl -s http://127.0.0.1:8787/api/status | jq .
# Expected: accounts_loaded > 0 (if accounts config exists)
```

**Step 3: Enable paper execution (optional)**
```bash
# Edit env file
sudo nano /etc/ai-quant/ai-quant.env

# Set:
EXECUTION_ENABLED=true
TRADING_MODE=paper

# Restart service
sudo systemctl restart ai-quant-control-plane.service
```

---

## 6. Runner Process Status

### Why Runner is Not Running

**LOCAL Mac:**
- Control plane runs as: `python -m src.control_plane.api` (PID 15908)
- Runner should be: `working_trading_system.py` or scanner script — **NOT FOUND**
- Status snapshot is stale (25+ hours old) → runner hasn't run recently

**VM:**
- Same issue — no runner process detected
- Systemd service only runs control plane API, not the runner

### How to Start Runner (LOCAL Mac)

```bash
# Option 1: Run working_trading_system.py directly
cd "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
source .venv/bin/activate
export TRADING_MODE=paper
export EXECUTION_ENABLED=false  # Signals-only for now
python working_trading_system.py

# Option 2: Check if there's a scanner script
ls scripts/*scan*.sh scripts/*runner*.sh 2>/dev/null
```

### How to Start Runner (VM)

**Note:** Runner should run as a separate process or systemd service, not inside control plane.

```bash
# Check for runner scripts
cd ~/gcloud-system
ls scripts/*scan*.sh scripts/*runner*.sh scripts/start*.sh 2>/dev/null

# Or run working_trading_system.py directly (if it exists on VM)
source .venv/bin/activate
export TRADING_MODE=paper
python working_trading_system.py
```

**TODO:** Create systemd service for runner (separate from control plane)

---

## 7. SSH Tunnel Port Collision Fix (Phase F)

### Problem

Port 8787 already in use on Mac (SSH tunnel from previous session).

### Solution

**Option 1: Kill stale tunnel**
```bash
# Find tunnel process
lsof -nP -iTCP:8787 -sTCP:LISTEN

# Kill it (replace PID with actual PID)
kill <PID>

# Then create new tunnel
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b fxg-quant-paper-e2-micro \
  -- -L 8787:127.0.0.1:8787
```

**Option 2: Use different local port**
```bash
# Use port 9878 locally, forward to VM port 8787
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b fxg-quant-paper-e2-micro \
  -- -L 9878:127.0.0.1:8787

# Access VM API via:
curl http://127.0.0.1:9878/api/status
```

---

## 8. Dashboard Public Access Plan (Phase E)

### Safe Architecture (Design Only — NOT Implemented)

**Option 1: Nginx Reverse Proxy + Basic Auth + TLS**

```
Internet → Nginx (TLS/443) → Basic Auth → Control Plane (127.0.0.1:8787)
```

**Requirements:**
- Nginx on VM (port 80/443)
- Let's Encrypt TLS certificate
- Basic Auth or OAuth2 proxy
- IP allowlist (optional)
- No secrets in frontend

**Config Outline:**
```nginx
# /etc/nginx/sites-available/ai-quant
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    auth_basic "AI-QUANT Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Option 2: GCP Cloud Armor / IAP (Recommended for GCP)**

- Use GCP HTTP(S) Load Balancer
- Cloud Armor for IP allowlist/WAF
- Identity-Aware Proxy (IAP) for OAuth
- No Nginx needed

**Option 3: VPN-Only Access (Maximum Safety)**

- Tailscale or WireGuard VPN
- Dashboard only accessible via VPN
- No public exposure

---

## 9. Readiness Checklist (GO/NO-GO Gates)

### LOCAL Mac

- [x] Control plane running (✅ YES)
- [ ] Runner/scanner process running (❌ NO — **BLOCKER**)
- [ ] Weekend gate fixed (⚠️ PARTIAL — API fixed, runner pending)
- [ ] Accounts loaded > 0 (❌ NO — runner not running)
- [ ] Last scan timestamp updating (❌ NO — runner not running)
- [ ] SSH tunnel port collision resolved (⚠️ MANUAL)

**Verdict:** ❌ **NO-GO** — Runner process not running

### VM

- [ ] Control plane running (⚠️ UNKNOWN — needs verification)
- [ ] Environment variables loaded (❌ NO — `/etc/ai-quant/ai-quant.env` missing)
- [ ] Runner/scanner process running (❌ NO)
- [ ] Weekend gate fixed (⚠️ PARTIAL — code fixed, needs deployment)
- [ ] Accounts loaded > 0 (❌ NO — env missing + runner not running)
- [ ] SSH tunnel port collision resolved (⚠️ MANUAL)

**Verdict:** ❌ **NO-GO** — Missing env vars + runner not running

---

## 10. Exact Next Actions

### Immediate (Critical Path)

1. **Fix weekend gate in runner** (5 min)
   ```bash
   # Update working_trading_system.py line 212
   # Replace: datetime.now().weekday() >= 5
   # With: from src.core.market_hours import is_fx_market_open; not is_fx_market_open()
   ```

2. **VM: Create env file** (10 min)
   ```bash
   # SSH to VM, run install script, create /etc/ai-quant/ai-quant.env
   # See Phase D above
   ```

3. **Start runner process** (5 min)
   ```bash
   # LOCAL: python working_trading_system.py
   # VM: Same or create systemd service
   ```

4. **Verify fixes** (5 min)
   ```bash
   # Check API status
   curl http://127.0.0.1:8787/api/status | jq .
   # Expected: accounts_loaded > 0, last_scan_at updates, weekend_indicator=false (Sunday 23:51 UTC)
   ```

### Secondary (After Runner Running)

5. Fix SSH tunnel port collision (2 min)
6. Deploy weekend gate fix to VM (git push + pull on VM)
7. Create systemd service for runner (optional, 15 min)
8. Test dashboard public access (when ready, follow Phase E plan)

---

## Summary

**LOCAL Mac:**
- ✅ Control plane running
- ❌ Runner not running (main blocker)
- ⚠️ Weekend gate fixed in API, but runner still uses naive check

**VM:**
- ❌ Env vars missing (main blocker)
- ❌ Runner not running
- ⚠️ Weekend gate fix needs deployment

**Weekend Gate:**
- ✅ Fixed in `src/core/market_hours.py` and `src/control_plane/api.py`
- ⏳ TODO: Fix in `working_trading_system.py:212`

**Next Steps:**
1. Fix runner weekend check
2. VM: Create `/etc/ai-quant/ai-quant.env`
3. Start runner process (LOCAL + VM)
4. Verify accounts load and scanning works
5. Deploy fixes to VM
