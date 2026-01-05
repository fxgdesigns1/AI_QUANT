#!/usr/bin/env bash
set -euo pipefail

# Gate 1: Deploy approval required
if [[ "${DEPLOY_APPROVED:-false}" != "true" ]]; then
  echo "DEPLOY_LOCKED: set DEPLOY_APPROVED=true to run deployment." 
  echo "Required env: VM_HOST, VM_USER, VM_DIR (e.g., /opt/ai_quant), VM_BRANCH (optional)."
  echo "This script NEVER transfers secrets. You must set env vars on the VM manually or via Secret Manager tooling." 
  exit 0
fi

# Gate 2: Required env vars
: "${VM_HOST:?Missing VM_HOST}"
: "${VM_USER:?Missing VM_USER}"
: "${VM_DIR:?Missing VM_DIR}"
VM_BRANCH="${VM_BRANCH:-safety/savepoint-pre-lockin}"

# Gate 3: Refuse placeholders
is_placeholder() {
  local val="$1"
  if [[ -z "$val" ]]; then
    return 0  # Empty is placeholder
  fi
  # Check for common placeholder patterns
  if [[ "$val" == *"__"* ]] || \
     [[ "$val" == *"your_"* ]] || \
     [[ "$val" == *"REDACTED"* ]] || \
     [[ "$val" == *"placeholder"* ]] || \
     [[ "$val" == *"replace"* ]] || \
     [[ "$val" == *"example"* ]]; then
    return 0  # Is placeholder
  fi
  return 1  # Not placeholder
}

if is_placeholder "$VM_HOST"; then
  echo "ERROR: VM_HOST appears to be a placeholder: $VM_HOST"
  exit 2
fi

if is_placeholder "$VM_USER"; then
  echo "ERROR: VM_USER appears to be a placeholder: $VM_USER"
  exit 2
fi

if is_placeholder "$VM_DIR"; then
  echo "ERROR: VM_DIR appears to be a placeholder: $VM_DIR"
  exit 2
fi

echo "Deploying branch=$VM_BRANCH to $VM_USER@$VM_HOST:$VM_DIR"

# Gate 4: SSH preflight check (dry-run connectivity test)
echo "Preflight: Testing SSH connectivity..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "${VM_USER}@${VM_HOST}" "hostname && whoami" >/dev/null 2>&1; then
  echo "ERROR: SSH preflight failed. Cannot connect to $VM_USER@$VM_HOST"
  echo "Check:"
  echo "  - SSH key is configured and authorized"
  echo "  - VM_HOST is reachable"
  echo "  - VM_USER is correct"
  exit 2
fi
echo "SSH preflight OK"

# Safer approach: use git remote URL if available
REMOTE_URL=$(git config --get remote.origin.url || true)
if [[ -z "$REMOTE_URL" ]]; then
  echo "ERROR: no remote.origin.url found. Configure git remote before deploy."; exit 1
fi

# Deploy: create directory if needed
ssh "${VM_USER}@${VM_HOST}" "mkdir -p '${VM_DIR}'"

# Deploy: clone or update git repo
if ssh "${VM_USER}@${VM_HOST}" "test -d '${VM_DIR}/.git'"; then
  echo "Updating existing git repo..."
  ssh "${VM_USER}@${VM_HOST}" "cd '${VM_DIR}' && (git remote set-url origin '$REMOTE_URL' || true) && git fetch origin && git checkout '$VM_BRANCH' && git reset --hard 'origin/$VM_BRANCH'"
else
  echo "Cloning git repo..."
  ssh "${VM_USER}@${VM_HOST}" "cd '$(dirname "${VM_DIR}")' && git clone '$REMOTE_URL' '$(basename "${VM_DIR}")' && cd '${VM_DIR}' && git checkout '$VM_BRANCH'"
fi

# VM setup: install deps, create venv, install requirements
echo "Setting up Python environment..."
ssh "${VM_USER}@${VM_HOST}" "cd '${VM_DIR}' && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip wheel && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi"

# Write deployment status log (no secrets)
DEPLOY_LOG="/tmp/ai-quant-deploy-$(date +%s).log"
ssh "${VM_USER}@${VM_HOST}" "echo 'Deploy completed: $(date -u +%Y-%m-%dT%H:%M:%SZ) branch=$VM_BRANCH' > '${VM_DIR}/.deploy_status.log'"

echo "DEPLOY_DONE (code only). Next: set secrets on VM and configure systemd using env file outside repo."
echo "Deployment status written to: ${VM_DIR}/.deploy_status.log on VM" 
