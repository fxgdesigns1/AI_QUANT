#!/bin/bash
# FXG AI-QUANT — Backup Verification Script
# Validates backup integrity without extracting or decrypting
#
# Usage:
#   bash scripts/backup/verify_backup.sh <backup-directory>
#   LIST_CONTENTS=1 bash scripts/backup/verify_backup.sh <backup-directory>

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BACKUP_DIR="${1:-}"
LIST_CONTENTS="${LIST_CONTENTS:-0}"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup-directory>"
    echo ""
    echo "Example:"
    echo "  $0 BACKUPS/myhost/gcloud-system/20260104T120000Z"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Directory not found: $BACKUP_DIR"
    exit 1
fi

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo "[VERIFY] $*"
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
# Main Verification
# ============================================================================

cd "$BACKUP_DIR"

log "=== FXG AI-QUANT Backup Verification ==="
log "Directory: $BACKUP_DIR"
log ""

ERRORS=0

# ============================================================================
# Check Required Files
# ============================================================================

log "Phase 1: Checking required files..."

# MANIFEST.json
if [ -f "MANIFEST.json" ]; then
    log_ok "MANIFEST.json present"
else
    log_fail "MANIFEST.json missing"
    ERRORS=$((ERRORS + 1))
fi

# SHA256SUMS
if [ -f "SHA256SUMS" ]; then
    log_ok "SHA256SUMS present"
else
    log_fail "SHA256SUMS missing"
    ERRORS=$((ERRORS + 1))
fi

# NOTE.txt
if [ -f "NOTE.txt" ]; then
    log_ok "NOTE.txt present"
else
    log_warn "NOTE.txt missing (optional)"
fi

# CORE archive
CORE_FILE=$(ls CORE_*.tar.* 2>/dev/null | head -n 1 || true)
if [ -n "$CORE_FILE" ] && [ -f "$CORE_FILE" ]; then
    CORE_SIZE=$(du -h "$CORE_FILE" | cut -f1)
    log_ok "CORE archive present: $CORE_FILE ($CORE_SIZE)"
else
    log_fail "CORE archive missing"
    ERRORS=$((ERRORS + 1))
fi

# SENSITIVE_FILES_LIST.txt
if [ -f "SENSITIVE_FILES_LIST.txt" ]; then
    SENSITIVE_COUNT=$(wc -l < "SENSITIVE_FILES_LIST.txt" | tr -d ' ')
    log_ok "SENSITIVE_FILES_LIST.txt present ($SENSITIVE_COUNT files listed)"
else
    log_warn "SENSITIVE_FILES_LIST.txt missing (optional)"
fi

# Git bundle (optional)
GIT_BUNDLE=$(ls *.git.bundle 2>/dev/null | head -n 1 || true)
if [ -n "$GIT_BUNDLE" ] && [ -f "$GIT_BUNDLE" ]; then
    GIT_SIZE=$(du -h "$GIT_BUNDLE" | cut -f1)
    log_ok "Git bundle present: $GIT_BUNDLE ($GIT_SIZE)"
else
    log_warn "Git bundle not found (optional)"
fi

# Encrypted sensitive bundle (optional)
SENSITIVE_ENC=$(ls SENSITIVE_*.enc 2>/dev/null | head -n 1 || true)
if [ -n "$SENSITIVE_ENC" ] && [ -f "$SENSITIVE_ENC" ]; then
    SENS_SIZE=$(du -h "$SENSITIVE_ENC" | cut -f1)
    log_ok "Encrypted SENSITIVE bundle present: $SENSITIVE_ENC ($SENS_SIZE)"
else
    log_warn "Encrypted SENSITIVE bundle not found (optional - set BACKUP_PASSPHRASE to create)"
fi

log ""

# ============================================================================
# Verify Checksums
# ============================================================================

log "Phase 2: Verifying checksums..."

if [ -f "SHA256SUMS" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        if sha256sum -c SHA256SUMS --quiet 2>/dev/null; then
            log_ok "All checksums verified"
        else
            log_fail "Checksum verification failed"
            sha256sum -c SHA256SUMS 2>&1 | grep -v ': OK$' || true
            ERRORS=$((ERRORS + 1))
        fi
    elif command -v shasum >/dev/null 2>&1; then
        if shasum -a 256 -c SHA256SUMS --quiet 2>/dev/null; then
            log_ok "All checksums verified"
        else
            log_fail "Checksum verification failed"
            shasum -a 256 -c SHA256SUMS 2>&1 | grep -v ': OK$' || true
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_warn "No checksum tool available (sha256sum or shasum)"
    fi
else
    log_fail "Cannot verify checksums (SHA256SUMS missing)"
    ERRORS=$((ERRORS + 1))
fi

log ""

# ============================================================================
# Verify Git Bundle (if present)
# ============================================================================

if [ -n "$GIT_BUNDLE" ] && [ -f "$GIT_BUNDLE" ]; then
    log "Phase 3: Verifying git bundle..."
    
    if command -v git >/dev/null 2>&1; then
        if git bundle verify "$GIT_BUNDLE" >/dev/null 2>&1; then
            log_ok "Git bundle is valid"
            
            # Show bundle info
            BUNDLE_HEADS=$(git bundle list-heads "$GIT_BUNDLE" 2>/dev/null | wc -l | tr -d ' ')
            log "  Contains $BUNDLE_HEADS refs"
        else
            log_fail "Git bundle verification failed"
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_warn "git not available, skipping bundle verification"
    fi
    
    log ""
fi

# ============================================================================
# Parse and Display Manifest
# ============================================================================

if [ -f "MANIFEST.json" ]; then
    log "Phase 4: Manifest contents..."
    
    if command -v python3 >/dev/null 2>&1; then
        python3 << 'PY'
import json
from pathlib import Path

try:
    manifest = json.loads(Path("MANIFEST.json").read_text())
    print(f"  Timestamp: {manifest.get('timestamp_utc', 'N/A')}")
    print(f"  Hostname: {manifest.get('hostname', 'N/A')}")
    print(f"  Repo: {manifest.get('repo_name', 'N/A')}")
    print(f"  Git SHA: {manifest.get('git_sha', 'N/A')[:12]}...")
    print(f"  Include artifacts: {manifest.get('include_artifacts', False)}")
    print(f"  Encrypted: {manifest.get('encrypted', False)}")
    print(f"  Compression: {manifest.get('compression', 'N/A')}")
except Exception as e:
    print(f"  Error parsing manifest: {e}")
PY
    else
        log "  (python3 not available for JSON parsing)"
        head -20 MANIFEST.json
    fi
    
    log ""
fi

# ============================================================================
# List Archive Contents (Optional)
# ============================================================================

if [ "$LIST_CONTENTS" = "1" ] && [ -n "$CORE_FILE" ]; then
    log "Phase 5: Archive contents (first 50 entries)..."
    
    if [[ "$CORE_FILE" == *.tar.gz ]]; then
        tar -tzf "$CORE_FILE" 2>/dev/null | head -50
    elif [[ "$CORE_FILE" == *.tar.zst ]]; then
        if command -v zstd >/dev/null 2>&1; then
            zstd -d -c "$CORE_FILE" 2>/dev/null | tar -t | head -50
        else
            log_warn "zstd not available for listing"
        fi
    fi
    
    log ""
fi

# ============================================================================
# Summary
# ============================================================================

log "=== Verification Summary ==="

if [ "$ERRORS" -eq 0 ]; then
    log_ok "Backup verification PASSED"
    exit 0
else
    log_fail "Backup verification FAILED ($ERRORS errors)"
    exit 1
fi
