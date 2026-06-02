# VM Deploy Instructions (Gated, Placeholder-Proofed)

**Date:** 2026-01-05  
**Script:** `scripts/vm_deploy_gated.sh`

---

## Overview

The VM deploy script is **gated** and **placeholder-proofed** to prevent accidental deployments with invalid configuration.

---

## Prerequisites

1. **SSH Access**: SSH key must be configured and authorized on the VM
2. **Git Remote**: Local repo must have `remote.origin.url` configured
3. **VM Access**: VM must be reachable via SSH

---

## Required Environment Variables

### Gate 1: Deploy Approval

```bash
export DEPLOY_APPROVED=true
```

**Without this**: Script exits with message (exit code 0 = skipped, not error)

### Gate 2: VM Configuration

```bash
export VM_HOST="your-vm-hostname-or-ip"
export VM_USER="your-vm-username"
export VM_DIR="/opt/ai_quant"  # or your preferred deployment directory
export VM_BRANCH="safety/savepoint-pre-lockin"  # optional, defaults to safety branch
```

**Placeholder Detection**: Script refuses:
- Values containing `__`
- Values containing `your_`
- Values containing `REDACTED`
- Values containing `placeholder`, `replace`, `example`
- Empty values

---

## Deployment Process

### Step 1: Preflight Check

Script performs SSH connectivity test:
```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 "$VM_USER@$VM_HOST" "hostname && whoami"
```

**If this fails**: Script exits with error (exit code 2) and does NOT deploy.

### Step 2: Git Clone/Update

- If `.git` directory exists: Updates existing repo (fetch, checkout, reset)
- If `.git` directory missing: Clones repo from `remote.origin.url`

### Step 3: Python Environment Setup

- Creates Python virtual environment (`.venv`)
- Upgrades pip and wheel
- Installs requirements from `requirements.txt` (if present)

### Step 4: Status Log

Writes deployment status to `${VM_DIR}/.deploy_status.log` on VM (no secrets).

---

## Example Usage

```bash
# Set gates
export DEPLOY_APPROVED=true
export VM_HOST="10.0.0.100"
export VM_USER="deploy"
export VM_DIR="/opt/ai_quant"
export VM_BRANCH="safety/savepoint-pre-lockin"

# Run deploy
./scripts/vm_deploy_gated.sh
```

---

## Safety Features

### 1. Gate Protection

- `DEPLOY_APPROVED=true` required
- Without gate: Script exits cleanly (not an error)

### 2. Placeholder Detection

- Refuses placeholder values before any SSH attempt
- Prevents accidental deployment with test/example values

### 3. SSH Preflight

- Tests SSH connectivity before any deployment actions
- Fails fast if VM is unreachable

### 4. No Secrets Transfer

- Script NEVER transfers secrets
- Secrets must be set on VM manually or via Secret Manager
- Git repo contains no secrets (enforced by pre-commit hook)

### 5. Non-Destructive

- Uses `git reset --hard` only after confirming branch exists
- Never deletes existing files (except git reset)
- Creates backup via git before reset (git's built-in safety)

---

## Error Handling

### Error: "DEPLOY_LOCKED"

**Cause**: `DEPLOY_APPROVED` is not set to `true`

**Solution**: Set `export DEPLOY_APPROVED=true`

### Error: "VM_HOST appears to be a placeholder"

**Cause**: Placeholder detection triggered

**Solution**: Use real VM hostname/IP, not placeholder values

### Error: "SSH preflight failed"

**Cause**: Cannot connect to VM via SSH

**Solution**: 
1. Check SSH key is authorized
2. Check VM is reachable
3. Check `VM_USER` and `VM_HOST` are correct

### Error: "no remote.origin.url found"

**Cause**: Local git repo has no remote configured

**Solution**: Configure git remote:
```bash
git remote add origin <your-repo-url>
```

---

## Post-Deployment

After deployment:

1. **Set Secrets on VM**: Use Secret Manager or manual env file (outside repo)
2. **Configure systemd**: Use env file outside repo (never commit secrets)
3. **Verify**: SSH to VM and check `${VM_DIR}/.deploy_status.log`

---

## Verification

Check deployment status on VM:
```bash
ssh "$VM_USER@$VM_HOST" "cat ${VM_DIR}/.deploy_status.log"
```

Expected output:
```
Deploy completed: 2026-01-05T12:00:00Z branch=safety/savepoint-pre-lockin
```

---

## Notes

- **No secrets in repo**: Script never transfers secrets
- **Fail closed**: Script fails fast on errors (does not continue)
- **Placeholder-proof**: Refuses placeholder values before any action
- **SSH preflight**: Tests connectivity before deployment
- **Git-based**: Uses git clone/fetch, never copies files directly
