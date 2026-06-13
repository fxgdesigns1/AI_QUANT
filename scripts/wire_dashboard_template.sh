#!/bin/bash
# wire_dashboard_template.sh
# Safely wires in a new dashboard template for development and production
# Supports mock mode for safe development

set -euo pipefail

TEMPLATE_DIR="templates"
BACKUP_DIR=".BACKUPS/templates"
NEW_TEMPLATE="${1:-}"
MODE="${2:-dev}"  # dev or prod

if [ -z "$NEW_TEMPLATE" ]; then
    echo "Usage: $0 <template_file.html> [dev|prod]"
    echo ""
    echo "This script wires in a new dashboard template:"
    echo "  1. Backs up current template"
    echo "  2. Validates new template exists"
    echo "  3. Places template in correct location"
    echo "  4. Creates symlink or copies based on mode"
    echo ""
    echo "Examples:"
    echo "  $0 my_new_dashboard.html dev   # Development mode (local file)"
    echo "  $0 my_new_dashboard.html prod   # Production mode (will be served on VM)"
    exit 1
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Current active template
CURRENT_TEMPLATE="$TEMPLATE_DIR/forensic_command.html"
NEW_TEMPLATE_PATH=$(realpath "$NEW_TEMPLATE" 2>/dev/null || echo "$NEW_TEMPLATE")

# Validate new template exists
if [ ! -f "$NEW_TEMPLATE_PATH" ]; then
    echo "❌ Error: Template file not found: $NEW_TEMPLATE"
    exit 1
fi

echo "=== WIRING DASHBOARD TEMPLATE ==="
echo "New template: $NEW_TEMPLATE_PATH"
echo "Mode: $MODE"
echo ""

# Backup current template if it exists
if [ -f "$CURRENT_TEMPLATE" ]; then
    BACKUP_NAME="forensic_command_$(date +%Y%m%d_%H%M%S).html"
    echo "📦 Backing up current template to $BACKUP_DIR/$BACKUP_NAME"
    cp "$CURRENT_TEMPLATE" "$BACKUP_DIR/$BACKUP_NAME"
else
    echo "ℹ️  No existing template to backup"
fi

# Copy new template to templates directory
TEMPLATE_NAME="forensic_command.html"
if [ "$MODE" == "dev" ]; then
    echo "🔧 Development mode: Creating symlink"
    ln -sf "$NEW_TEMPLATE_PATH" "$CURRENT_TEMPLATE"
elif [ "$MODE" == "prod" ]; then
    echo "🚀 Production mode: Copying template"
    cp "$NEW_TEMPLATE_PATH" "$CURRENT_TEMPLATE"
else
    echo "❌ Error: Invalid mode '$MODE'. Use 'dev' or 'prod'"
    exit 1
fi

echo "✅ Template wired successfully!"
echo ""
echo "Next steps:"
if [ "$MODE" == "dev" ]; then
    echo "  1. Start mock API: python scripts/mock_api_server.py"
    echo "  2. Open dashboard: http://127.0.0.1:8787"
    echo "  3. Or start tunnel: ./scripts/dev_tunnel_alpha.sh"
elif [ "$MODE" == "prod" ]; then
    echo "  1. Deploy to VM: ./scripts/push_repo_to_vm.sh"
    echo "  2. Restart API on VM"
    echo "  3. Access via: http://127.0.0.1:28787 (via tunnel)"
fi
