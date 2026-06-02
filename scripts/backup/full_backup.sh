#!/bin/bash
# FXG AI-QUANT — Full Backup Script (Non-Destructive)
# Creates categorized backups: CORE + optional encrypted SENSITIVE + git bundle
# 
# Usage:
#   bash scripts/backup/full_backup.sh
#   INCLUDE_ARTIFACTS=1 bash scripts/backup/full_backup.sh
#   BACKUP_PASSPHRASE="secret" bash scripts/backup/full_backup.sh
#
# Environment variables:
#   BACKUP_DIR          - Override backup destination (default: BACKUPS/)
#   INCLUDE_ARTIFACTS   - Set to 1 to include ARTIFACTS/ directory
#   BACKUP_PASSPHRASE   - Set to encrypt sensitive bundle (never printed)
#   EXCLUDE_EXTRA       - Comma-separated extra directories to exclude

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"
HOSTNAME_SHORT="$(hostname -s 2>/dev/null || hostname | cut -d. -f1)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Backup destination
BACKUP_BASE="${BACKUP_DIR:-$REPO_ROOT/BACKUPS}"
BACKUP_DEST="$BACKUP_BASE/$HOSTNAME_SHORT/$REPO_NAME/$TIMESTAMP"

# Options
INCLUDE_ARTIFACTS="${INCLUDE_ARTIFACTS:-0}"
EXCLUDE_EXTRA="${EXCLUDE_EXTRA:-}"

# Compression: prefer zstd, fallback to gzip
if command -v zstd >/dev/null 2>&1; then
    COMPRESS_CMD="zstd -T0 -19"
    COMPRESS_EXT="tar.zst"
    DECOMPRESS_CMD="zstd -d"
else
    COMPRESS_CMD="gzip -9"
    COMPRESS_EXT="tar.gz"
    DECOMPRESS_CMD="gunzip"
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

# Redact sensitive values from environment
redact_env() {
    env | sort | while IFS='=' read -r name value; do
        case "$name" in
            *KEY*|*TOKEN*|*SECRET*|*PASSWORD*|*PASSPHRASE*|*CREDENTIAL*|*AUTH*)
                if [ -n "$value" ]; then
                    echo "$name=***REDACTED***"
                else
                    echo "$name="
                fi
                ;;
            *)
                # Redact anything that looks like a token (long alphanumeric)
                if echo "$value" | grep -qE '^[a-zA-Z0-9_-]{30,}$'; then
                    echo "$name=***REDACTED***"
                else
                    echo "$name=$value"
                fi
                ;;
        esac
    done
}

# Check if a file is sensitive
is_sensitive_file() {
    local file="$1"
    local name="$(basename "$file")"
    
    # Match sensitive patterns
    case "$name" in
        .env|.env.*|*.env)
            return 0
            ;;
        *.key|*.pem|*.p12|*.pfx|*.jks)
            return 0
            ;;
        *credential*|*secret*|*token*)
            return 0
            ;;
        id_rsa|id_ed25519|id_ecdsa)
            return 0
            ;;
    esac
    
    # Check file content for sensitive markers (first 100 bytes only)
    if head -c 100 "$file" 2>/dev/null | grep -q 'BEGIN.*PRIVATE\|BEGIN RSA\|BEGIN EC\|BEGIN OPENSSH'; then
        return 0
    fi
    
    return 1
}

# ============================================================================
# Main
# ============================================================================

cd "$REPO_ROOT"

log "=== FXG AI-QUANT Full Backup ==="
log "Repo: $REPO_NAME"
log "Host: $HOSTNAME_SHORT"
log "Timestamp: $TIMESTAMP"
log "Destination: $BACKUP_DEST"
log ""

# Create backup directory
mkdir -p "$BACKUP_DEST"

# Create metadata directory
META_DIR="$BACKUP_DEST/__BACKUP_META__"
mkdir -p "$META_DIR"

# ============================================================================
# Phase 1: Collect Metadata
# ============================================================================

log "Phase 1: Collecting metadata..."

# System info
{
    echo "hostname: $(hostname)"
    echo "uname: $(uname -a)"
    echo "date_utc: $(date -u)"
    echo "user: $(whoami)"
    echo "pwd: $(pwd)"
    echo "shell: $SHELL"
    if command -v python3 >/dev/null 2>&1; then
        echo "python3: $(python3 --version 2>&1)"
    fi
} > "$META_DIR/system_info.txt"

# Git info
if [ -d .git ]; then
    GIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
    GIT_SHA_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    git status --porcelain > "$META_DIR/git_status.txt" 2>/dev/null || true
    git log --oneline -20 > "$META_DIR/git_log_recent.txt" 2>/dev/null || true
    echo "$GIT_SHA" > "$META_DIR/git_head.txt"
