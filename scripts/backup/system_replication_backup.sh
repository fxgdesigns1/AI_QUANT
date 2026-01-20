#!/bin/bash
# FXG AI-QUANT — System Replication Backup
# Creates a focused backup for replicating Alpha + Beta VMs
# Includes: VM configs, code, documentation, deployment scripts
# Excludes: venv, node_modules, logs, large artifacts, caches
#
# Usage:
#   bash scripts/backup/system_replication_backup.sh

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
GIT_SHA=$(cd "$REPO_ROOT" && git rev-parse HEAD 2>/dev/null || echo "NO_GIT")
GIT_SHA_SHORT="${GIT_SHA:0:8}"

# Backup destination
BACKUP_BASE="${BACKUP_DIR:-$REPO_ROOT/.BACKUPS}"
BACKUP_DEST="$BACKUP_BASE/SYSTEM_REPLICATION_${TIMESTAMP}"
mkdir -p "$BACKUP_DEST"

# GCP Project/VMs
PROJECT="${GCP_PROJECT:-fxg-ai-trading}"
ZONE="${GCP_ZONE:-us-east1-b}"
ALPHA_VM="${ALPHA_VM:-fxg-quant-paper-e2-micro}"
BETA_VM="${BETA_VM:-fxg-strat-2}"

# Compression
if command -v zstd >/dev/null 2>&1; then
    COMPRESS_CMD="zstd -T0 -19"
    COMPRESS_EXT="tar.zst"
else
    COMPRESS_CMD="gzip -9"
    COMPRESS_EXT="tar.gz"
fi

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo "[$(date -u +%H:%M:%S)] $*"
}

log_error() {
    echo "[$(date -u +%H:%M:%S)] ERROR: $*" >&2
}

# ============================================================================
# Phase 1: Backup GCP Infrastructure Config
# ============================================================================

log "Phase 1: Backing up GCP infrastructure configuration..."

VM_CONFIG_DIR="$BACKUP_DEST/vm_configs"
mkdir -p "$VM_CONFIG_DIR"

# Alpha VM config
log "  Alpha VM: $ALPHA_VM"
gcloud compute instances describe "$ALPHA_VM" \
    --project "$PROJECT" \
    --zone "$ZONE" \
    --format="yaml(name,status,machineType,networkInterfaces,disks[0].source.basename(),tags.items)" \
    > "$VM_CONFIG_DIR/alpha_vm.yaml" 2>&1 || log_error "Failed to backup Alpha VM config"

# Beta VM config
log "  Beta VM: $BETA_VM"
gcloud compute instances describe "$BETA_VM" \
    --project "$PROJECT" \
    --zone "$ZONE" \
    --format="yaml(name,status,machineType,networkInterfaces,disks[0].source.basename(),tags.items)" \
    > "$VM_CONFIG_DIR/beta_vm.yaml" 2>&1 || log_error "Failed to backup Beta VM config"

# Firewall rules
log "  Firewall rules"
gcloud compute firewall-rules list \
    --project "$PROJECT" \
    --format="yaml" \
    > "$VM_CONFIG_DIR/firewall_rules.yaml" 2>&1 || log_error "Failed to backup firewall rules"

# Network configs
log "  Network configs"
gcloud compute networks list \
    --project "$PROJECT" \
    --format="yaml" \
    > "$VM_CONFIG_DIR/networks.yaml" 2>&1 || log_error "Failed to backup network configs"

log "  ✓ Infrastructure configs saved to vm_configs/"

# ============================================================================
# Phase 2: Backup VM Systemd Services + Configs (if accessible)
# ============================================================================

log "Phase 2: Backing up VM systemd services and configs..."

VM_SERVICES_DIR="$BACKUP_DEST/vm_services"
mkdir -p "$VM_SERVICES_DIR"

