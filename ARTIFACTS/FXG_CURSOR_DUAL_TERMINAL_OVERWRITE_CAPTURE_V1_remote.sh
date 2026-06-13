#!/bin/bash
set -e
FRESH_SEEN_AT=""
STALE_SEEN_AT=""
sudo mv /tmp/bridge_log_fresh.jsonl /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl
sudo chown aiquant:aiquant /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl
echo "INSTALL_DONE_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
for i in $(seq 1 40); do
  LC=$(wc -l < /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl | tr -d " ")
  ST=$(stat -c "%y %s" /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl)
  echo ""
  echo "=== tick $i $(date -u +%Y-%m-%dT%H:%M:%SZ) lines=$LC ==="
  echo "$ST"
  tail -n 5 /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl
  sudo lsof /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl 2>/dev/null || true
  if [ -z "$FRESH_SEEN_AT" ] && [ "$LC" -lt 1000 ]; then FRESH_SEEN_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ); echo "FRESH_MARKED_AT=$FRESH_SEEN_AT"; fi
  if [ "$LC" = "110383" ]; then
    TAILH=$(tail -n 3 /home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl)
    if echo "$TAILH" | grep -q "2026.03.20"; then
      if [ -z "$STALE_SEEN_AT" ]; then STALE_SEEN_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ); echo "STALE_OVERWRITE_MARKED_AT=$STALE_SEEN_AT"; fi
    fi
  fi
  sleep 1
done
echo "FRESH_SEEN_AT=${FRESH_SEEN_AT:-}"
echo "STALE_SEEN_AT=${STALE_SEEN_AT:-}"