else
    GIT_SHA="no-git"
    GIT_SHA_SHORT="no-git"
fi

# Redacted environment snapshot
redact_env > "$META_DIR/env_redacted.txt"

# File count summary
find . -type f -not -path './.git/*' -not -path './BACKUPS/*' -not -path './.venv/*' -not -path './node_modules/*' 2>/dev/null | wc -l > "$META_DIR/file_count.txt" || echo "0" > "$META_DIR/file_count.txt"

log "  Metadata collected"

# ============================================================================
# Phase 2: Identify Sensitive Files
# ============================================================================

log "Phase 2: Identifying sensitive files..."

SENSITIVE_LIST="$BACKUP_DEST/SENSITIVE_FILES_LIST.txt"
> "$SENSITIVE_LIST"

# Find sensitive files
while IFS= read -r -d '' file; do
    rel_path="${file#./}"
    if is_sensitive_file "$file"; then
        echo "$rel_path" >> "$SENSITIVE_LIST"
    fi
done < <(find . -type f \
    -not -path './.git/*' \
    -not -path './BACKUPS/*' \
    -not -path './.venv/*' \
    -not -path './venv/*' \
    -not -path './node_modules/*' \
    -not -path './__pycache__/*' \
    -print0 2>/dev/null)

SENSITIVE_COUNT=$(wc -l < "$SENSITIVE_LIST" | tr -d ' ')
log "  Found $SENSITIVE_COUNT sensitive file candidates"

# ============================================================================
# Phase 3: Create CORE Bundle
# ============================================================================

log "Phase 3: Creating CORE bundle..."

CORE_ARCHIVE="$BACKUP_DEST/CORE_${REPO_NAME}_${TIMESTAMP}.${COMPRESS_EXT}"

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
EOF

# Add ARTIFACTS exclusion if not requested
if [ "$INCLUDE_ARTIFACTS" != "1" ]; then
    echo "ARTIFACTS" >> "$EXCLUDE_FILE"
fi

# Add extra exclusions
if [ -n "$EXCLUDE_EXTRA" ]; then
    echo "$EXCLUDE_EXTRA" | tr ',' '\n' >> "$EXCLUDE_FILE"
fi

# Create tarball
if [ "$COMPRESS_EXT" = "tar.zst" ]; then
    tar --exclude-from="$EXCLUDE_FILE" -cf - . 2>/dev/null | $COMPRESS_CMD > "$CORE_ARCHIVE"
else
    tar --exclude-from="$EXCLUDE_FILE" -czf "$CORE_ARCHIVE" . 2>/dev/null
fi

rm -f "$EXCLUDE_FILE"

CORE_SIZE=$(du -h "$CORE_ARCHIVE" | cut -f1)
log "  CORE archive: $CORE_SIZE"

# ============================================================================
# Phase 4: Create Git Bundle (if applicable)
# ============================================================================

if [ -d .git ]; then
    log "Phase 4: Creating git bundle..."
    
    GIT_BUNDLE="$BACKUP_DEST/${REPO_NAME}_${HOSTNAME_SHORT}_${TIMESTAMP}_${GIT_SHA_SHORT}.git.bundle"
    
    if git bundle create "$GIT_BUNDLE" --all 2>/dev/null; then
        GIT_BUNDLE_SIZE=$(du -h "$GIT_BUNDLE" | cut -f1)
        log "  Git bundle: $GIT_BUNDLE_SIZE"
    else
        log "  WARNING: Failed to create git bundle (continuing)"
        GIT_BUNDLE=""
    fi
else
    log "Phase 4: Skipping git bundle (no .git directory)"
    GIT_BUNDLE=""
fi

# ============================================================================
# Phase 5: Create Encrypted Sensitive Bundle (if passphrase provided)
# ============================================================================

SENSITIVE_ARCHIVE=""
ENCRYPTED=false

if [ -n "${BACKUP_PASSPHRASE:-}" ] && [ "$SENSITIVE_COUNT" -gt 0 ]; then
    if command -v openssl >/dev/null 2>&1; then
        log "Phase 5: Creating encrypted SENSITIVE bundle..."
        
        SENSITIVE_TAR="$BACKUP_DEST/SENSITIVE_${REPO_NAME}_${TIMESTAMP}.tar.gz"
        SENSITIVE_ARCHIVE="$SENSITIVE_TAR.enc"
        
        # Create tarball of sensitive files
        tar -czf "$SENSITIVE_TAR" -T "$SENSITIVE_LIST" 2>/dev/null || true
        
        # Encrypt with AES-256-CBC
        openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
            -salt -in "$SENSITIVE_TAR" -out "$SENSITIVE_ARCHIVE" \
            -pass env:BACKUP_PASSPHRASE 2>/dev/null
        
        # Remove unencrypted tarball
        rm -f "$SENSITIVE_TAR"
        
        ENCRYPTED=true
        SENSITIVE_SIZE=$(du -h "$SENSITIVE_ARCHIVE" | cut -f1)
        log "  Encrypted SENSITIVE archive: $SENSITIVE_SIZE"
    else
        log "Phase 5: Skipping encryption (openssl not available)"
    fi
