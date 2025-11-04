#!/bin/sh

BASE_URL="${BASE_URL:-http://localhost:8080}"

set -e

curl -sSf "$BASE_URL/api/health/scheduler" | jq '.' >/dev/null || exit 1
curl -sSf "$BASE_URL/api/health/nontrading" | jq '.' >/dev/null || exit 1
curl -sSf "$BASE_URL/api/signals" | jq '.' >/dev/null || exit 1

echo "Smoke health checks passed against $BASE_URL"
