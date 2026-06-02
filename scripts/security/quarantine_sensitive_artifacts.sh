#!/bin/bash
# quarantine_sensitive_artifacts.sh — NON-DESTRUCTIVE secrets quarantine
#
# WHAT IT DOES:
# - COPIES (never moves/deletes) sensitive files to QUARANTINE/<timestamp>/
# - Creates SHA256 manifest of files (paths + hashes only, NO contents)
# - Idempotent: safe to run multiple times
# - NEVER prints secret values
#
# USAGE:
#   bash scripts/security/quarantine_sensitive_artifacts.sh
#   DRY_RUN=1 bash scripts/security/quarantine_sensitive_artifacts.sh  # preview only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN="${DRY_RUN:-0}"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
QUARANTINE_DIR="QUARANTINE/${TIMESTAMP}"

echo "=== FXG AI-QUANT — Secrets Quarantine (NON-DESTRUCTIVE) ==="
echo "Timestamp: $TIMESTAMP"
echo "Repo root: $REPO_ROOT"
echo "Quarantine dir: $QUARANTINE_DIR"
echo "Dry run: $DRY_RUN"
echo ""

if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY RUN] No files will be copied. Preview only."
    echo ""
fi

# Create quarantine subdirectories
create_dirs() {
    if [ "$DRY_RUN" = "0" ]; then
        mkdir -p "$QUARANTINE_DIR"/{historical,service,ssh_keys,yaml_creds,env,other}
    fi
}

# Initialize manifest
MANIFEST_FILE="$QUARANTINE_DIR/MANIFEST.json"
MANIFEST_ENTRIES=""

# Add entry to manifest (path + sha256, never contents)
add_to_manifest() {
    local src_path="$1"
    local category="$2"
    local dest_path="$3"
    
    if [ -f "$src_path" ]; then
        local sha256
        sha256=$(shasum -a 256 "$src_path" 2>/dev/null | cut -d' ' -f1 || echo "UNREADABLE")
        local entry="{\"source\": \"$src_path\", \"category\": \"$category\", \"dest\": \"$dest_path\", \"sha256\": \"$sha256\"}"
        if [ -n "$MANIFEST_ENTRIES" ]; then
            MANIFEST_ENTRIES="$MANIFEST_ENTRIES,
    $entry"
        else
            MANIFEST_ENTRIES="$entry"
        fi
    fi
}

# Copy file to quarantine (with hash, never print contents)
quarantine_file() {
    local src_path="$1"
    local category="$2"
    local dest_subdir="$QUARANTINE_DIR/$category"
    
    if [ ! -f "$src_path" ]; then
        echo "  [SKIP] Not found: $src_path"
        return 0
    fi
    
    local filename
    filename=$(basename "$src_path")
    local dest_path="$dest_subdir/$filename"
    
    # Handle duplicates by adding hash prefix
    if [ -f "$dest_path" ] && [ "$DRY_RUN" = "0" ]; then
        local hash_prefix
        hash_prefix=$(shasum -a 256 "$src_path" | cut -c1-8)
        dest_path="$dest_subdir/${hash_prefix}_${filename}"
    fi
    
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [DRY] Would copy: $src_path -> $category/"
    else
        cp "$src_path" "$dest_path" 2>/dev/null || {
            echo "  [WARN] Could not copy: $src_path (may be unreadable)"
            return 0
        }
        echo "  [COPIED] $src_path -> $category/"
    fi
    
    add_to_manifest "$src_path" "$category" "$dest_path"
}

# === QUARANTINE CATEGORIES ===