# Alpha VM services
log "  Alpha VM services"
if gcloud compute ssh "$ALPHA_VM" \
    --project "$PROJECT" \
    --zone "$ZONE" \
    --tunnel-through-iap \
    --command "sudo cat /etc/systemd/system/ai-quant-control-plane.service /etc/systemd/system/ai-quant-runner.service 2>/dev/null || true" \
    > "$VM_SERVICES_DIR/alpha_services.txt" 2>&1; then
    log "    ✓ Alpha services backed up"
else
    log "    ⚠ Alpha services backup failed (services may not exist)"
fi

# Beta VM services
log "  Beta VM services"
if gcloud compute ssh "$BETA_VM" \
    --project "$PROJECT" \
    --zone "$ZONE" \
    --tunnel-through-iap \
    --command "sudo cat /etc/systemd/system/ai-quant-control-plane.service /etc/systemd/system/ai-quant-runner.service 2>/dev/null || true" \
    > "$VM_SERVICES_DIR/beta_services.txt" 2>&1; then
    log "    ✓ Beta services backed up"
else
    log "    ⚠ Beta services backup failed (services may not exist)"
fi

# Copy local systemd service files (templates)
if [ -d "$REPO_ROOT/scripts/systemd" ]; then
    cp -a "$REPO_ROOT/scripts/systemd" "$VM_SERVICES_DIR/local_systemd_templates" 2>/dev/null || true
    log "    ✓ Local systemd templates backed up"
fi

# ============================================================================
# Phase 3: Backup Codebase (Core Only - No Unnecessary Data)
# ============================================================================

log "Phase 3: Creating codebase backup (excluding unnecessary data)..."

CODEBASE_ARCHIVE="$BACKUP_DEST/CODEBASE_${REPO_NAME}_${TIMESTAMP}.${COMPRESS_EXT}"

# Build exclude list
EXCLUDE_FILE=$(mktemp)
cat > "$EXCLUDE_FILE" <<EOF
.git
.venv
venv
__pycache__
*.pyc
*.pyo
node_modules
.cache
.pytest_cache
.mypy_cache
BACKUPS
.BACKUPS
.sandbox
sandbox
.DS_Store
*.swp
*.swo
.env
.env.*
*.key
*.pem
*.p12
id_rsa
id_ed25519
*.log
*.out
*.err
*.tgz
*.tar.gz
*.zip
*.bundle
ARTIFACTS
artifacts
logs
tmp
temp
EOF

# Create tarball
cd "$REPO_ROOT"
if [ "$COMPRESS_EXT" = "tar.zst" ]; then
    tar --exclude-from="$EXCLUDE_FILE" -cf - . 2>/dev/null | $COMPRESS_CMD > "$CODEBASE_ARCHIVE"
else
    tar --exclude-from="$EXCLUDE_FILE" -czf "$CODEBASE_ARCHIVE" . 2>/dev/null
fi

rm -f "$EXCLUDE_FILE"

CODEBASE_SIZE=$(du -h "$CODEBASE_ARCHIVE" | cut -f1)
log "  ✓ Codebase archive: $CODEBASE_SIZE"

# ============================================================================
# Phase 4: Create Git Bundle
# ============================================================================

log "Phase 4: Creating git bundle..."

if [ -d "$REPO_ROOT/.git" ]; then
    GIT_BUNDLE="$BACKUP_DEST/${REPO_NAME}_${TIMESTAMP}_${GIT_SHA_SHORT}.git.bundle"
    
    if cd "$REPO_ROOT" && git bundle create "$GIT_BUNDLE" --all 2>/dev/null; then
        GIT_BUNDLE_SIZE=$(du -h "$GIT_BUNDLE" | cut -f1)
        log "  ✓ Git bundle: $GIT_BUNDLE_SIZE"
    else
        log "  ⚠ Failed to create git bundle (continuing)"
        GIT_BUNDLE=""
    fi
else
    log "  ⚠ Skipping git bundle (no .git directory)"
    GIT_BUNDLE=""
fi

# ============================================================================
# Phase 5: Create Backup Manifest
# ============================================================================

log "Phase 5: Creating backup manifest..."

MANIFEST_FILE="$BACKUP_DEST/MANIFEST.md"
cat > "$MANIFEST_FILE" <<EOF
# System Replication Backup Manifest

