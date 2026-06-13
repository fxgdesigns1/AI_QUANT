#!/bin/bash
# AI-QUANT Retention Cleanup Script
# 
# Enforces retention policies to keep VMs lean:
# - Delete old /opt/ai-quant.prev.* beyond newest 1
# - Delete /tmp/backup_* older than 1 day
# - Delete stale /opt/ai-quant/runtime/.status_*.tmp older than 1 day
# - Keep /var/backups/ai-quant/*.tgz max 0-1
#
# Run manually: sudo bash scripts/retention_cleanup.sh
# Or via systemd timer: ai-quant-retention.timer

set -euo pipefail

echo "=== AI-QUANT Retention Cleanup ==="
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

CLEANED_COUNT=0
FREED_SPACE=0

# 1. Clean old /opt/ai-quant.prev.* directories (keep only newest 1)
echo "[1] Cleaning old /opt/ai-quant.prev.* directories..."
if [ -d /opt ]; then
    # Find all /opt/ai-quant.prev.* directories, sort by modification time (newest first)
    OLD_DIRS=$(find /opt -maxdepth 1 -type d -name 'ai-quant.prev.*' -printf '%T@ %p\n' 2>/dev/null | sort -rn | tail -n +2 | cut -d' ' -f2- || true)
    
    if [ -n "$OLD_DIRS" ]; then
        while IFS= read -r dir; do
            if [ -d "$dir" ]; then
                SIZE=$(du -sb "$dir" 2>/dev/null | cut -f1 || echo "0")
                echo "  Deleting: $dir (size: $(numfmt --to=iec-i --suffix=B "$SIZE" 2>/dev/null || echo "$SIZE bytes"))"
                rm -rf "$dir"
                CLEANED_COUNT=$((CLEANED_COUNT + 1))
                FREED_SPACE=$((FREED_SPACE + SIZE))
            fi
        done <<< "$OLD_DIRS"
    else
        echo "  No old deploy directories found"
    fi
else
    echo "  /opt directory not found (skipping)"
fi

# 2. Clean /tmp/backup_* older than 1 day
echo ""
echo "[2] Cleaning /tmp/backup_* older than 1 day..."
if [ -d /tmp ]; then
    # Find backup directories older than 1 day
    OLD_BACKUPS=$(find /tmp -maxdepth 1 -type d -name 'backup_*' -mtime +1 2>/dev/null || true)
    
    if [ -n "$OLD_BACKUPS" ]; then
        while IFS= read -r dir; do
            if [ -d "$dir" ]; then
                SIZE=$(du -sb "$dir" 2>/dev/null | cut -f1 || echo "0")
                echo "  Deleting: $dir (older than 1 day, size: $(numfmt --to=iec-i --suffix=B "$SIZE" 2>/dev/null || echo "$SIZE bytes"))"
                rm -rf "$dir"
                CLEANED_COUNT=$((CLEANED_COUNT + 1))
                FREED_SPACE=$((FREED_SPACE + SIZE))
            fi
        done <<< "$OLD_BACKUPS"
    else
        echo "  No old /tmp/backup_* directories found"
    fi
else
    echo "  /tmp directory not found (skipping)"
fi

# 3. Clean stale /opt/ai-quant/runtime/.status_*.tmp older than 1 day
echo ""
echo "[3] Cleaning stale /opt/ai-quant/runtime/.status_*.tmp files..."
if [ -d /opt/ai-quant/runtime ]; then
    # Find .status_*.tmp files older than 1 day
    OLD_TMP=$(find /opt/ai-quant/runtime -maxdepth 1 -type f -name '.status_*.tmp' -mtime +1 2>/dev/null || true)
    
    if [ -n "$OLD_TMP" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
                echo "  Deleting: $file (older than 1 day, size: $(numfmt --to=iec-i --suffix=B "$SIZE" 2>/dev/null || echo "$SIZE bytes"))"
                rm -f "$file"
                CLEANED_COUNT=$((CLEANED_COUNT + 1))
                FREED_SPACE=$((FREED_SPACE + SIZE))
            fi
        done <<< "$OLD_TMP"
    else
        echo "  No stale .status_*.tmp files found"
    fi
else
    echo "  /opt/ai-quant/runtime directory not found (skipping)"
fi

# 4. Keep /var/backups/ai-quant/*.tgz max 0-1 (keep only newest if any exist)
echo ""
echo "[4] Cleaning /var/backups/ai-quant/*.tgz (keep max 1)..."
if [ -d /var/backups/ai-quant ]; then
    # Find all .tgz files, sort by modification time (newest first)
    BACKUP_FILES=$(find /var/backups/ai-quant -maxdepth 1 -type f -name '*.tgz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | tail -n +2 | cut -d' ' -f2- || true)
    
    if [ -n "$BACKUP_FILES" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
                echo "  Deleting: $file (size: $(numfmt --to=iec-i --suffix=B "$SIZE" 2>/dev/null || echo "$SIZE bytes"))"
                rm -f "$file"
                CLEANED_COUNT=$((CLEANED_COUNT + 1))
                FREED_SPACE=$((FREED_SPACE + SIZE))
            fi
        done <<< "$BACKUP_FILES"
    else
        echo "  No backup files to clean (keeping existing or none present)"
    fi
else
    echo "  /var/backups/ai-quant directory not found (skipping)"
fi

echo ""
echo "=== Cleanup Summary ==="
echo "Items cleaned: $CLEANED_COUNT"
echo "Space freed: $(numfmt --to=iec-i --suffix=B "$FREED_SPACE" 2>/dev/null || echo "$FREED_SPACE bytes")"
echo "Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
