#!/usr/bin/env bash
# Copy export pack to ALPHA import Incoming (research review). Default: dry-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESEARCH_ROOT="${FXG_RESEARCH_ROOT:-${HOME}/fxg-research}"
PACK_ID=""
PACK_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --pack)
      PACK_ID="$2"
      shift 2
      ;;
    --pack-path)
      PACK_PATH="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

if [ -n "${PACK_PATH}" ]; then
  SRC="${PACK_PATH}"
elif [ -n "${PACK_ID}" ]; then
  SRC="${RESEARCH_ROOT}/ARTIFACTS/exports/${PACK_ID}"
else
  echo "Usage: $0 --pack <pack_id> | --pack-path /path/to/pack_dir"
  exit 1
fi

if [ ! -d "${SRC}" ] || [ ! -f "${SRC}/manifest.json" ]; then
  echo "Missing pack at ${SRC}"
  exit 1
fi

REMOTE="${ALPHA_SSH_TARGET:-}"
RDIR="${ALPHA_RESEARCH_IMPORT_DIR:-}"

if [ -z "${REMOTE}" ] || [ -z "${RDIR}" ]; then
  echo "ALPHA_IMPORT_DRY_RUN_OK (no ALPHA_SSH_TARGET or ALPHA_RESEARCH_IMPORT_DIR — would upload):"
  echo "  rsync -av \"${SRC}/\" \"${REMOTE}:${RDIR}/${PACK_ID}/\""
  exit 0
fi

if [ "${ALPHA_IMPORT_APPLY:-0}" != "1" ]; then
  echo "ALPHA_IMPORT_DRY_RUN_OK set ALPHA_IMPORT_APPLY=1 to run:"
  echo "  rsync -av \"${SRC}/\" \"${REMOTE}:${RDIR}/${PACK_ID}/\""
  exit 0
fi

rsync -av "${SRC}/" "${REMOTE}:${RDIR}/${PACK_ID}/"
echo "ALPHA_IMPORT_APPLIED ${PACK_ID}"