elif [ "$SENSITIVE_COUNT" -gt 0 ]; then
    log "Phase 5: Skipping SENSITIVE bundle (no BACKUP_PASSPHRASE set)"
    log "  Set BACKUP_PASSPHRASE to create encrypted sensitive backup"
else
    log "Phase 5: Skipping SENSITIVE bundle (no sensitive files found)"
fi

# ============================================================================
# Phase 6: Generate Checksums and Manifest
# ============================================================================

log "Phase 6: Generating checksums and manifest..."

cd "$BACKUP_DEST"

# SHA256 checksums
> SHA256SUMS

# Use find to safely iterate over files
for pattern in "*.tar.*" "*.git.bundle" "*.enc" "SENSITIVE_FILES_LIST.txt"; do
    for f in $pattern; do
        if [ -f "$f" ]; then
            if command -v sha256sum >/dev/null 2>&1; then
                sha256sum "$f" >> SHA256SUMS
            elif command -v shasum >/dev/null 2>&1; then
                shasum -a 256 "$f" >> SHA256SUMS
            fi
        fi
    done 2>/dev/null || true
done

# Manifest JSON
cat > MANIFEST.json <<EOF
{
  "version": "1.0.0",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hostname": "$HOSTNAME_SHORT",
  "repo_name": "$REPO_NAME",
  "repo_root": "$REPO_ROOT",
  "git_sha": "$GIT_SHA",
  "files": {
    "core": "$(basename "$CORE_ARCHIVE")",
    "sensitive": "$([ -n "$SENSITIVE_ARCHIVE" ] && basename "$SENSITIVE_ARCHIVE" || echo "null")",
    "git_bundle": "$([ -n "$GIT_BUNDLE" ] && basename "$GIT_BUNDLE" || echo "null")"
  },
  "checksums": "SHA256SUMS",
  "include_artifacts": $([ "$INCLUDE_ARTIFACTS" = "1" ] && echo "true" || echo "false"),
  "encrypted": $ENCRYPTED,
  "sensitive_file_count": $SENSITIVE_COUNT,
  "compression": "$COMPRESS_EXT"
}
EOF

# Note file
cat > NOTE.txt <<EOF
FXG AI-QUANT Backup
===================
Created: $(date -u)
Host: $HOSTNAME_SHORT
Repo: $REPO_NAME
Git SHA: $GIT_SHA

Contents:
- CORE archive: $(basename "$CORE_ARCHIVE")
- Git bundle: $([ -n "$GIT_BUNDLE" ] && basename "$GIT_BUNDLE" || echo "N/A")
- Sensitive files: $SENSITIVE_COUNT candidates listed
EOF

if [ "$ENCRYPTED" = "true" ]; then
    cat >> NOTE.txt <<EOF

Encrypted Sensitive Bundle
--------------------------
File: $(basename "$SENSITIVE_ARCHIVE")
Algorithm: AES-256-CBC with PBKDF2 (100k iterations)

To decrypt:
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \\
    -in $(basename "$SENSITIVE_ARCHIVE") \\
    -out SENSITIVE_decrypted.tar.gz
  (enter passphrase when prompted)
EOF
fi

cat >> NOTE.txt <<EOF

Verification:
  sha256sum -c SHA256SUMS

Restore CORE:
  tar -xzf $(basename "$CORE_ARCHIVE") -C /path/to/target

Restore Git:
  git clone $([ -n "$GIT_BUNDLE" ] && basename "$GIT_BUNDLE" || echo "N/A") restored-repo
EOF

log "  Manifest and checksums written"

# ============================================================================
# Summary
# ============================================================================

cd "$REPO_ROOT"

log ""
log "=== Backup Complete ==="
log "Location: $BACKUP_DEST"
log ""
log "Files created:"
ls -la "$BACKUP_DEST" | grep -v '^d' | grep -v '^total' | while read -r line; do
    log "  $line"
done
log ""
log "Verify with: bash scripts/backup/verify_backup.sh \"$BACKUP_DEST\""

# Output backup path for scripting
echo "$BACKUP_DEST"
