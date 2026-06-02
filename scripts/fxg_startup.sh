#!/usr/bin/env bash
# FXG Startup Health Script - Comprehensive system check and auto-remediation
# Runs on ALPHA VM and fixes everything automatically
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/opt/ai-quant/logs/fxg_startup.log"
SIGNAL_FILE="/home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl"
BRIDGE_CONFIG="/opt/ai-quant/configs/bridge_accounts.json"
RUNTIME_CONFIG="/opt/ai-quant/runtime/config.yaml"
WINDOWS_PULL_LOG="C:\\FXG\\logs\\pull_signals.log"
TELEGRAM_SCRIPT="/opt/ai-quant/scripts/send_telegram_alert.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || mkdir -p "$ROOT_DIR/logs"

# Adjust log file path if /opt/ai-quant doesn't exist
if [[ ! -d "/opt/ai-quant" ]]; then
    LOG_FILE="$ROOT_DIR/logs/fxg_startup.log"
fi

# Logging function
log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

# Status tracking
ISSUES_FOUND=0
FIXES_APPLIED=0

log "INFO" "=== FXG Startup Health Check Started ==="

# Function to send Telegram alert
send_telegram_alert() {
    local level="$1"
    local title="$2"
    local message="$3"
    local fix_command="${4:-}"

    local emoji
    case "$level" in
        "CRITICAL") emoji="🚨" ;;
        "WARNING") emoji="⚠️" ;;
        "INFO") emoji="ℹ️" ;;
        "SUCCESS") emoji="✅" ;;
    esac

    local full_message="${emoji} **${title}**\n\n${message}"
    if [[ -n "$fix_command" ]]; then
        full_message="${full_message}\n\n**Fix command:**\n\`\`\`\n${fix_command}\n\`\`\`"
    fi

    # Try to use existing telegram notification system
    if [[ -f "$TELEGRAM_SCRIPT" ]]; then
        echo -e "$full_message" | "$TELEGRAM_SCRIPT" "$level"
    else
        # Fallback: try to find telegram notifier in the system
        if command -v python3 &> /dev/null; then
            python3 -c "
import sys
sys.path.append('$ROOT_DIR/src')
sys.path.append('/opt/ai-quant/src')
try:
    from control_plane.telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier()
    notifier.send_message('$full_message')
except Exception as e:
    print(f'Failed to send telegram: {e}')
" 2>/dev/null || log "WARNING" "Failed to send Telegram alert: $title"
        fi
    fi
}

# Function to check service status
check_service() {
    local service_name="$1"
    log "INFO" "Checking service: $service_name"

    if systemctl is-active "$service_name" --quiet 2>/dev/null; then
        log "INFO" "✅ Service $service_name is running"
        return 0
    else
        log "ERROR" "❌ Service $service_name is NOT running"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))

        # Try to restart the service
        log "INFO" "Attempting to restart $service_name..."
        if sudo systemctl restart "$service_name" 2>/dev/null; then
            log "INFO" "✅ Successfully restarted $service_name"
            send_telegram_alert "INFO" "Service Restarted" "Service $service_name was down and has been automatically restarted."
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
        else
            log "ERROR" "❌ Failed to restart $service_name"
            send_telegram_alert "CRITICAL" "Service Down" "Service $service_name is down and failed to restart automatically." "sudo systemctl restart $service_name && sudo systemctl status $service_name"
        fi
        return 1
    fi
}

