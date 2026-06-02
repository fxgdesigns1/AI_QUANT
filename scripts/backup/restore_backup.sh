#!/bin/bash
# FXG AI-QUANT — Backup Restore Script
# Safely restores backups with dry-run mode by default
#
# Usage:
#   bash scripts/backup/restore_backup.sh <backup-directory>              # Dry-run
#   DRY_RUN=0 bash scripts/backup/restore_backup.sh <backup-dir> <target> # Actual restore
#   DRY_RUN=0 FORCE=1 bash scripts/backup/restore_backup.sh <dir> <target> # Force overwrite

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BACKUP_DIR="${1:-}"
TARGET_DIR="${2:-./restored}"

DRY_RUN="${DRY_RUN:-1}"
FORCE="${FORCE:-0}"
RESTORE_SENSITIVE="${RESTORE_SENSITIVE:-0}"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup-directory> [target-directory]"
    echo ""
    echo "Environment variables:"
    echo "  DRY_RUN=0          Actually perform restore (default: 1, dry-run only)"
    echo "  FORCE=1            Overwrite existing target directory"
    echo "  RESTORE_SENSITIVE=1 Attempt to decrypt and restore sensitive files"
    echo ""
    echo "Examples:"
    echo "  $0 BACKUPS/host/repo/20260104T120000Z                    # Dry-run"
    echo "  DRY_RUN=0 $0 BACKUPS/host/repo/20260104T120000Z ./target # Restore"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo "[RESTORE] $*"
}

log_dryrun() {
    echo "[DRY-RUN] $*"
}

log_ok() {
    echo "[✅] $*"
}

log_warn() {
    echo "[⚠️ ] $*"
}

log_fail() {
    echo "[❌] $*"
}

# ============================================================================
# Main
# ============================================================================

cd "$BACKUP_DIR"

log "=== FXG AI-QUANT Backup Restore ==="
log "Source: $BACKUP_DIR"
log "Target: $TARGET_DIR"
log "Mode: $([ "$DRY_RUN" = "1" ] && echo "DRY-RUN (no changes)" || echo "LIVE RESTORE")"
log ""

# ============================================================================
# Pre-flight Checks
# ============================================================================

log "Phase 1: Pre-flight checks..."

# Find CORE archive
CORE_FILE=$(ls CORE_*.tar.* 2>/dev/null | head -n 1 || true)
if [ -z "$CORE_FILE" ] || [ ! -f "$CORE_FILE" ]; then
    log_fail "CORE archive not found in backup"
    exit 1
fi
log_ok "CORE archive: $CORE_FILE"

# Check for git bundle
GIT_BUNDLE=$(ls *.git.bundle 2>/dev/null | head -n 1 || true)
if [ -n "$GIT_BUNDLE" ]; then
    log_ok "Git bundle: $GIT_BUNDLE"
fi

# Check for encrypted sensitive bundle
SENSITIVE_ENC=$(ls SENSITIVE_*.enc 2>/dev/null | head -n 1 || true)
if [ -n "$SENSITIVE_ENC" ]; then
    log_ok "Encrypted sensitive bundle: $SENSITIVE_ENC"
fi

# Check SHA256SUMS
if [ -f "SHA256SUMS" ]; then
    log_ok "Checksums file present"
else
    log_warn "No checksums file (cannot verify integrity)"
fi

log ""

# ============================================================================
# Verify Checksums
# ============================================================================

log "Phase 2: Verifying backup integrity..."

