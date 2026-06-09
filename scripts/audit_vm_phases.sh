#!/bin/bash
# VM-side audit phases 4-8: Runtime truth collection (NON-DESTRUCTIVE)
# This script must be run on the VM via: gcloud compute ssh ... then run this script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Ensure ARTIFACTS directory exists
mkdir -p ARTIFACTS

echo "=== Phase 4: Runtime Truth on VM ==="
echo ""

# Get token
if [ -f /tmp/control_plane_token_current.txt ]; then
    TOKEN=$(cat /tmp/control_plane_token_current.txt)
    echo "Token(first8): ${TOKEN:0:8}..."
else
    echo "ERROR: Token file not found at /tmp/control_plane_token_current.txt"
    echo "       Run start_control_plane_clean.sh first or set CONTROL_PLANE_TOKEN"
    exit 1
fi

# Capture current status
curl -s http://127.0.0.1:8787/api/status | jq '.' | tee ARTIFACTS/vm_status.json || {
    echo "ERROR: Cannot reach /api/status - is control plane running?"
    exit 1
}

# Capture strategies
curl -s http://127.0.0.1:8787/api/strategies | jq '.' | tee ARTIFACTS/vm_strategies.json

# Extract original strategy
python3 << 'PY'
import json
from pathlib import Path
st=json.loads(Path('ARTIFACTS/vm_status.json').read_text())
Path('ARTIFACTS/original_active_strategy.txt').write_text(st.get('active_strategy_key',''))
print('original_active_strategy=', st.get('active_strategy_key',''))
PY

ORIG=$(cat ARTIFACTS/original_active_strategy.txt)
echo "original_strategy=$ORIG"