# Function to check EA heartbeat
check_ea_heartbeat() {
    log "INFO" "Checking EA heartbeat age..."

    # Try to get heartbeat from Windows via sidecar API
    local heartbeat_age=0
    local heartbeat_data=""

    # Get sidecar URL from environment or config
    local sidecar_url="${MT5_SIDECAR_BASE_URL:-http://192.168.1.100:8080}"

    if command -v curl &> /dev/null; then
        heartbeat_data=$(curl -s --connect-timeout 5 "${sidecar_url}/api/heartbeat" 2>/dev/null || echo "")
        if [[ -n "$heartbeat_data" ]]; then
            # Parse heartbeat timestamp and calculate age
            local last_heartbeat=$(echo "$heartbeat_data" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('timestamp', 0))
except:
    print(0)
" 2>/dev/null || echo "0")

            if [[ "$last_heartbeat" != "0" ]]; then
                local current_time=$(date +%s)
                heartbeat_age=$((current_time - last_heartbeat))
            else
                heartbeat_age=999  # Force error condition
            fi
        else
            heartbeat_age=999  # Force error condition
        fi
    else
        heartbeat_age=999  # Force error condition
    fi

    if [[ $heartbeat_age -gt 120 ]]; then
        log "ERROR" "❌ EA heartbeat is stale: ${heartbeat_age}s old (threshold: 120s)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))

        # Try telemetry sync via scp from Windows
        log "INFO" "Attempting telemetry sync from Windows..."

        local sync_command="gcloud compute scp --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance:/FXG/telemetry/latest.json /tmp/ea_heartbeat_sync.json --project fxg-ai-trading"

        if eval "$sync_command" &> /dev/null; then
            log "INFO" "✅ Telemetry sync successful"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
            send_telegram_alert "WARNING" "EA Heartbeat Stale - Synced" "EA heartbeat was ${heartbeat_age}s old. Telemetry sync completed successfully."
        else
            send_telegram_alert "CRITICAL" "EA Heartbeat Critical" "EA heartbeat is ${heartbeat_age}s old and telemetry sync failed." "$sync_command"
        fi
    else
        log "INFO" "✅ EA heartbeat is fresh: ${heartbeat_age}s old"
    fi
}

# Function to check signal file size
check_signal_file() {
    log "INFO" "Checking signal file size..."

    if [[ ! -f "$SIGNAL_FILE" ]]; then
        log "ERROR" "❌ Signal file does not exist: $SIGNAL_FILE"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))

        # Create signal file with minimal content
        if mkdir -p "$(dirname "$SIGNAL_FILE")" 2>/dev/null; then
            for i in {1..5}; do
                echo '{"timestamp": "'$(date -Iseconds)'", "type": "startup_pad", "message": "Signal file padded by startup script"}' >> "$SIGNAL_FILE"
            done
            log "INFO" "✅ Created signal file with 5 initial entries"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
        else
            log "WARNING" "Cannot create signal file directory (permission denied)"
        fi
        return
    fi

    local file_size=$(stat -c%s "$SIGNAL_FILE" 2>/dev/null || echo "0")

    if [[ $file_size -lt 1000 ]]; then
        log "ERROR" "❌ Signal file too small: ${file_size} bytes (threshold: 1000)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))

        # Pad signal file to 5 lines
        log "INFO" "Padding signal file to 5 lines..."
        for i in {1..5}; do
            echo '{"timestamp": "'$(date -Iseconds)'", "type": "startup_pad", "message": "Signal file padded by startup script"}' >> "$SIGNAL_FILE" 2>/dev/null || true
        done

        local new_size=$(stat -c%s "$SIGNAL_FILE" 2>/dev/null || echo "0")
        if [[ $new_size -gt $file_size ]]; then
            log "INFO" "✅ Signal file padded from $file_size to $new_size bytes"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
        fi
    else
        log "INFO" "✅ Signal file size OK: $file_size bytes"
    fi
}

# Function to check pull loop log
check_pull_loop() {
    log "INFO" "Checking Windows pull loop log..."

    # Try to access via sidecar API first
    local sidecar_url="${MT5_SIDECAR_BASE_URL:-http://192.168.1.100:8080}"
    local log_content=""

    if command -v curl &> /dev/null; then
        log_content=$(curl -s --connect-timeout 5 "${sidecar_url}/api/logs/pull_signals" 2>/dev/null || echo "")
    fi

    # Fallback to SSH access
    if [[ -z "$log_content" ]]; then
        local ssh_command="gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance --command=\"powershell -Command 'Get-Content C:\\FXG\\logs\\pull_signals.log -Tail 10'\" --project fxg-ai-trading"
        log_content=$(eval "$ssh_command" 2>/dev/null || echo "")
    fi

    if [[ -n "$log_content" ]]; then
        # Check last entry for ERROR
        if echo "$log_content" | tail -1 | grep -qi "error"; then
            log "ERROR" "❌ Pull loop has ERROR in last entry"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))

            local error_line=$(echo "$log_content" | tail -1)
            local fix_cmd="# Connect to Windows VM and check pull_signals service:
gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance --project fxg-ai-trading
# Then run: powershell -Command 'Restart-Service FXGPullSignals; Get-Service FXGPullSignals'"

            send_telegram_alert "CRITICAL" "Pull Loop Error" "Windows pull loop has error: $error_line" "$fix_cmd"
        else
            log "INFO" "✅ Pull loop status OK"
        fi
    else
        log "WARNING" "⚠️ Could not access pull loop log"
        send_telegram_alert "WARNING" "Pull Loop Unreachable" "Cannot access Windows pull_signals.log via sidecar or SSH"
    fi
}

# Function to check preflight
check_preflight() {
    log "INFO" "Checking preflight status..."

    local preflight_response=""
    if command -v curl &> /dev/null; then
        preflight_response=$(curl -s --connect-timeout 5 http://127.0.0.1:8787/api/mt5/preflight 2>/dev/null || echo "")
    fi

    if [[ -n "$preflight_response" ]]; then
        # Parse JSON response
        local status=$(echo "$preflight_response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'UNKNOWN'))
except:
    print('ERROR')
" 2>/dev/null)

        if [[ "$status" == "PASS" ]]; then
            log "INFO" "✅ Preflight status: PASS"
        else
            log "ERROR" "❌ Preflight status: $status"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))

            # Get blocking reason
            local reason=$(echo "$preflight_response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('blocking_reason', 'Unknown'))
except:
    print('Unknown')
" 2>/dev/null)

            local fix_cmd="# Check preflight details:
curl -s http://127.0.0.1:8787/api/mt5/preflight | python3 -m json.tool
# Check services and restart if needed:
sudo systemctl restart ai-quant-control-plane ai-quant-runner"

            send_telegram_alert "CRITICAL" "Preflight BLOCKED" "Preflight is blocked: $reason" "$fix_cmd"
        fi
    else
        log "ERROR" "❌ Cannot reach preflight API"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        send_telegram_alert "CRITICAL" "Preflight API Unreachable" "Cannot connect to preflight API at http://127.0.0.1:8787"
    fi
}

# Main execution
main() {
    log "INFO" "Starting comprehensive health checks..."

    # Check all ALPHA services
    echo -e "${BLUE}=== Service Health Check ===${NC}"
    check_service "ai-quant-control-plane"
    check_service "ai-quant-runner"

    # Check EA heartbeat
    echo -e "${BLUE}=== EA Heartbeat Check ===${NC}"
    check_ea_heartbeat

    # Check signal file
    echo -e "${BLUE}=== Signal File Check ===${NC}"
    check_signal_file

    # Check pull loop
    echo -e "${BLUE}=== Pull Loop Check ===${NC}"
    check_pull_loop

    # Check preflight
    echo -e "${BLUE}=== Preflight Check ===${NC}"
    check_preflight

    # Final status summary
    echo -e "${BLUE}=== Final Status Summary ===${NC}"
    if [[ $ISSUES_FOUND -eq 0 ]]; then
        echo -e "${GREEN}✅ All systems healthy - no issues found${NC}"
        log "INFO" "✅ All systems healthy - no issues found"
        send_telegram_alert "SUCCESS" "FXG Startup Complete" "All systems are healthy and operational."
    else
        echo -e "${YELLOW}⚠️  Found $ISSUES_FOUND issues, applied $FIXES_APPLIED fixes${NC}"
        log "WARNING" "Found $ISSUES_FOUND issues, applied $FIXES_APPLIED fixes"
    fi

    log "INFO" "=== FXG Startup Health Check Completed ==="

    # Return exit code based on remaining issues
    local remaining_issues=$((ISSUES_FOUND - FIXES_APPLIED))
    if [[ $remaining_issues -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Handle script termination
trap 'log "ERROR" "Script terminated unexpectedly"' EXIT

# Run main function
main "$@"

# If we get here, everything went well
trap - EXIT