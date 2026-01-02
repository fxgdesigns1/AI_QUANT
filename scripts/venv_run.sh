#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing .venv. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -U openai google-genai"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# If the caller passed VAR=VALUE prefixes, convert to: env VAR=VALUE ... command...
env_kv=()
while [[ "${1-}" == *=* ]]; do
  env_kv+=("$1")
  shift
done

if (( ${#env_kv[@]} > 0 )); then
  exec env "${env_kv[@]}" "$@"
else
  exec "$@"
fi
