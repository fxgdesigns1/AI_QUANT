# GCP VM Cloud-Ready Runbook: Control Plane

## Quick Start (One Command)

**On the VM**, run:

```bash
cd ~/gcloud-system
bash scripts/vm_bootstrap_deploy_verify.sh
```

This script is **idempotent** - safe to run multiple times.

## What It Does

1. **Installs prerequisites**: python3, venv, pip, git, curl, jq, lsof, ripgrep
2. **Verifies repo**: Checks that repo exists at `~/gcloud-system`
3. **Sets up venv**: Creates virtual environment and installs requirements
4. **Compiles Python**: Verifies `src/control_plane/api.py` compiles
5. **Starts server**: Runs in background mode (PID stored in `/tmp/control_plane_pid`)
6. **Verifies**: Runs full verification suite (must exit 0)
7. **Confirms paper mode**: Checks `/api/status` shows `mode=paper` and `execution_enabled=false`

## Expected Output

```
✅ Repo OK: /home/fxgdesigns1_gmail_com/gcloud-system
✅ py_compile OK
✅ Server started with PID: <PID>
Token(first8): <first8>...
✅ All verification tests passed!
verify_exit_code=0
{
  "mode": "paper",
  "execution_enabled": false,
  ...
}
```

## Evidence Files

After successful deployment:

- **PID file**: `/tmp/control_plane_pid` (contains server PID)
- **Log file**: `/tmp/control_plane.out` (server logs)
- **Token file**: `/tmp/control_plane_token_current.txt` (⚠️ do not share full token)

## Safe Access from Mac

The server binds to `127.0.0.1:8787` only (localhost). Access via SSH tunnel:

### Step 1: Open SSH Tunnel

```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- -L 8787:127.0.0.1:8787
```

Keep this terminal open while using the dashboard.

### Step 2: Get Token

In another terminal:

```bash
gcloud compute ssh --project fxg-ai-trading --zone us-east1-b \
  fxg-quant-paper-e2-micro -- 'cat /tmp/control_plane_token_current.txt'
```

**⚠️ IMPORTANT**: Only show first 8 chars in logs. Never paste full token.

### Step 3: Open Dashboard

Open browser: `http://127.0.0.1:8787`

### Step 4: Configure Token

1. Click Settings (⚙️) in dashboard
2. Paste token from Step 2
3. Click Save

## Optional: Systemd Persistence

To make the service survive reboots and auto-start:

```bash
cd ~/gcloud-system
bash scripts/create_systemd_unit.sh
sudo systemctl start ai-quant-control-plane.service
```

**Note**: If using systemd, stop any manually started server first:

```bash
bash scripts/stop_control_plane.sh
```

### Systemd Commands

```bash
# Start service
sudo systemctl start ai-quant-control-plane.service

# Stop service
sudo systemctl stop ai-quant-control-plane.service

# Check status
sudo systemctl status ai-quant-control-plane.service

# View logs
sudo journalctl -u ai-quant-control-plane.service -f

# Enable auto-start on boot
sudo systemctl enable ai-quant-control-plane.service
```

## Verification Checklist

After deployment, verify:

- [ ] `verify_exit_code=0` (verification script passes)
- [ ] `/api/status` shows `mode=paper`
- [ ] `/api/status` shows `execution_enabled=false`
- [ ] Noise shims return 204:
  - [ ] `/favicon.ico` → 204
  - [ ] `/socket.io` → 204
  - [ ] `/api/insights` → 204
  - [ ] `/api/trade_ideas` → 204
  - [ ] `/tasks/full_scan` → 204
- [ ] Server PID exists in `/tmp/control_plane_pid`
- [ ] Logs exist in `/tmp/control_plane.out`
- [ ] Token file exists (first 8 chars only shown)

## Troubleshooting

### Verification Fails (exit code != 0)

```bash
# Check what failed
cd ~/gcloud-system
TOKEN=$(cat /tmp/control_plane_token_current.txt)
bash -x scripts/verify_control_plane.sh "$TOKEN" 2>&1 | tail -50
```

**Common issues**:
- Missing `ripgrep`: `sudo apt-get install -y ripgrep`
- Server not listening: `lsof -i :8787` and `tail -200 /tmp/control_plane.out`
- Missing dependencies: `pip install -r requirements.txt`

### Server Not Starting

```bash
# Check if port is in use
lsof -i :8787

# Check logs
tail -200 /tmp/control_plane.out

# Try manual start
cd ~/gcloud-system
source .venv/bin/activate
python -m src.control_plane.api
```

### Token Issues

**Never**:
- Print full token in logs
- Commit token to git
- Share token in chat

**Always**:
- Show only first 8 chars: `${TOKEN:0:8}...`
- Store token in `/tmp/control_plane_token_current.txt` (temporary)
- Use SSH tunnel for access (no public port)

## Security Notes

✅ **Enforced**:
- Paper mode only (`TRADING_MODE=paper`)
- Execution disabled (`execution_enabled=false`)
- Localhost binding only (`127.0.0.1:8787`)
- No public firewall port
- SSH tunnel required for access
- Token redaction (first 8 chars only)

❌ **Never**:
- Enable live trading
- Open port 8787 in firewall
- Print full tokens
- Commit secrets

## Manual Verification Commands

```bash
# Check server is running
lsof -nP -iTCP:8787 -sTCP:LISTEN

# Check status
curl -s http://127.0.0.1:8787/api/status | jq

# Check noise shims
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/favicon.ico
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/api/insights
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8787/tasks/full_scan

# Check logs
tail -50 /tmp/control_plane.out

# Check PID
cat /tmp/control_plane_pid
```

## Files Created

- `scripts/vm_bootstrap_deploy_verify.sh` - One-shot bootstrap+deploy+verify
- `scripts/create_systemd_unit.sh` - Optional systemd persistence
- `VM_RUNBOOK.md` - This document

## Success Criteria

✅ All of these must be true:

1. Repo exists at `~/gcloud-system`
2. Prerequisites installed (python3, venv, pip, git, curl, jq, lsof, ripgrep)
3. `python3 -m py_compile src/control_plane/api.py` succeeds
4. Server runs in background (PID in `/tmp/control_plane_pid`)
5. `bash scripts/verify_control_plane.sh "$TOKEN"` exits 0
6. `/api/status` shows `mode=paper` and `execution_enabled=false`
7. All noise shims return 204
8. Token file exists (only first 8 chars displayed)

## Backup Before Operations

**RECOMMENDED**: Create a backup before running audits or making changes.

### Quick Backup Command

```bash
cd ~/gcloud-system
bash scripts/backup/full_backup.sh
```

### Include ARTIFACTS Directory

```bash
INCLUDE_ARTIFACTS=1 bash scripts/backup/full_backup.sh
```

### Verify Backup

```bash
LATEST=$(ls -dt BACKUPS/*/* | head -n 1)
bash scripts/backup/verify_backup.sh "$LATEST"
```

### Backups Location

Backups are stored in: `BACKUPS/<hostname>/<repo>/<timestamp>/`

For full backup documentation, see: `docs/runbooks/BACKUP_RUNBOOK.md`

## Next Steps

After successful deployment:

1. ✅ Create backup (recommended before any operations)
2. ✅ Verify all checks pass
3. ✅ Test dashboard access via SSH tunnel
4. ✅ Configure token in dashboard Settings
5. ✅ (Optional) Enable systemd unit for persistence
6. ✅ Document any custom configurations

---

**Last Updated**: 2026-01-04  
**VM**: fxg-quant-paper-e2-micro (Debian bullseye)  
**Service Port**: 8787 (localhost only)  
**Mode**: Paper (execution disabled)