echo "--- SSH Private Keys (CRITICAL) ---"
quarantine_file "cloud_declutter_v2/Oracle/ssh-key-2025-12-15.key" "ssh_keys"
quarantine_file "cloud_declutter_v2/Oracle/ssh-key-2025-12-01 (2).key" "ssh_keys"
# Find any other .key files
find . -maxdepth 5 -name "*.key" -type f 2>/dev/null | while read -r keyfile; do
    case "$keyfile" in
        ./QUARANTINE/*) continue ;;
        *) quarantine_file "$keyfile" "ssh_keys" ;;
    esac
done
echo ""

echo "--- Service Files with Hardcoded Env ---"
quarantine_file "ai_trading.service" "service"
quarantine_file "ai_trading_service_CORRECT.service" "service"
quarantine_file "ai_trading_service_FINAL.service" "service"
quarantine_file "ai_trading_service_ORIGINAL.service" "service"
quarantine_file "ai_trading_FIXED.service" "service"
quarantine_file "ai_trading_service_GROUND_TRUTH.service" "service"
quarantine_file "ai_trading_TEST.service" "service"
quarantine_file "automated_trading.service" "service"
quarantine_file "google-cloud-trading-system/systemd/agent-controller.service" "service"
echo ""

echo "--- Historical Forensic Files ---"
quarantine_file "FORENSIC_AUDIT_REPORT.json" "historical"
quarantine_file "forensic_snapshot/FXG_FORENSIC_REPORT.json" "historical"
quarantine_file "forensic_snapshot/FXG_ARCH_EVIDENCE.json" "historical"
quarantine_file "SYSTEM_MAP_GCLOUD_SYSTEM.json" "historical"
quarantine_file "ARTIFACTS/secrets_scan_redacted.json" "historical"
quarantine_file "ARTIFACTS/LOCAL_scan_summary.json" "historical"
quarantine_file "docs/forensics/BROKER_TOUCHPOINTS_CODE.md" "historical"
quarantine_file "docs/forensics/BROKER_TOUCHPOINTS.md" "historical"
echo ""

echo "--- Other Sensitive Artifacts ---"
# Any .env files not already in gitignore
find . -maxdepth 3 -name "*.env" -type f 2>/dev/null | grep -v QUARANTINE | while read -r envfile; do
    quarantine_file "$envfile" "env"
done
echo ""

# === WRITE MANIFEST ===

if [ "$DRY_RUN" = "0" ]; then
    create_dirs
    cat > "$MANIFEST_FILE" << EOF
{
  "quarantine_timestamp": "$TIMESTAMP",
  "repo_root": "$REPO_ROOT",
  "created_by": "quarantine_sensitive_artifacts.sh",
  "note": "Files COPIED (not moved). Originals remain in place but should be gitignored. SHA256 hashes provided for verification.",
  "files": [
    $MANIFEST_ENTRIES
  ]
}
EOF
    echo "--- Manifest written: $MANIFEST_FILE ---"
fi

# === UPDATE .gitignore ===

echo ""
echo "--- Checking .gitignore coverage ---"

GITIGNORE_ADDITIONS=""

check_gitignore() {
    local pattern="$1"
    if ! grep -qF "$pattern" .gitignore 2>/dev/null; then
        GITIGNORE_ADDITIONS="$GITIGNORE_ADDITIONS
$pattern"
        echo "  [MISSING] $pattern"
    else
        echo "  [OK] $pattern"
    fi
}

check_gitignore "QUARANTINE/"
check_gitignore "forensic_snapshot/"
check_gitignore "cloud_declutter_v2/Oracle/"

if [ -n "$GITIGNORE_ADDITIONS" ] && [ "$DRY_RUN" = "0" ]; then
    echo ""
    echo "--- Adding missing patterns to .gitignore ---"
    cat >> .gitignore << EOF

# === QUARANTINE (sensitive artifacts - added by remediation script) ===
QUARANTINE/
forensic_snapshot/
cloud_declutter_v2/Oracle/
EOF
    echo "[UPDATED] .gitignore with quarantine patterns"
fi

echo ""
echo "=== Quarantine Complete ==="
if [ "$DRY_RUN" = "1" ]; then
    echo "DRY RUN - no changes made. Run without DRY_RUN=1 to execute."
else
    echo "Files copied to: $QUARANTINE_DIR"
    echo "Manifest: $MANIFEST_FILE"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Review manifest for completeness"
    echo "2. Rotate any exposed credentials externally (OANDA/Telegram/Google)"
    echo "3. Verify .gitignore now covers all sensitive paths"
    echo "4. Run scripts/security/verify_repo_no_secrets.sh to confirm clean state"
fi
