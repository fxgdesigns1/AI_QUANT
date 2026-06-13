# November 2025 Deployment Blueprint (Recovered)

## Snapshot

- **Current branch**: `safety/savepoint-pre-lockin`
- **Current HEAD**: `2e2adc1e6718be20f42694b6a090a7e2db2a65d7`
- **Target period**: 2025-11-01 .. 2025-11-06 (safepoint tag)
- **Forensic branch**: `nov2025-deploy-forensics`

## Primary Evidence

- **Selected Nov 2025 commit SHA**: `b25f28a6a25669cd96b29ea18ea0704b177e39d5` (tag: `safepoint-2025-11-06`)
- **Deployment method**: `systemd-vm` (GCE VM with systemd service units)
- **Why this is the working blueprint**:
  - Tagged safepoint commit from Nov 6, 2025 indicating a known working state
  - Contains complete VM bootstrap script: `deploy/gcp/bootstrap_vm.sh`
  - Includes systemd unit file: `deploy/gcp/ai-quant-control-plane.service`
  - References to secrets loading via GCP Secret Manager
  - Firewall rule configuration for port 8787
  - Evidence from commit `695add7` (Nov 5) showing Cloud Run deployment files as secondary/alternative approach
  - Primary deployment target: GCE VM (e2-small, Debian 12) in `europe-west2-a`

## Deployment File Inventory (Nov 2025 commit b25f28a)

### Core Deployment Files

```
deploy/gcp/bootstrap_vm.sh                          # Main VM provisioning & deployment script
deploy/gcp/ai-quant-control-plane.service          # systemd unit file
deploy/gcp/secrets_to_env.sh                       # Secret Manager → env vars loader
scripts/systemd/ai-quant-control-plane.service     # Alternative systemd unit (if present)
scripts/systemd/ai-quant-runner.service            # Runner service unit (if present)
```

### Configuration Files

```
AI_QUANT_credentials/strategy_configs/*.yaml        # Strategy configurations
runtime/config.yaml                                 # Runtime config (hot-reload)
runtime/config.example.yaml                         # Config template
```

### Alternative/Secondary Deployment (Not Primary)

```
google-cloud-trading-system/app.yaml                # App Engine config (F1 free tier)
google-cloud-trading-system/Dockerfile*             # Docker images (if Cloud Run used)
dashboard/deploy_cloud_run.sh                       # Cloud Run deployment script (from commit 695add7)
```

**Note**: App Engine/Cloud Run files exist but the primary deployment method in Nov 2025 was **systemd on GCE VM** based on bootstrap_vm.sh being the most complete automation.

## Runbook (Nov 2025)

### 1) Preconditions

- **GCP Project/Region/Zone**: 
  - Project: `${GCP_PROJECT_ID}` (required env var)
  - Zone: `europe-west2-a` (default, configurable via `GCP_ZONE`)
- **Runtime target**: GCE VM (e2-small, Debian 12, 30GB disk)
- **Network**: Firewall rule `aiquant-allow-8787` for TCP port 8787
- **Prerequisites**:
  - `gcloud` CLI installed and authenticated locally
  - GCP Secret Manager secrets populated (see Config Contract section)

### 2) VM Creation & Bootstrap

```bash
# Set required environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_ZONE="europe-west2-a"  # optional, defaults to europe-west2-a
export GCP_VM_NAME="ai-quant-control-plane"  # optional, defaults to ai-quant-control-plane

# Run bootstrap script (creates VM, deploys code, installs systemd unit)
bash deploy/gcp/bootstrap_vm.sh
```

**What bootstrap_vm.sh does**:
1. Creates GCE VM if it doesn't exist (e2-small, Debian 12, 30GB disk)
2. Creates firewall rule for port 8787 if missing
3. Packages repo (excluding .git, .venv, node_modules, .env) into tarball
4. Copies tarball to VM via `gcloud compute scp`
5. SSH into VM and:
   - Creates `aiquant` user if missing
   - Deploys code to `/opt/ai-quant`
   - Installs Python 3, venv, pip, curl
   - Creates venv and installs dependencies from `requirements.txt` or `pyproject.toml`
   - Copies systemd unit to `/etc/systemd/system/`
   - Reloads systemd daemon
   - Enables and starts `ai-quant-control-plane` service

### 3) Secrets Configuration (Must be done on VM)

