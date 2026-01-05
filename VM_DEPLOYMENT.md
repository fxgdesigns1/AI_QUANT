# VM Deployment Guide: Control Plane on GCP Debian

## Quick Start (If repo is already on VM)

If you've already copied/cloned the repo to the VM, run:

```bash
cd ~/gcloud-system  # or wherever the repo is
bash scripts/vm_bootstrap_control_plane.sh
```

## Step-by-Step Manual Deployment

### Option A: Copy repo from local machine to VM

From your **local machine** (Mac), run:

```bash
# Set VM variables
VM_ZONE="us-east1-b"
VM_NAME="fxg-quant-paper-e2-micro"
PROJECT="fxg-ai-trading"
REPO_PATH="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"

# Copy repo to VM
gcloud compute scp --recurse \
  --zone="$VM_ZONE" \
  --project="$PROJECT" \
  "$REPO_PATH" \
  "$VM_NAME:~/gcloud-system"
```

Then SSH into VM and run bootstrap:

```bash
gcloud compute ssh --zone "$VM_ZONE" --project "$PROJECT" "$VM_NAME"
cd ~/gcloud-system
bash scripts/vm_bootstrap_control_plane.sh
```

### Option B: Clone from Git (if repo is in a git remote)

On the VM:

```bash
cd ~
git clone <YOUR_GIT_URL> gcloud-system
cd gcloud-system
bash scripts/vm_bootstrap_control_plane.sh
```

## What the Bootstrap Script Does

1. **Phase 0**: System info and tool checks
2. **Phase 1**: Install prerequisites (python3, git, curl, jq, lsof)
3. **Phase 2**: Locate repo root
4. **Phase 3**: Create venv, install dependencies, compile Python
5. **Phase 4**: Start control plane in background, verify, confirm paper mode

## Verification

After bootstrap completes, verify:

```bash
# Check status
curl -s http://127.0.0.1:8787/api/status | jq

# Should show:
# {
#   "mode": "paper",
#   "execution_enabled": false,
#   ...
# }

# Check noise shims (all should return 204)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/favicon.ico
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/api/insights
```

## Background Mode

The bootstrap script uses `CONTROL_PLANE_BG=1` if supported. This:
- Starts server in background
- Writes PID to `/tmp/control_plane_pid`
- Writes logs to `/tmp/control_plane.out`
- Returns immediately after server is ready

## Troubleshooting

### Repo not found
```bash
# Find repo
find ~ -name "start_control_plane_clean.sh" 2>/dev/null

# Or manually set path
export REPO_ROOT=~/gcloud-system
cd $REPO_ROOT
```

### Server not starting
```bash
# Check logs
tail -200 /tmp/control_plane.out

# Check if port is in use
lsof -i :8787

# Check Python compilation
python3 -m py_compile src/control_plane/api.py
```

### Dependencies fail to install
```bash
# Update pip first
python3 -m pip install -U pip setuptools wheel

# Install build tools
sudo apt-get install -y python3-dev build-essential

# Retry
pip install -r requirements.txt
```

## Security Notes

- ✅ Tokens are never printed in full (only first 8 chars)
- ✅ Paper mode enforced (execution_enabled=false)
- ✅ No secrets in code or logs
- ✅ Same-origin only (no CORS by default)
