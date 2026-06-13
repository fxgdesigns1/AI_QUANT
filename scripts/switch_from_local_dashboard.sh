#!/bin/bash
# Helper script to restore original React app from local dashboard mode

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN_JSX="$PROJECT_ROOT/frontend/fxg-dashboard/src/main.jsx"
BACKUP_JSX="$PROJECT_ROOT/frontend/fxg-dashboard/src/main.jsx.backup"

if [ ! -f "$BACKUP_JSX" ]; then
    echo "⚠️  No backup found - not in local dashboard mode"
    exit 0
fi

# Restore original
cp "$BACKUP_JSX" "$MAIN_JSX"
rm "$BACKUP_JSX"

echo "✅ Restored original main.jsx"
echo "   Removed backup file"