if [ -f "SHA256SUMS" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        if sha256sum -c SHA256SUMS --quiet 2>/dev/null; then
            log_ok "All checksums verified"
        else
            log_fail "Checksum verification failed!"
            if [ "$DRY_RUN" = "0" ] && [ "$FORCE" != "1" ]; then
                log_fail "Aborting restore. Use FORCE=1 to override."
                exit 1
            fi
        fi
    elif command -v shasum >/dev/null 2>&1; then
        if shasum -a 256 -c SHA256SUMS --quiet 2>/dev/null; then
            log_ok "All checksums verified"
        else
            log_fail "Checksum verification failed!"
            if [ "$DRY_RUN" = "0" ] && [ "$FORCE" != "1" ]; then
                log_fail "Aborting restore. Use FORCE=1 to override."
                exit 1
            fi
        fi
    else
        log_warn "No checksum tool available"
    fi
fi

log ""

# ============================================================================
# Verify Git Bundle (if present)
# ============================================================================

if [ -n "$GIT_BUNDLE" ]; then
    log "Phase 3: Verifying git bundle..."
    
    if command -v git >/dev/null 2>&1; then
        if git bundle verify "$GIT_BUNDLE" >/dev/null 2>&1; then
            log_ok "Git bundle is valid"
        else
            log_warn "Git bundle verification failed"
        fi
    fi
    
    log ""
fi

# ============================================================================
# Target Directory Check
# ============================================================================

log "Phase 4: Target directory check..."

if [ "$DRY_RUN" = "1" ]; then
    log_dryrun "Would restore to: $TARGET_DIR"
    
    if [ -d "$TARGET_DIR" ]; then
        log_dryrun "Target exists - would require FORCE=1 to overwrite"
    else
        log_dryrun "Target does not exist - would create it"
    fi
else
    # Actual restore checks
    if [ -d "$TARGET_DIR" ]; then
        if [ "$FORCE" = "1" ]; then
            log_warn "Target exists but FORCE=1 set - will overwrite"
        else
            log_fail "Target directory exists: $TARGET_DIR"
            log_fail "Use FORCE=1 to overwrite or choose a different target"
            exit 1
        fi
    fi
fi

log ""

# ============================================================================
# Restore Plan
# ============================================================================

log "Phase 5: Restore plan..."

log "Actions to perform:"
log "  1. Extract CORE archive to $TARGET_DIR"

if [ -n "$GIT_BUNDLE" ]; then
    log "  2. Git bundle available for: git clone $GIT_BUNDLE"
fi

if [ -n "$SENSITIVE_ENC" ] && [ "$RESTORE_SENSITIVE" = "1" ]; then
    log "  3. Decrypt and restore sensitive files (will prompt for passphrase)"
fi

log ""

# ============================================================================
# Execute Restore
# ============================================================================

if [ "$DRY_RUN" = "1" ]; then
    log "=== DRY-RUN Complete ==="
    log ""
    log "To perform actual restore:"
    log "  DRY_RUN=0 $0 \"$BACKUP_DIR\" \"$TARGET_DIR\""
    log ""
    log "To restore with sensitive files:"
    log "  DRY_RUN=0 RESTORE_SENSITIVE=1 $0 \"$BACKUP_DIR\" \"$TARGET_DIR\""
    exit 0
fi

log "Phase 6: Executing restore..."

# Create target directory
mkdir -p "$TARGET_DIR"

# Extract CORE archive
log "Extracting CORE archive..."

if [[ "$CORE_FILE" == *.tar.gz ]]; then
    tar -xzf "$CORE_FILE" -C "$TARGET_DIR"
elif [[ "$CORE_FILE" == *.tar.zst ]]; then
    if command -v zstd >/dev/null 2>&1; then
        zstd -d -c "$CORE_FILE" | tar -xf - -C "$TARGET_DIR"
    else
        log_fail "zstd not available for decompression"
        exit 1
    fi
else
    tar -xf "$CORE_FILE" -C "$TARGET_DIR"
fi

log_ok "CORE archive extracted"

# Restore metadata
if [ -d "__BACKUP_META__" ]; then
    cp -r "__BACKUP_META__" "$TARGET_DIR/"
    log_ok "Metadata restored"
fi

# Decrypt sensitive files (if requested)
if [ -n "$SENSITIVE_ENC" ] && [ "$RESTORE_SENSITIVE" = "1" ]; then
    log "Decrypting sensitive files..."
    log_warn "Enter passphrase when prompted (will not be stored):"
    
    SENSITIVE_TAR="${SENSITIVE_ENC%.enc}"
    
    if openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
        -in "$SENSITIVE_ENC" -out "$SENSITIVE_TAR"; then
        
        tar -xzf "$SENSITIVE_TAR" -C "$TARGET_DIR"
        rm -f "$SENSITIVE_TAR"
        log_ok "Sensitive files restored"
    else
        log_fail "Failed to decrypt sensitive files (wrong passphrase?)"
    fi
fi

# ============================================================================
# Summary
# ============================================================================

log ""
log "=== Restore Complete ==="
log "Target: $TARGET_DIR"
log ""
log "Restored contents:"
ls -la "$TARGET_DIR" | head -20

if [ -n "$GIT_BUNDLE" ]; then
    log ""
    log "To restore git history:"
    log "  cd $TARGET_DIR"
    log "  rm -rf .git  # if exists"
    log "  git clone $BACKUP_DIR/$GIT_BUNDLE temp-git"
    log "  mv temp-git/.git ."
    log "  rm -rf temp-git"
fi
