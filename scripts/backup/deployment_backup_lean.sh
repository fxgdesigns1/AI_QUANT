#!/bin/bash
# FXG AI-QUANT — Lean Deployment Backup
# Creates categorized backup of essential deployment files only
# 
# Usage:
#   bash scripts/backup/deployment_backup_lean.sh

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

# Backup destination (use .BACKUPS to match existing structure)
BACKUP_BASE="${BACKUP_DIR:-$REPO_ROOT/.BACKUPS}"
BACKUP_DEST="$BACKUP_BASE/DEPLOYMENT_ESSENTIAL_${TIMESTAMP}"
mkdir -p "$BACKUP_DEST"

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
# Phase 1: Core Source Code
# ============================================================================

log "Phase 1: Backing up core source code..."

CORE_DIR="$BACKUP_DEST/01_core_source"
mkdir -p "$CORE_DIR"

cd "$REPO_ROOT"

# Copy essential source directories
for dir in src templates; do
    if [ -d "$dir" ]; then
        log "  Copying $dir/"
        cp -r "$dir" "$CORE_DIR/" 2>/dev/null || log_error "Failed to copy $dir"
    fi
done

# Copy working system file
if [ -f "working_trading_system.py" ]; then
    cp "working_trading_system.py" "$CORE_DIR/" 2>/dev/null || log_error "Failed to copy working_trading_system.py"
fi

# Copy requirements
if [ -f "requirements.txt" ]; then
    cp "requirements.txt" "$CORE_DIR/" 2>/dev/null || log_error "Failed to copy requirements.txt"
fi

log "  ✓ Core source saved"

# ============================================================================
# Phase 2: Deployment Scripts & Systemd
# ============================================================================

log "Phase 2: Backing up deployment scripts and systemd services..."

DEPLOY_DIR="$BACKUP_DEST/02_deployment"
mkdir -p "$DEPLOY_DIR"

# Systemd services
if [ -d "scripts/systemd" ]; then
    log "  Copying systemd services"
    cp -r "scripts/systemd" "$DEPLOY_DIR/" 2>/dev/null || log_error "Failed to copy systemd"
fi

# Deployment scripts (critical ones)
DEPLOY_SCRIPTS=(
    "scripts/start_control_plane_clean.sh"
    "scripts/start_runner_clean.sh"
    "scripts/stop_control_plane.sh"
    "scripts/provision_vm.sh"
    "scripts/vm_bootstrap_control_plane.sh"
    "scripts/vm_bootstrap_deploy_verify.sh"
    "scripts/vm_deploy_gated.sh"
    "scripts/setup_cloudflare_tunnel.sh"
    "scripts/push_repo_to_vm.sh"
    "scripts/bringup_local_full.sh"
    "scripts/run_control_plane.sh"
    "scripts/dashboard_probe.py"
)

mkdir -p "$DEPLOY_DIR/scripts"
for script in "${DEPLOY_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        mkdir -p "$DEPLOY_DIR/$(dirname "$script")"
        cp "$script" "$DEPLOY_DIR/$script" 2>/dev/null || log_error "Failed to copy $script"
    fi
done

log "  ✓ Deployment scripts saved"

# ============================================================================
# Phase 3: Configuration Files
# ============================================================================

log "Phase 3: Backing up configuration files..."

CONFIG_DIR="$BACKUP_DEST/03_configuration"
mkdir -p "$CONFIG_DIR"

# Runtime config (examples only, no secrets)
if [ -d "runtime" ]; then
    log "  Copying runtime configs (examples)"
    mkdir -p "$CONFIG_DIR/runtime"
    for file in runtime/config.example.yaml runtime/config.yaml; do
        if [ -f "$file" ]; then
            cp "$file" "$CONFIG_DIR/$file" 2>/dev/null || true
        fi
    done
fi

# .env.example (no actual .env files)
if [ -f ".env.example" ]; then
    cp ".env.example" "$CONFIG_DIR/" 2>/dev/null || true
fi

log "  ✓ Configuration files saved"

# ============================================================================
# Phase 4: Essential Documentation
# ============================================================================

log "Phase 4: Backing up essential documentation..."

DOCS_DIR="$BACKUP_DEST/04_documentation"
mkdir -p "$DOCS_DIR"

# Essential docs only
ESSENTIAL_DOCS=(
    "docs/SYSTEM_STATUS_AND_PLAN_2026.md"
    "docs/DASHBOARD_INVENTORY_ISSUES.md"
    "docs/DASHBOARD_FIXES_APPLIED.md"
    "docs/runbooks/RUNNER_AND_ACCOUNTS.md"
    "docs/runbooks/CLOUD_DEPLOY_FULL.md"
    "README.md"
)

