# How to Run AI_QUANT System

**Complete guide for local and cloud deployment.**

---

## Local Development

### Quick Start (One Command)

```bash
ENV_FILE=.env bash scripts/bringup_local_full.sh
```

This starts:
- Control Plane (http://127.0.0.1:8787)
- Runner (account loading, price polling, signal scanning)
- Verifies everything is working

### Manual Start

**Control Plane:**
```bash
ENV_FILE=.env CONTROL_PLANE_BG=1 bash scripts/start_control_plane_clean.sh
```

**Runner:**
```bash
ENV_FILE=.env RUNNER_BG=1 bash scripts/start_runner_clean.sh
```

### Verification

```bash
# Check control plane
curl -s http://127.0.0.1:8787/health | jq

# Check status
curl -s http://127.0.0.1:8787/api/status | jq

# Check live prices
curl -s http://127.0.0.1:8787/api/sidebar/live-prices | jq

# Verify paper readiness
ENV_FILE=.env bash scripts/verify_paper_readiness.sh

# Verify live prices
ENV_FILE=.env bash scripts/verify_live_prices.sh

# Verify Telegram
ENV_FILE=.env bash scripts/verify_telegram.sh
```

### Stop Services

```bash
# Stop control plane
bash scripts/stop_control_plane.sh

# Stop runner
pkill -f "runner_src.runner.main"
```

---

## Cloud Deployment (GCP VM)

### Quick Deploy

**On the VM:**
```bash
cd ~/gcloud-system
bash scripts/vm_bootstrap_deploy_verify.sh
```

### Manual Deployment

**1. Install prerequisites:**
```bash
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl jq lsof ripgrep
```

**2. Setup repository:**
```bash
cd ~/gcloud-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Configure environment:**
```bash
cp .env.example .env
nano .env  # Add your credentials
```

**4. Install systemd services:**
```bash
# Create environment directory and copy .env
sudo mkdir -p /etc/ai-quant
sudo install -m 600 .env /etc/ai-quant/.env

# Install both service units
sudo bash scripts/systemd/install_units.sh

# Optional: Enable and start immediately
sudo ENABLE_AND_START=1 bash scripts/systemd/install_units.sh
```

**5. Start services:**
```bash
sudo systemctl enable ai-quant-control-plane.service
sudo systemctl start ai-quant-control-plane.service

sudo systemctl enable ai-quant-runner.service
sudo systemctl start ai-quant-runner.service
```

**6. Verify:**
```bash
# Quick verification (all checks)
ENV_FILE=/etc/ai-quant/.env bash scripts/verify_vm_full_stack.sh

# Or verify manually:
sudo systemctl status ai-quant-control-plane.service
sudo systemctl status ai-quant-runner.service

curl -s http://127.0.0.1:8787/health | jq
curl -s http://127.0.0.1:8787/api/status | jq
curl -s http://127.0.0.1:8787/api/sidebar/live-prices | jq

# Verify live prices are populated
ENV_FILE=/etc/ai-quant/.env bash scripts/verify_live_prices.sh
```

### Access from Mac

**1. Open SSH tunnel:**
```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- -L 8787:127.0.0.1:8787
```

**2. Get token:**
```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- 'cat /tmp/control_plane_token_current.txt'
```

**3. Open dashboard:**
```
http://127.0.0.1:8787
```

---

## Environment Variables

**Required:**
- `OANDA_API_KEY` - OANDA API key
- `OANDA_ACCOUNT_ID` - OANDA account ID (practice or live)

**Optional:**
- `OANDA_BASE_URL` - OANDA API base URL (defaults based on OANDA_ENV)
- `OANDA_ENV` - `practice` or `live` (default: `practice`)
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Telegram chat ID
- `PAPER_EXECUTION_ENABLED` - `true` to enable paper execution (default: `false`)
- `TRADING_MODE` - `paper` or `live` (default: `paper`)

**See `.env.example` for complete list.**

---

## Verification Commands

```bash
# Environment check
python3 scripts/env_sanity_check.py --env .env
ENV_FILE=.env bash scripts/local_preflight.sh

# Control plane
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/api/status

# Live prices
curl -s http://127.0.0.1:8787/api/sidebar/live-prices

# Paper readiness
ENV_FILE=.env bash scripts/verify_paper_readiness.sh

# Telegram
ENV_FILE=.env bash scripts/verify_telegram.sh
```

---

## Troubleshooting

**Control plane not starting:**
- Check logs: `tail -f /tmp/control_plane.out`
- Check port: `lsof -i :8787`
- Verify dependencies: `pip install -r requirements.txt`

**Runner not loading accounts:**
- Check logs: `tail -f /tmp/runner.out`
- Verify OANDA credentials: `ENV_FILE=.env bash scripts/local_preflight.sh`
- Check account ID is valid

**Live prices empty:**
- Check runner is running: `ps aux | grep runner_src.runner.main`
- Wait 30-60 seconds for first scan
- Check status snapshot: `cat runtime/status.json | jq '.live_prices'`

**Telegram not working:**
- Run: `ENV_FILE=.env bash scripts/verify_telegram.sh`
- Check bot token and chat ID
- Verify bot is added to group/channel

---

## Documentation

- **Runner Architecture:** `docs/runbooks/RUNNER_AND_ACCOUNTS.md`
- **Paper Execution:** `docs/runbooks/READY_TO_EXECUTE_PAPER.md`
- **Cloud Deployment:** `docs/runbooks/CLOUD_DEPLOY_FULL.md`
- **Control Plane:** `docs/RUN_CONTROL_PLANE.md`

---

**Last Updated:** 2026-01-06