**Timestamp:** ${TIMESTAMP}  
**Git SHA:** ${GIT_SHA}  
**Project:** ${PROJECT}  
**Zone:** ${ZONE}

## Contents

### 1. VM Infrastructure Configs (\`vm_configs/\`)
- \`alpha_vm.yaml\` - Alpha VM (${ALPHA_VM}) configuration
- \`beta_vm.yaml\` - Beta VM (${BETA_VM}) configuration
- \`firewall_rules.yaml\` - GCP firewall rules
- \`networks.yaml\` - GCP network configurations

### 2. VM Services (\`vm_services/\`)
- \`alpha_services.txt\` - Alpha VM systemd service files
- \`beta_services.txt\` - Beta VM systemd service files
- \`local_systemd_templates/\` - Local systemd service templates

### 3. Codebase Archive
- \`CODEBASE_${REPO_NAME}_${TIMESTAMP}.${COMPRESS_EXT}\` - Complete codebase (excluding unnecessary data)
  - Size: ${CODEBASE_SIZE}
  - Excludes: .venv, node_modules, logs, caches, artifacts, large binaries

### 4. Git Bundle
- \`${REPO_NAME}_${TIMESTAMP}_${GIT_SHA_SHORT}.git.bundle\` - Complete git history
  - Size: ${GIT_BUNDLE_SIZE:-N/A}
  - Restore with: \`git clone <bundle_file> <target_dir>\`

## Replication Steps

1. **Restore Git Repository:**
   \`\`\`bash
   git clone ${REPO_NAME}_${TIMESTAMP}_${GIT_SHA_SHORT}.git.bundle gcloud-system
   cd gcloud-system
   \`\`\`

2. **Review VM Configurations:**
   - Check \`vm_configs/alpha_vm.yaml\` and \`vm_configs/beta_vm.yaml\`
   - Review firewall rules in \`vm_configs/firewall_rules.yaml\`

3. **Deploy Services:**
   - Use systemd templates from \`vm_services/local_systemd_templates/\`
   - Or use service files from \`vm_services/alpha_services.txt\` (if backed up)

4. **Follow Deployment Documentation:**
   - See \`docs/runbooks/\` for deployment runbooks
   - See \`VM_DEPLOYMENT.md\` for VM deployment guide

## Files Excluded (Not Needed for Replication)

- Virtual environments (\`.venv/\`, \`venv/\`)
- Node modules (\`node_modules/\`)
- Build caches (\`.cache/\`, \`__pycache__/\`)
- Log files (\`*.log\`, \`*.out\`)
- Large artifacts and backups
- Sensitive files (\`.env\`, \`*.key\`, \`*.pem\`)
- Git directory (replaced by git bundle)

## Notes

- This backup is designed for system replication, not full file-level recovery
- VM service files are backed up if accessible via SSH/IAP
- Sensitive credentials are NOT included (must be configured separately)
- Large binaries and artifacts are excluded to keep backup size manageable
EOF

log "  ✓ Manifest created: MANIFEST.md"

# ============================================================================
# Phase 6: Create SHA256 Checksums
# ============================================================================

log "Phase 6: Creating checksums..."

CHECKSUM_FILE="$BACKUP_DEST/SHA256SUMS.txt"
cd "$BACKUP_DEST"
find . -type f -not -name "SHA256SUMS.txt" -not -name "MANIFEST.md" -exec sha256sum {} \; > "$CHECKSUM_FILE" 2>/dev/null || true
log "  ✓ Checksums created: SHA256SUMS.txt"

# ============================================================================
# Summary
# ============================================================================

log ""
log "=== Backup Complete ==="
log "Location: $BACKUP_DEST"
log ""
log "Contents:"
ls -lh "$BACKUP_DEST" | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}'
log ""
log "Total size:"
du -sh "$BACKUP_DEST" | cut -f1
log ""
log "✓ System replication backup complete"
log "✓ Review MANIFEST.md for replication instructions"
