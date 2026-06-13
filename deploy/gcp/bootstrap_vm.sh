#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_ZONE:=europe-west2-a}"
: "${GCP_VM_NAME:=ai-quant-control-plane}"

# Creates VM, installs deps, sets up service account access, deploys repo, installs systemd unit.
# Assumes gcloud is installed and authenticated locally.

# 1) Create VM (idempotent-ish)
if ! gcloud compute instances describe "$GCP_VM_NAME" --zone "$GCP_ZONE" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
  gcloud compute instances create "$GCP_VM_NAME" \
    --project "$GCP_PROJECT_ID" \
    --zone "$GCP_ZONE" \
    --machine-type "e2-small" \
    --image-family "debian-12" \
    --image-project "debian-cloud" \
    --tags "aiquant" \
    --scopes "https://www.googleapis.com/auth/cloud-platform" \
    --boot-disk-size "30GB"
fi

# 2) Firewall (port 8787). You may restrict by IP later.
if ! gcloud compute firewall-rules describe aiquant-allow-8787 --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
  gcloud compute firewall-rules create aiquant-allow-8787 \
    --project "$GCP_PROJECT_ID" \
    --allow tcp:8787 \
    --target-tags aiquant \
    --description "Allow AI_QUANT dashboard/control plane"
fi

# 3) Deploy code to VM
TMP_TAR="/tmp/ai_quant_deploy.tar.gz"
tar --exclude-vcs --exclude='.venv' --exclude='node_modules' --exclude='.env' -czf "$TMP_TAR" .

gcloud compute scp "$TMP_TAR" "$GCP_VM_NAME:/tmp/ai_quant_deploy.tar.gz" --zone "$GCP_ZONE" --project "$GCP_PROJECT_ID"

gcloud compute ssh "$GCP_VM_NAME" --zone "$GCP_ZONE" --project "$GCP_PROJECT_ID" --command '
set -euo pipefail

# Ensure aiquant user exists
if ! id -u aiquant >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash aiquant || { echo "Failed to create aiquant user" >&2; exit 1; }
fi

# Ensure /opt/ai-quant exists and is owned by aiquant
sudo mkdir -p /opt/ai-quant
sudo chown -R aiquant:aiquant /opt/ai-quant

# Deploy code
sudo -u aiquant bash -lc "cd /opt/ai-quant && rm -rf ./* && tar -xzf /tmp/ai_quant_deploy.tar.gz" || { echo "Failed to extract code" >&2; exit 1; }

# Ensure secrets_to_env.sh is executable
sudo -u aiquant bash -lc "cd /opt/ai-quant && chmod +x deploy/gcp/secrets_to_env.sh" || { echo "Failed to chmod secrets_to_env.sh" >&2; exit 1; }

# Install python + venv
sudo apt-get update -y || { echo "Failed to apt-get update" >&2; exit 1; }
sudo apt-get install -y python3 python3-venv python3-pip curl || { echo "Failed to install dependencies" >&2; exit 1; }

# Create venv and install dependencies
sudo -u aiquant bash -lc "cd /opt/ai-quant && python3 -m venv .venv && source .venv/bin/activate && pip install -U pip && if [ -f requirements.txt ]; then pip install -r requirements.txt; elif [ -f pyproject.toml ]; then pip install -e .; fi" || { echo "Failed to setup Python environment" >&2; exit 1; }

# Install systemd unit
sudo cp /opt/ai-quant/deploy/gcp/ai-quant-control-plane.service /etc/systemd/system/ai-quant-control-plane.service || { echo "Failed to copy systemd unit" >&2; exit 1; }
sudo systemctl daemon-reload || { echo "Failed to reload systemd" >&2; exit 1; }
sudo systemctl enable ai-quant-control-plane || { echo "Failed to enable service" >&2; exit 1; }
sudo systemctl restart ai-quant-control-plane || { echo "Failed to restart service" >&2; exit 1; }
'

echo "VM bootstrap complete."
