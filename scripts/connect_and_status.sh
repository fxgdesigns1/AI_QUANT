#!/bin/bash

# Source configuration
CONFIG_FILE="scripts/config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file '$CONFIG_FILE' not found."
    exit 1
fi

echo "Using VM: $VM_NAME in Project: $PROJECT_ID, Zone: $ZONE"

# Function to execute a command on the remote VM
execute_ssh_command() {
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="$1"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to execute SSH command on $VM_NAME."
        exit 1
    fi
}

# Function to get the status of the AI Trading service
get_trade_status() {
    echo "Fetching status for $SERVICE_NAME..."
    execute_ssh_command "uptime && systemctl status $SERVICE_NAME"
}

# Function to get detailed logs for the AI Trading service (requires sudo)
get_trade_logs() {
    echo "Fetching logs for $SERVICE_NAME. This will require your sudo password on the VM."
    execute_ssh_command "sudo journalctl -u $SERVICE_NAME -n 100 --no-pager"
}

# Provide instructions if no argument is given
if [ -z "$1" ]; then
    echo "Usage:"
    echo "  $0 status - Get the current uptime and service status."
    echo "  $0 logs   - Get the latest service logs (requires sudo password on the VM)."
    echo ""
    echo "Example: $0 status"
else
    case "$1" in
        status)
            get_trade_status
            ;;
        logs)
            get_trade_logs
            ;;
        *)
            echo "Invalid command. Use 'status' or 'logs'."
            ;;
    esac
fi