**Secrets must be stored in GCP Secret Manager** with these names:
- `ai-quant-oanda-api-key`
- `ai-quant-oanda-account-id`
- `ai-quant-newsapi-api-key`
- `ai-quant-alphavantage-api-key`
- `ai-quant-telegram-bot-token`
- `ai-quant-telegram-chat-id`
- Optional: `ai-quant-alphavantage-api-keys`, `ai-quant-marketaux-keys`, `ai-quant-polygon-api-keys`, `ai-quant-fmp-api-keys`, `ai-quant-finnhub-api-keys`, `ai-quant-fred-api-keys`

**The systemd service loads secrets at startup** via `deploy/gcp/secrets_to_env.sh` which:
- Requires `GCP_PROJECT_ID` environment variable
- Uses `gcloud secrets versions access latest` to fetch secrets
- Validates presence of required secrets (OANDA_API_KEY, OANDA_ACCOUNT_ID, NEWSAPI_API_KEY, ALPHAVANTAGE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Logs secret presence checks (without values) to `/tmp/aiquant_env_check.log`

### 4) Service Management

```bash
# SSH into VM
gcloud compute ssh ai-quant-control-plane --zone europe-west2-a --project $GCP_PROJECT_ID

# Check service status
sudo systemctl status ai-quant-control-plane

# View logs
sudo journalctl -u ai-quant-control-plane -f

# Restart service
sudo systemctl restart ai-quant-control-plane

# Stop service
sudo systemctl stop ai-quant-control-plane

# Start service
sudo systemctl start ai-quant-control-plane
```

### 5) Health Checks

```bash
# On VM or via SSH tunnel
curl http://127.0.0.1:8787/health

# Get status
curl http://127.0.0.1:8787/api/status

# Check logs for secret loading
cat /tmp/aiquant_env_check.log
```

**Endpoints**:
- Health: `http://127.0.0.1:8787/health`
- Status: `http://127.0.0.1:8787/api/status`
- Dashboard: `http://127.0.0.1:8787/` (requires SSH tunnel for external access)

**SSH Tunnel** (from local machine):
```bash
ssh -L 8787:127.0.0.1:8787 user@vm-external-ip
# Then access: http://localhost:8787/
```

## Config Contract (names only, no values)

### Required Environment Variables (loaded from Secret Manager)

| Variable Name | Purpose | Source |
|--------------|---------|--------|
| `GCP_PROJECT_ID` | GCP project identifier | Environment / systemd unit |
| `OANDA_API_KEY` | OANDA API authentication | Secret Manager: `ai-quant-oanda-api-key` |
| `OANDA_ACCOUNT_ID` | OANDA account identifier | Secret Manager: `ai-quant-oanda-account-id` |
| `OANDA_ENV` | OANDA environment (practice/live) | Hardcoded to "practice" in secrets_to_env.sh |
| `OANDA_BASE_URL` | OANDA API base URL | Hardcoded to "https://api-fxpractice.oanda.com" |
| `NEWSAPI_API_KEY` | NewsAPI authentication | Secret Manager: `ai-quant-newsapi-api-key` |
| `ALPHAVANTAGE_API_KEY` | Alpha Vantage API key | Secret Manager: `ai-quant-alphavantage-api-key` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot authentication | Secret Manager: `ai-quant-telegram-bot-token` |
| `TELEGRAM_CHAT_ID` | Telegram chat identifier | Secret Manager: `ai-quant-telegram-chat-id` |

### Optional Environment Variables (loaded from Secret Manager)

| Variable Name | Purpose | Source |
|--------------|---------|--------|
| `ALPHAVANTAGE_API_KEYS` | Multiple Alpha Vantage keys (comma-separated) | Secret Manager: `ai-quant-alphavantage-api-keys` |
| `MARKETAUX_KEYS` | MarketAux API keys | Secret Manager: `ai-quant-marketaux-keys` |
| `POLYGON_API_KEYS` | Polygon API keys | Secret Manager: `ai-quant-polygon-api-keys` |
| `FMP_API_KEYS` | Financial Modeling Prep API keys | Secret Manager: `ai-quant-fmp-api-keys` |
| `FINNHUB_API_KEYS` | Finnhub API keys | Secret Manager: `ai-quant-finnhub-api-keys` |
| `FRED_API_KEYS` | FRED API keys | Secret Manager: `ai-quant-fred-api-keys` |

### Service Runtime Variables (set by systemd unit)

| Variable Name | Purpose | Source |
|--------------|---------|--------|
| `PYTHONUNBUFFERED` | Python output buffering | systemd Environment directive (set to "1") |
| `CONTROL_PLANE_BG` | Control plane background mode | ExecStart command (set to "0") |
| `REQUIRE_OANDA` | Require OANDA credentials | ExecStart command (set to "1") |
| `REQUIRE_NEWS` | Require news API credentials | ExecStart command (set to "1") |
| `REQUIRE_TELEGRAM` | Require Telegram credentials | ExecStart command (set to "1") |

## Service Topology

### Components

1. **Control Plane API** (FastAPI)
   - **Process**: `src.control_plane.api` (Python module)
   - **Port**: 8787 (TCP, bind to 127.0.0.1 by default)
   - **User**: `aiquant` (non-root)
   - **Working Directory**: `/opt/ai-quant`
   - **Service File**: `/etc/systemd/system/ai-quant-control-plane.service`
   - **Startup Script**: `scripts/start_control_plane_clean.sh` (invoked by systemd)

2. **Runner** (if present)
   - **Process**: `runner_src.runner.main` (Python module)
   - **Service File**: `scripts/systemd/ai-quant-runner.service` (if deployed)
   - **Mode**: Separate service (optional)

### Ports

- **8787/TCP**: Control Plane API (HTTP, FastAPI/Uvicorn)
  - Access: 127.0.0.1:8787 (local), or via SSH tunnel
  - Firewall: `aiquant-allow-8787` rule allows TCP:8787 from internet (restrict by IP if needed)

### Logging

- **Systemd logs**: `sudo journalctl -u ai-quant-control-plane -f`
- **Secret loading logs**: `/tmp/aiquant_env_check.log`
- **Application logs**: Defined by `LOG_FILE_PATH` env (default: `logs/ai_quant.log`)

### Health Checks

- **Endpoint**: `GET /health`
- **Status endpoint**: `GET /api/status`
- **Log verification**: Check `/tmp/aiquant_env_check.log` for secret loading status

## Safety / Execution Gating

### Default Mode

**Not explicitly documented in Nov 2025 commit**, but evidence suggests:
- **OANDA_ENV**: Hardcoded to "practice" in `deploy/gcp/secrets_to_env.sh` (line 14)
- **Service requirements**: Systemd unit requires `REQUIRE_OANDA=1`, `REQUIRE_NEWS=1`, `REQUIRE_TELEGRAM=1` (all must be present)
- **Fail-closed**: Service will not start if required secrets are missing (validated by `secrets_to_env.sh`)

### Live Trading Enablement Mechanism

**Not explicitly found in Nov 2025 commit**. To enable live trading:
1. Modify `deploy/gcp/secrets_to_env.sh` to set `OANDA_ENV="live"` and `OANDA_BASE_URL="https://api-fxtrade.oanda.com"`
2. Ensure live account credentials are stored in Secret Manager
3. Restart systemd service

**Risk Controls** (inferred from app.yaml patterns found in repo):
- Trading mode controlled by `OANDA_ENV` environment variable
- Practice mode is default
- No explicit "TRADING_ENABLED" or "DRY_RUN" flags found in Nov 2025 deployment files

## Appendix: High-signal differences vs current

See `NOV2025_DEPLOYMENT_DIFF.md` for detailed comparison.

### Key Changes Since Nov 2025

1. **Deployment location**: Nov 2025 used `/opt/ai-quant`; current may use different paths
2. **Service file location**: Nov 2025 had `deploy/gcp/ai-quant-control-plane.service`; current has `scripts/systemd/ai-quant-control-plane.service`
3. **Secrets management**: Nov 2025 relied entirely on Secret Manager; current may have `.env` file support
4. **Control plane token**: Current system requires `CONTROL_PLANE_TOKEN` for POST endpoints; not found in Nov 2025 commit
5. **Runner service**: Current has `scripts/systemd/ai-quant-runner.service`; presence in Nov 2025 unclear

## Verification Commands

```bash
# Verify deployment at Nov 2025 commit
git checkout nov2025-deploy-forensics
git log -1 --oneline  # Should show: b25f28a Safepoint: snapshot on 2025-11-06

# Verify deployment files exist
ls -la deploy/gcp/bootstrap_vm.sh
ls -la deploy/gcp/ai-quant-control-plane.service
ls -la deploy/gcp/secrets_to_env.sh

# Verify systemd unit content
cat deploy/gcp/ai-quant-control-plane.service

# Verify bootstrap script
head -20 deploy/gcp/bootstrap_vm.sh
```
