# Cloud Deployment Full Stack (GCP VM)

**Purpose:** Deploy AI_QUANT Control Plane + Runner on GCP VM with systemd services.

---

## Prerequisites

- GCP VM running Ubuntu/Debian
- SSH access to VM
- Repository copied to VM (or cloned)
- OANDA credentials configured

---

## Quick Deploy (One Command)

**On the VM:**

```bash
cd ~/gcloud-system
bash scripts/vm_bootstrap_deploy_verify.sh
```

This script:
1. Installs prerequisites (python3, venv, pip, git, curl, jq, lsof, ripgrep)
2. Sets up virtual environment
3. Installs dependencies
4. Starts control plane and runner in background
5. Verifies both services are running
6. Checks accounts loaded, live prices, Telegram

---

## Manual Deployment (Step-by-Step)

### Step 1: Install Prerequisites

```bash
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl jq lsof ripgrep
```

### Step 2: Setup Repository

```bash
cd ~/gcloud-system
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit with your credentials
nano .env

# Ensure .env has:
# - OANDA_API_KEY
# - OANDA_ACCOUNT_ID
# - OANDA_BASE_URL (optional, defaults to practice)
# - TELEGRAM_BOT_TOKEN (optional)
# - TELEGRAM_CHAT_ID (optional)
```

### Step 4: Install Systemd Services

**Create environment directory and copy .env:**

```bash
# Create environment directory
sudo mkdir -p /etc/ai-quant
sudo chmod 700 /etc/ai-quant

# Copy .env to systemd location (with secure permissions)
sudo install -m 600 .env /etc/ai-quant/.env
```

**Install both systemd units:**

```bash
# Install both service units (control plane + runner)
sudo bash scripts/systemd/install_units.sh
```

This script:
- Copies both service files to `/etc/systemd/system/`
- Reloads systemd daemon
- Verifies environment file exists and has correct permissions

**Optional: Enable and start immediately:**

```bash
# Install, enable, and start both services in one command
sudo ENABLE_AND_START=1 bash scripts/systemd/install_units.sh
```

### Step 5: Start Services

```bash
# Enable and start control plane
sudo systemctl enable ai-quant-control-plane.service
sudo systemctl start ai-quant-control-plane.service

# Enable and start runner
sudo systemctl enable ai-quant-runner.service
sudo systemctl start ai-quant-runner.service
```

### Step 6: Verify Services

```bash
# Check status
sudo systemctl status ai-quant-control-plane.service
sudo systemctl status ai-quant-runner.service

# Check logs
sudo journalctl -u ai-quant-control-plane.service -f
sudo journalctl -u ai-quant-runner.service -f

# Verify endpoints
curl -s http://127.0.0.1:8787/health | jq
curl -s http://127.0.0.1:8787/api/status | jq

# Verify accounts loaded
curl -s http://127.0.0.1:8787/api/status | jq '.accounts_loaded'

# Verify live prices
curl -s http://127.0.0.1:8787/api/sidebar/live-prices | jq
```

---

## Access from Mac (SSH Tunnel)

### Step 1: Open SSH Tunnel

```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- -L 8787:127.0.0.1:8787
```

**Keep this terminal open** while using the dashboard.

### Step 2: Get Control Plane Token

In another terminal:

```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- 'cat /tmp/control_plane_token_current.txt'
```

**⚠️ IMPORTANT:** Only show first 8 chars in logs. Never paste full token.

### Step 3: Open Dashboard

Open browser: `http://127.0.0.1:8787`

### Step 4: Configure Token

1. Click Settings (⚙️) in dashboard
2. Paste token into "Control Plane Token" field
3. Click Save

---

## Troubleshooting

### Issue: Control plane not starting

**Check logs:**
```bash
sudo journalctl -u ai-quant-control-plane.service -n 50
```

**Common causes:**
- Missing dependencies: `pip install -r requirements.txt`
- Port 8787 already in use: `sudo lsof -i :8787`
- Invalid .env file: Check syntax with `python3 scripts/env_sanity_check.py --env .env`

### Issue: Runner not loading accounts

**Check logs:**
```bash
sudo journalctl -u ai-quant-runner.service -n 50
```

**Common causes:**
- Invalid OANDA credentials: Verify `OANDA_API_KEY` and `OANDA_ACCOUNT_ID`
- Network issues: Check VM can reach OANDA API
- Account ID invalid: Verify account exists in OANDA practice environment

### Issue: Live prices empty

**Check:**
```bash
# Check if runner is running
sudo systemctl is-active ai-quant-runner.service

# Check status snapshot
cat ~/gcloud-system/runtime/status.json | jq '.live_prices'

# Check runner logs for errors
sudo journalctl -u ai-quant-runner.service | grep -i "price\|error"
```

**Common causes:**
- Runner not running: `sudo systemctl start ai-quant-runner.service`
- Runner hasn't completed first scan yet (wait 30-60 seconds)
- OANDA API errors (check logs)

### Issue: Services keep restarting

**Check:**
```bash
# Check service status
sudo systemctl status ai-quant-control-plane.service
sudo systemctl status ai-quant-runner.service

# Check for errors in logs
sudo journalctl -u ai-quant-control-plane.service --since "5 minutes ago" | grep -i error
sudo journalctl -u ai-quant-runner.service --since "5 minutes ago" | grep -i error
```

**Common causes:**
- Missing environment variables
- Python import errors
- Permission issues (check /opt/ai-quant permissions)

---

## Service Management

### Stop Services

```bash
sudo systemctl stop ai-quant-control-plane.service
sudo systemctl stop ai-quant-runner.service
```

### Start Services

```bash
sudo systemctl start ai-quant-control-plane.service
sudo systemctl start ai-quant-runner.service
```

### Restart Services

```bash
sudo systemctl restart ai-quant-control-plane.service
sudo systemctl restart ai-quant-runner.service
```

### Disable Services (prevent auto-start on boot)

```bash
sudo systemctl disable ai-quant-control-plane.service
sudo systemctl disable ai-quant-runner.service
```

### View Logs

```bash
# Follow logs
sudo journalctl -u ai-quant-control-plane.service -f
sudo journalctl -u ai-quant-runner.service -f

# Last 100 lines
sudo journalctl -u ai-quant-control-plane.service -n 100
sudo journalctl -u ai-quant-runner.service -n 100
```

---

## Verification Checklist

After deployment, verify:

**Quick verification (single command):**

```bash
ENV_FILE=/etc/ai-quant/.env bash scripts/verify_vm_full_stack.sh
```

**Manual verification:**

- [ ] Control plane service is active: `sudo systemctl is-active ai-quant-control-plane.service`
- [ ] Runner service is active: `sudo systemctl is-active ai-quant-runner.service`
- [ ] Health endpoint returns OK: `curl -s http://127.0.0.1:8787/health | jq`
- [ ] Status shows accounts loaded > 0: `curl -s http://127.0.0.1:8787/api/status | jq '.accounts_loaded'`
- [ ] Live prices are populated: `curl -s http://127.0.0.1:8787/api/sidebar/live-prices | jq '.prices | length'`
- [ ] Telegram health check passes: `ENV_FILE=/etc/ai-quant/.env bash scripts/verify_telegram.sh` (if configured)

---

## Security Notes

- **Environment file:** `/etc/ai-quant/.env` must have 600 permissions (owner read/write only)
- **No public ports:** Services bind to 127.0.0.1 only (localhost)
- **SSH tunnel required:** Access dashboard via SSH tunnel only
- **Token security:** Never paste full token in logs or chat

---

**Last Updated:** 2026-01-06  
**Status:** ✅ Verified Working
