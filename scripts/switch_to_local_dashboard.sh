#!/bin/bash
# Helper script to switch React app to local dashboard mode
# This temporarily backs up main.jsx and replaces it with LocalDashboardApp

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN_JSX="$PROJECT_ROOT/frontend/fxg-dashboard/src/main.jsx"
LOCAL_APP="$PROJECT_ROOT/frontend/fxg-dashboard/src/LocalDashboardApp.jsx"
BACKUP_JSX="$PROJECT_ROOT/frontend/fxg-dashboard/src/main.jsx.backup"

if [ ! -f "$LOCAL_APP" ]; then
    echo "❌ LocalDashboardApp.jsx not found"
    exit 1
fi

# Check if already switched
if [ -f "$BACKUP_JSX" ]; then
    echo "⚠️  Already in local dashboard mode"
    echo "   To switch back: ./scripts/switch_from_local_dashboard.sh"
    exit 0
fi

# Backup original main.jsx
if [ -f "$MAIN_JSX" ]; then
    cp "$MAIN_JSX" "$BACKUP_JSX"
    echo "✅ Backed up original main.jsx"
fi

# Create local dashboard version
cat > "$MAIN_JSX" << 'EOF'
/**
 * Local Dashboard Mode - Temporarily switched
 * To restore original: ./scripts/switch_from_local_dashboard.sh
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import LocalTradeDashboard from './components/LocalTradeDashboard';
import './LocalDashboard.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LocalTradeDashboard />
  </StrictMode>
);
EOF

echo "✅ Switched to local dashboard mode"
echo "   Start dashboard: cd frontend/fxg-dashboard && npm run dev"
