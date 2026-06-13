# GCP Deploy (GCE + systemd) - AI_QUANT Control Plane

## Required env vars on your local machine
- GCP_PROJECT_ID
- GCP_REGION (default: europe-west2)
- GCP_ZONE (default: europe-west2-a)
- GCP_VM_NAME (default: ai-quant-control-plane)

## Secrets (Secret Manager)
Create secrets (use deploy/gcp/create_secrets_from_files.sh to avoid shell history):
- ai-quant-oanda-api-key
- ai-quant-oanda-account-id
- ai-quant-newsapi-api-key
- ai-quant-alphavantage-api-key (or ai-quant-alphavantage-api-keys for CSV)
- ai-quant-marketaux-keys (CSV)
- ai-quant-polygon-api-keys (CSV)
- ai-quant-fmp-api-keys (CSV)
- ai-quant-finnhub-api-keys (CSV)
- ai-quant-fred-api-keys (CSV)
- ai-quant-telegram-bot-token
- ai-quant-telegram-chat-id

## VM
- Debian/Ubuntu recommended
- systemd service runs control plane

## Verification on VM
Use deploy/gcp/verify_vm.sh after install.
