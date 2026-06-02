#!/usr/bin/env bash
# Deploy fixed pull_signals.ps1 to Windows VM
# Fixed threshold from 1000 bytes to 100 bytes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PS1_FILE="$SCRIPT_DIR/windows/pull_signals.ps1"
WINDOWS_TARGET_PATH="C:\\FXG\\pull_signals.ps1"
WINDOWS_BACKUP_PATH="C:\\FXG\\pull_signals_backup_$(date +%Y%m%d_%H%M%S).ps1"

echo "=== Deploying Fixed pull_signals.ps1 to Windows VM ==="
echo "Local file: $LOCAL_PS1_FILE"
echo "Target path: $WINDOWS_TARGET_PATH"

# Check if local file exists
if [[ ! -f "$LOCAL_PS1_FILE" ]]; then
    echo "ERROR: Local PowerShell file not found: $LOCAL_PS1_FILE"
    exit 1
fi

echo "✅ Local PowerShell file found"

# Backup existing file on Windows
echo "Creating backup of existing pull_signals.ps1..."
gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance \
    --command="powershell -Command \"if (Test-Path 'C:\\FXG\\pull_signals.ps1') { Copy-Item 'C:\\FXG\\pull_signals.ps1' '$WINDOWS_BACKUP_PATH' -Force; Write-Output 'Backup created: $WINDOWS_BACKUP_PATH' } else { Write-Output 'No existing file to backup' }\"" \
    --project fxg-ai-trading

# Deploy new file
echo "Deploying new pull_signals.ps1..."
gcloud compute scp --tunnel-through-iap --zone us-central1-a \
    "$LOCAL_PS1_FILE" \
    fxg-windows-vm-instance:"$WINDOWS_TARGET_PATH" \
    --project fxg-ai-trading

if [[ $? -eq 0 ]]; then
    echo "✅ Successfully deployed pull_signals.ps1"
else
    echo "❌ Failed to deploy pull_signals.ps1"
    exit 1
fi

# Verify deployment
echo "Verifying deployment..."
gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance \
    --command="powershell -Command \"if (Test-Path '$WINDOWS_TARGET_PATH') { Write-Output 'File exists'; Get-Item '$WINDOWS_TARGET_PATH' | Select-Object Name,Length,LastWriteTime } else { Write-Output 'File not found' }\"" \
    --project fxg-ai-trading

# Check if FXG service exists and restart it
echo "Checking and restarting FXG service..."
gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance \
    --command="powershell -Command \"
        \$service = Get-Service -Name 'FXGPullSignals' -ErrorAction SilentlyContinue
        if (\$service) {
            Write-Output 'FXGPullSignals service found, restarting...'
            Restart-Service -Name 'FXGPullSignals' -Force
            Start-Sleep -Seconds 2
            \$status = Get-Service -Name 'FXGPullSignals'
            Write-Output 'Service status: ' + \$status.Status
        } else {
            Write-Output 'FXGPullSignals service not found'
            Write-Output 'You may need to install/register the service manually'
        }
    \"" \
    --project fxg-ai-trading

echo "=== Deployment Complete ==="
echo "Summary of changes:"
echo "- Fixed threshold from 1000 bytes to 100 bytes"
echo "- Enhanced error handling and logging"
echo "- Added health checks and connectivity tests"
echo ""
echo "Next steps:"
echo "1. Verify the service is running properly"
echo "2. Monitor C:\\FXG\\logs\\pull_signals.log for any issues"
echo "3. Test signal pulling functionality"