# Get allowed strategies
ALLOWED=$(cat ARTIFACTS/vm_strategies.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(" ".join(d.get("allowed",[])))')
echo "allowed=$ALLOWED"

# Strategy switching cycle (with revert)
echo "[SWITCH] cycling strategies (revert at end)" | tee ARTIFACTS/strategy_switch_cycle.log
for k in $ALLOWED; do 
  echo "switch->$k" | tee -a ARTIFACTS/strategy_switch_cycle.log
  curl -s -X POST http://127.0.0.1:8787/api/config \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"active_strategy_key\":\"$k\"}" | jq -r '.status,.message' | sed 's/^/  /' | tee -a ARTIFACTS/strategy_switch_cycle.log
  CUR=$(curl -s http://127.0.0.1:8787/api/status | python3 -c 'import sys,json; print(json.load(sys.stdin).get("active_strategy_key",""))')
  echo "  now=$CUR" | tee -a ARTIFACTS/strategy_switch_cycle.log
  if [ "$CUR" != "$k" ]; then 
    echo "  MISMATCH expected=$k got=$CUR" | tee -a ARTIFACTS/strategy_switch_cycle.log
    exit 8
  fi
done

# Revert to original
echo "[SWITCH] reverting to original: $ORIG" | tee -a ARTIFACTS/strategy_switch_cycle.log
curl -s -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"active_strategy_key\":\"$ORIG\"}" | jq '.' | tee ARTIFACTS/revert_response.json

curl -s http://127.0.0.1:8787/api/status | jq '.' | tee ARTIFACTS/vm_status_after_revert.json

# Capture accounts proof
curl -s http://127.0.0.1:8787/api/status | jq '{accounts_loaded,accounts_execution_capable,mode,execution_enabled,active_strategy_key}' | tee ARTIFACTS/accounts_runtime_proof.json

# Capture strategies proof
curl -s http://127.0.0.1:8787/api/strategies | jq '{allowed,default}' | tee ARTIFACTS/strategies_runtime_proof.json

# Dashboard switching proof
jq -n --arg orig "$ORIG" --arg allowed "$ALLOWED" '{original_strategy:$orig, allowed_keys:($allowed|split(" "))}' > ARTIFACTS/dashboard_switching_proof.json

echo ""
echo "=== Phase 5: Telegram Verification ==="
python3 << 'PY'
import os, json
from pathlib import Path
keys=['TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID']
obj={k:('SET' if os.getenv(k) else 'MISSING') for k in keys}
Path('ARTIFACTS/telegram_env_presence.json').write_text(json.dumps(obj,indent=2))
print(json.dumps(obj,indent=2))
PY

echo "[TELEGRAM] code presence (vm)" > ARTIFACTS/telegram_code_presence.txt
rg -n "TELEGRAM|telegram|sendMessage|chat_id|bot_token" src scripts 2>/dev/null | head -200 >> ARTIFACTS/telegram_code_presence.txt || true

if [ "${TELEGRAM_SEND_TEST:-0}" = "1" ]; then 
  echo "[TELEGRAM] send test requested (non-destructive)" | tee ARTIFACTS/telegram_send_test.log
  python3 << 'PY'
import os, requests
from pathlib import Path
if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
    raise SystemExit('telegram env missing')
tok=os.getenv('TELEGRAM_BOT_TOKEN')
chat=os.getenv('TELEGRAM_CHAT_ID')
text='AI-QUANT TEST: Telegram alert path OK ✅ (cloud readiness proof)'
r=requests.post(f'https://api.telegram.org/bot{tok}/sendMessage', data={'chat_id':chat,'text':text}, timeout=15)
Path('ARTIFACTS/telegram_send_test_http.txt').write_text(f'status={r.status_code}\nbody_prefix={r.text[:200]}')
print('status', r.status_code)
print(r.text[:200])
PY
else
  echo "[TELEGRAM] send test skipped (set TELEGRAM_SEND_TEST=1 to run)" | tee ARTIFACTS/telegram_send_test.log
fi

jq -n --slurpfile env ARTIFACTS/telegram_env_presence.json --rawfile code ARTIFACTS/telegram_code_presence.txt --rawfile send ARTIFACTS/telegram_send_test.log '{env_presence:$env[0], code_presence_preview:$code, send_test_log:$send}' > ARTIFACTS/telegram_proof.json

echo ""
echo "=== Phase 6: Reports Verification ==="
rg -n "daily|weekly|monthly|report|summary|targets|guid(e|ance)|planner|schedule|cron|timer" src scripts | head -400 | tee ARTIFACTS/reports_code_hits_vm.txt || true
find . -maxdepth 4 -type d -iname "*report*" -o -iname "*artifact*" -o -iname "*log*" | tee ARTIFACTS/reports_dirs_vm.txt || true
rg -n "systemd|timer|cron|crontab|apscheduler|celery|background" src scripts | head -300 | tee ARTIFACTS/reports_scheduler_hits_vm.txt || true

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
obj={
 'reports_code_hits_preview': (p/'reports_code_hits_vm.txt').read_text().splitlines()[:200] if (p/'reports_code_hits_vm.txt').exists() else [],
 'reports_dirs': (p/'reports_dirs_vm.txt').read_text().splitlines() if (p/'reports_dirs_vm.txt').exists() else [],
 'scheduler_hits_preview': (p/'reports_scheduler_hits_vm.txt').read_text().splitlines()[:200] if (p/'reports_scheduler_hits_vm.txt').exists() else []
}
(p/'reports_proof.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/reports_proof.json')
PY

echo ""
echo "=== Phase 7: AI Readiness Verification ==="
rg -n "openai|gpt|gemini|google-genai|anthropic|llm|prompt|completion|chat" src scripts | head -400 | tee ARTIFACTS/ai_code_hits_vm.txt || true

python3 << 'PY'
import os, json
from pathlib import Path
keys=['OPENAI_API_KEY','GOOGLE_API_KEY','GEMINI_API_KEY','MARKETAUX_API_KEY','MARKETAUX_API_KEYS']
obj={k:('SET' if os.getenv(k) else 'MISSING') for k in keys}
Path('ARTIFACTS/ai_env_presence.json').write_text(json.dumps(obj,indent=2))
print(json.dumps(obj,indent=2))
PY

curl -s -o /dev/null -w "egress_google=%{http_code}\n" https://www.google.com | tee ARTIFACTS/ai_egress_check.txt || true
curl -s -o /dev/null -w "egress_telegram=%{http_code}\n" https://api.telegram.org | tee -a ARTIFACTS/ai_egress_check.txt || true

if [ "${AI_E2E_TEST:-0}" = "1" ]; then 
  echo "[AI] E2E test requested; must be minimal, free, and safe. Only call an internal /api endpoint if it exists; otherwise skip." | tee ARTIFACTS/ai_e2e_test.log
  rg -n "/api/(ai|llm|predict|analysis)" src/control_plane templates 2>/dev/null | head -50 | tee -a ARTIFACTS/ai_e2e_test.log || true
else
  echo "[AI] E2E test skipped (set AI_E2E_TEST=1 to attempt)" | tee ARTIFACTS/ai_e2e_test.log
fi

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
obj={
 'ai_code_hits_preview': (p/'ai_code_hits_vm.txt').read_text().splitlines()[:200] if (p/'ai_code_hits_vm.txt').exists() else [],
 'ai_env_presence': json.loads((p/'ai_env_presence.json').read_text()) if (p/'ai_env_presence.json').exists() else {},
 'egress_check': (p/'ai_egress_check.txt').read_text() if (p/'ai_egress_check.txt').exists() else '',
 'e2e_test_log': (p/'ai_e2e_test.log').read_text() if (p/'ai_e2e_test.log').exists() else ''
}
(p/'ai_readiness_proof.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/ai_readiness_proof.json')
PY

echo ""
echo "=== Phase 8: VM Code Scan Summary ==="
rg -n "api/strategies|allowed\s*\[|strateg(y|ies)\s*catalog|active_strategy_key" src templates scripts | head -400 | tee ARTIFACTS/vm_code_strategies_hits.txt || true
rg -n "accounts_loaded|accounts_execution_capable|OANDA|practice|live|ACCOUNT_ID|ACCESS_TOKEN|oanda" src | head -400 | tee ARTIFACTS/vm_code_accounts_hits.txt || true
rg -n "TELEGRAM|telegram|sendMessage|chat_id|bot_token" src scripts | head -400 | tee ARTIFACTS/vm_code_telegram_hits.txt || true
rg -n "daily|weekly|monthly|report|summary|targets|guid(e|ance)|planner|schedule|cron|timer" src scripts | head -400 | tee ARTIFACTS/vm_code_reports_hits.txt || true
rg -n "openai|gpt|gemini|google-genai|anthropic|llm|prompt|completion|chat" src scripts | head -400 | tee ARTIFACTS/vm_code_ai_hits.txt || true

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
def sl(fn):
    f=p/fn
    return f.read_text().splitlines()[:200] if f.exists() else []
obj={
 'strategies_hits': sl('vm_code_strategies_hits.txt'),
 'accounts_hits': sl('vm_code_accounts_hits.txt'),
 'telegram_hits': sl('vm_code_telegram_hits.txt'),
 'reports_hits': sl('vm_code_reports_hits.txt'),
 'ai_hits': sl('vm_code_ai_hits.txt')
}
(p/'VM_scan_summary.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/VM_scan_summary.json')
PY

echo ""
echo "✅ VM audit phases 4-8 complete. Artifacts saved to ARTIFACTS/"