for doc in "${ESSENTIAL_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        mkdir -p "$DOCS_DIR/$(dirname "$doc")"
        cp "$doc" "$DOCS_DIR/$doc" 2>/dev/null || log_error "Failed to copy $doc"
    fi
done

log "  ✓ Essential documentation saved"

# ============================================================================
# Phase 5: Verification Scripts
# ============================================================================

log "Phase 5: Backing up verification scripts..."

VERIFY_DIR="$BACKUP_DEST/05_verification"
mkdir -p "$VERIFY_DIR"

# Critical verification scripts
VERIFY_SCRIPTS=(
    "scripts/verify_control_plane.sh"
    "scripts/verify_paper_readiness.sh"
    "scripts/verify_alpha_e2e.sh"
    "scripts/verify_alpha_strategy_inputs.sh"
    "scripts/verify_dashboard_and_trades.sh"
)

mkdir -p "$VERIFY_DIR/scripts"
for script in "${VERIFY_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        mkdir -p "$VERIFY_DIR/$(dirname "$script")"
        cp "$script" "$VERIFY_DIR/$script" 2>/dev/null || log_error "Failed to copy $script"
    fi
done

log "  ✓ Verification scripts saved"

# ============================================================================
# Phase 6: Create Compressed Archive
# ============================================================================

log "Phase 6: Creating compressed archive..."

cd "$BACKUP_DEST/.."
ARCHIVE_NAME="DEPLOYMENT_ESSENTIAL_${REPO_NAME}_${TIMESTAMP}_${GIT_SHA_SHORT}.${COMPRESS_EXT}"

if [ "$COMPRESS_EXT" = "tar.zst" ]; then
    tar --exclude="*.pyc" --exclude="__pycache__" --exclude="*.swp" -cf - "$(basename "$BACKUP_DEST")" 2>/dev/null | $COMPRESS_CMD > "$ARCHIVE_NAME"
else
    tar --exclude="*.pyc" --exclude="__pycache__" --exclude="*.swp" -czf "$ARCHIVE_NAME" "$(basename "$BACKUP_DEST")" 2>/dev/null
fi

ARCHIVE_SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
log "  ✓ Archive created: $ARCHIVE_NAME ($ARCHIVE_SIZE)"

# ============================================================================
# Phase 7: Create Manifest
# ============================================================================

log "Phase 7: Creating manifest..."

cd "$BACKUP_DEST"

# Count files
FILE_COUNT=$(find . -type f | wc -l | tr -d ' ')

# Create manifest
cat > MANIFEST.txt <<EOF
FXG AI-QUANT — Lean Deployment Backup
======================================
Timestamp: $(date -u)
Git SHA: $GIT_SHA
Git SHA (short): $GIT_SHA_SHORT
Repo: $REPO_NAME
Archive: $ARCHIVE_NAME

Structure:
----------
01_core_source/          - Core source code (src/, templates/, working_trading_system.py)
02_deployment/           - Deployment scripts and systemd services
03_configuration/        - Configuration files (examples only, no secrets)
04_documentation/        - Essential documentation
05_verification/         - Verification scripts

Statistics:
-----------
Total files: $FILE_COUNT
Archive size: $ARCHIVE_SIZE

Restore:
--------
cd /path/to/restore/location
tar -xzf $ARCHIVE_NAME  # or tar -xzf if .tar.zst

EOF

log "  ✓ Manifest created"

# ============================================================================
# Phase 8: Create Checksums
# ============================================================================

log "Phase 8: Creating checksums..."

cd "$BACKUP_DEST/.."

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$ARCHIVE_NAME" > "${ARCHIVE_NAME}.sha256"
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$ARCHIVE_NAME" > "${ARCHIVE_NAME}.sha256"
fi

log "  ✓ Checksums created"

# ============================================================================
# Summary
# ============================================================================

cd "$REPO_ROOT"

log ""
log "=== Backup Complete ==="
log "Location: $BACKUP_DEST"
log "Archive: $BACKUP_DEST/../$ARCHIVE_NAME"
log "Size: $ARCHIVE_SIZE"
log "Files: $FILE_COUNT"
log ""
log "Verify with: sha256sum -c $ARCHIVE_NAME.sha256"
log ""

# Output backup path for scripting
echo "$BACKUP_DEST"
