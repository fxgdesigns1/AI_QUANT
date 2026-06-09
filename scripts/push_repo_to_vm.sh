#!/usr/bin/env bash
set -euo pipefail

PROJECT="fxg-ai-trading"
ZONE="us-east1-b"
INSTANCE="fxg-quant-paper-e2-micro"

# Repo root = directory containing scripts/start_control_plane_clean.sh
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[PUSH] Repo root: $REPO_ROOT"
echo "[PUSH] Creating safe tarball (excluding secrets/heavy dirs)..."

TARBALL="/tmp/gcloud-system-upload.tgz"
rm -f "$TARBALL"

tar -czf "$TARBALL" \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='**/__pycache__' \
  --exclude='**/*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='**/*.pem' \
  --exclude='**/*.key' \
  --exclude='**/secrets*' \
  --exclude='**/*token*' \
  --exclude='scripts/artifacts/*.har' \
  --exclude='scripts/artifacts/*.zip' \
  .

echo "[PUSH] Uploading tarball to VM..."
gcloud compute scp --project "$PROJECT" --zone "$ZONE" "$TARBALL" "$INSTANCE:~/gcloud-system-upload.tgz"

echo "[PUSH] Extracting on VM..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "rm -rf ~/gcloud-system && mkdir -p ~/gcloud-system && tar -xzf ~/gcloud-system-upload.tgz -C ~/gcloud-system"

echo "[PUSH] Running deploy script on VM..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "cd ~/gcloud-system && chmod +x scripts/deploy_vm_end_to_end.sh && bash scripts/deploy_vm_end_to_end.sh"

echo "[PUSH] Done."
