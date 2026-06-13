#!/usr/bin/env bash
# Sync Research Artifacts from VM to 5950X Local
# Pulls datasets, candle cache, and resolved configs

set -euo pipefail

# VM connection details (adjust as needed)
VM_PROJECT="${VM_PROJECT:-fxg-ai-trading}"
VM_ZONE="${VM_ZONE:-us-east1-b}"
VM_INSTANCE="${VM_INSTANCE:-fxg-quant-paper-e2-micro}"

# Local destination
LOCAL_ROOT="${HOME}/fxg-ai-quant-local"
LOCAL_ARTIFACTS="${LOCAL_ROOT}/artifacts"

# VM source paths
VM_ARTIFACTS_BASE="/opt/ai-quant/ARTIFACTS"

# Specific artifacts to sync (from user's known truth)
DATASET_ID="dataset_20260307T222011Z_recent30_enriched"
TOURNAMENT_ID="tournament_dataset_20260307T222011Z_recent30_enriched"
WAVE2_ID="${TOURNAMENT_ID}_wave2_v1"

echo "======================================================================"
echo "=== SYNCING VM ARTIFACTS TO LOCAL 5950X ==="
echo "======================================================================"
echo "VM: ${VM_INSTANCE} (${VM_PROJECT}/${VM_ZONE})"
echo "Local: ${LOCAL_ARTIFACTS}"
echo ""

# Verify VM connection
echo "Verifying VM connection..."
if ! gcloud compute ssh --project "${VM_PROJECT}" --zone "${VM_ZONE}" "${VM_INSTANCE}" --command "echo 'VM accessible'" > /dev/null 2>&1; then
    echo "❌ Cannot connect to VM. Check gcloud auth and VM status."
    exit 1
fi
echo "✅ VM accessible"

# Create local directories
mkdir -p "${LOCAL_ARTIFACTS}"/{datasets,backtests,candles}

# Sync dataset
echo ""
echo "Syncing dataset: ${DATASET_ID}"
VM_DATASET="${VM_ARTIFACTS_BASE}/datasets/${DATASET_ID}"
LOCAL_DATASET="${LOCAL_ARTIFACTS}/datasets/${DATASET_ID}"

if gcloud compute ssh --project "${VM_PROJECT}" --zone "${VM_ZONE}" "${VM_INSTANCE}" --command "test -d ${VM_DATASET}" > /dev/null 2>&1; then
    echo "  Found dataset on VM, syncing..."
    gcloud compute scp --recurse --project "${VM_PROJECT}" --zone "${VM_ZONE}" \
        "${VM_INSTANCE}:${VM_DATASET}" \
        "${LOCAL_DATASET}" || echo "  ⚠️  Dataset sync failed (may not exist)"
else
    echo "  ⚠️  Dataset not found on VM: ${VM_DATASET}"
fi

# Sync tournament candle cache
echo ""
echo "Syncing tournament candle cache: ${TOURNAMENT_ID}"
VM_CANDLES="${VM_ARTIFACTS_BASE}/backtests/${TOURNAMENT_ID}/candles"
LOCAL_CANDLES="${LOCAL_ARTIFACTS}/candles/${TOURNAMENT_ID}"

if gcloud compute ssh --project "${VM_PROJECT}" --zone "${VM_ZONE}" "${VM_INSTANCE}" --command "test -d ${VM_CANDLES}" > /dev/null 2>&1; then
    echo "  Found candle cache on VM, syncing..."
    gcloud compute scp --recurse --project "${VM_PROJECT}" --zone "${VM_ZONE}" \
        "${VM_INSTANCE}:${VM_CANDLES}" \
        "${LOCAL_CANDLES}" || echo "  ⚠️  Candle cache sync failed"
else
    echo "  ⚠️  Candle cache not found on VM: ${VM_CANDLES}"
fi

# Sync resolved tournament config
echo ""
echo "Syncing resolved config: ${WAVE2_ID}"
VM_CONFIG="${VM_ARTIFACTS_BASE}/backtests/${WAVE2_ID}/tournament_config_resolved.json"
LOCAL_CONFIG_DIR="${LOCAL_ARTIFACTS}/backtests/${WAVE2_ID}"
mkdir -p "${LOCAL_CONFIG_DIR}"

if gcloud compute ssh --project "${VM_PROJECT}" --zone "${VM_ZONE}" "${VM_INSTANCE}" --command "test -f ${VM_CONFIG}" > /dev/null 2>&1; then
    echo "  Found resolved config on VM, syncing..."
    gcloud compute scp --project "${VM_PROJECT}" --zone "${VM_ZONE}" \
        "${VM_INSTANCE}:${VM_CONFIG}" \
        "${LOCAL_CONFIG_DIR}/tournament_config_resolved.json" || echo "  ⚠️  Config sync failed"
else
    echo "  ⚠️  Resolved config not found on VM: ${VM_CONFIG}"
fi

# Sync tournament report
echo ""
echo "Syncing tournament report: ${WAVE2_ID}"
VM_REPORT="${VM_ARTIFACTS_BASE}/backtests/${WAVE2_ID}/report.json"

if gcloud compute ssh --project "${VM_PROJECT}" --zone "${VM_ZONE}" "${VM_INSTANCE}" --command "test -f ${VM_REPORT}" > /dev/null 2>&1; then
    echo "  Found report on VM, syncing..."
    gcloud compute scp --project "${VM_PROJECT}" --zone "${VM_ZONE}" \
        "${VM_INSTANCE}:${VM_REPORT}" \
        "${LOCAL_CONFIG_DIR}/report.json" || echo "  ⚠️  Report sync failed"
else
    echo "  ⚠️  Report not found on VM: ${VM_REPORT}"
fi

echo ""
echo "✅ Artifact sync complete!"
echo ""
echo "Synced artifacts:"
echo "  - Dataset: ${LOCAL_DATASET}"
echo "  - Candles: ${LOCAL_CANDLES}"
echo "  - Config: ${LOCAL_CONFIG_DIR}/tournament_config_resolved.json"
echo ""
echo "Next: Run cached backtest smoke test"
