#!/bin/bash
set -e

PROJECT="fxg-ai-trading"
ZONE="us-east1-b"
INSTANCE="fxg-quant-paper-e2-micro"

echo "=========================================================="
echo "   PULLING VM LOGS FOR TRADE DATA ANALYSIS"
echo "=========================================================="
echo ""

# Create local directory for VM logs
VM_LOGS_DIR="logs/vm_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$VM_LOGS_DIR"

echo "1. Checking VM trade ledger..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "if [ -f ~/gcloud-system/data/trade_ledger.jsonl ]; then cat ~/gcloud-system/data/trade_ledger.jsonl | tail -100; else echo 'File not found: ~/gcloud-system/data/trade_ledger.jsonl'; fi" \
  > "$VM_LOGS_DIR/trade_ledger.jsonl" 2>&1 || echo "⚠️  Could not read trade ledger"

echo "2. Checking VM control plane logs..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "if [ -f /tmp/control_plane.out ]; then tail -200 /tmp/control_plane.out; else echo 'File not found: /tmp/control_plane.out'; fi" \
  > "$VM_LOGS_DIR/control_plane.out" 2>&1 || echo "⚠️  Could not read control plane logs"

echo "3. Checking systemd runner service logs..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "sudo journalctl -u ai-quant-runner.service -n 200 --no-pager" \
  > "$VM_LOGS_DIR/runner_service.log" 2>&1 || echo "⚠️  Could not read runner service logs"

echo "4. Checking systemd control plane service logs..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "sudo journalctl -u ai-quant-control-plane.service -n 200 --no-pager" \
  > "$VM_LOGS_DIR/control_plane_service.log" 2>&1 || echo "⚠️  Could not read control plane service logs"

echo "5. Checking for data directory contents..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "ls -lah ~/gcloud-system/data/ 2>/dev/null || echo 'Data directory not found'" \
  > "$VM_LOGS_DIR/data_directory.txt" 2>&1

echo "6. Checking for recent trade activity in logs..."
gcloud compute ssh --project "$PROJECT" --zone "$ZONE" "$INSTANCE" -- \
  "grep -i 'trade\|order\|execution\|fill' /tmp/control_plane.out 2>/dev/null | tail -50 || echo 'No trade keywords found'" \
  > "$VM_LOGS_DIR/trade_keywords.log" 2>&1

echo ""
echo "=========================================================="
echo "   LOGS SAVED TO: $VM_LOGS_DIR"
echo "=========================================================="
echo ""
echo "📊 Analyzing trade ledger..."
if [ -f "$VM_LOGS_DIR/trade_ledger.jsonl" ]; then
  python3 scripts/analyze_vm_logs_dates.py "$VM_LOGS_DIR/trade_ledger.jsonl" || echo "Analysis script needs update"
else
  echo "⚠️  Trade ledger file not found on VM"
fi

echo ""
echo "✅ Done. Check $VM_LOGS_DIR for all VM logs"
