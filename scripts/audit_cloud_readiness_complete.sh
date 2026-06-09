#!/bin/bash
# Complete Cloud Readiness Audit — VM-side execution (Phases 1-8)
# NON-DESTRUCTIVE: No deletes, no commits, no trading enable, no secrets printed
# Run on VM: bash scripts/audit_cloud_readiness_complete.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

mkdir -p ARTIFACTS

echo "=== FXG AI-QUANT — Cloud Readiness Audit (VM-side) ==="
echo ""

# ============================================================================
# Phase 1: VM Duplicate Truth and Repo Fingerprint
# ============================================================================
echo "=== Phase 1: VM Duplicate Truth Scan ==="
date -u | tee ARTIFACTS/vm_run_timestamp_utc.txt
echo "[VM] repo path: $(pwd)" | tee ARTIFACTS/vm_repo_path.txt
git rev-parse HEAD 2>/dev/null | tee ARTIFACTS/vm_git_head.txt || echo "no git head" | tee ARTIFACTS/vm_git_head.txt
git status --porcelain=v1 2>/dev/null | tee ARTIFACTS/vm_git_status.txt || echo "not a git repo" | tee ARTIFACTS/vm_git_status.txt

echo "[VM] find duplicate copies of key entrypoints under ~ (bounded)"
find ~ -maxdepth 6 -type f -name 'scripts/start_control_plane_clean.sh' 2>/dev/null | tee ARTIFACTS/vm_find_start_script.txt || echo "no matches" | tee ARTIFACTS/vm_find_start_script.txt
find ~ -maxdepth 6 -type f -name 'src/control_plane/api.py' 2>/dev/null | tee ARTIFACTS/vm_find_api_py.txt || echo "no matches" | tee ARTIFACTS/vm_find_api_py.txt

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
obj={
  'vm':{
    'repo_root':str(Path('.').resolve()),
    'start_script_hits':p.joinpath('vm_find_start_script.txt').read_text().strip().splitlines() if p.joinpath('vm_find_start_script.txt').exists() else [],
    'api_py_hits':p.joinpath('vm_find_api_py.txt').read_text().strip().splitlines() if p.joinpath('vm_find_api_py.txt').exists() else []
  }
}
p.joinpath('VM_DUPLICATE_TRUTH_SCAN.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/VM_DUPLICATE_TRUTH_SCAN.json')
PY

echo ""

# ============================================================================
# Phase 2: VM Runtime Truth and Safety Invariants
# ============================================================================
echo "=== Phase 2: VM Runtime Truth and Safety ==="

if [ ! -f /tmp/control_plane_token_current.txt ]; then
    echo "ERROR: Token file not found at /tmp/control_plane_token_current.txt"
    echo "       Run start_control_plane_clean.sh first or set CONTROL_PLANE_TOKEN"
    exit 1
fi

TOKEN=$(cat /tmp/control_plane_token_current.txt)
echo "Token(first8): ${TOKEN:0:8}..." | tee ARTIFACTS/token_prefix.txt

echo "[VM] baseline status"
curl -s http://127.0.0.1:8787/api/status | jq '.' | tee ARTIFACTS/vm_status_baseline.json

echo "[VM] strategies catalog"
curl -s http://127.0.0.1:8787/api/strategies | jq '.' | tee ARTIFACTS/vm_strategies.json

python3 << 'PY'
import json
from pathlib import Path
st=json.loads(Path('ARTIFACTS/vm_status_baseline.json').read_text())
Path('ARTIFACTS/original_active_strategy.txt').write_text(st.get('active_strategy_key',''))
print('original_active_strategy=', st.get('active_strategy_key',''))
PY

ORIG=$(cat ARTIFACTS/original_active_strategy.txt)
ALLOWED=$(cat ARTIFACTS/vm_strategies.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(" ".join(d.get("allowed",[])))')

echo "original_strategy=$ORIG" | tee ARTIFACTS/original_strategy_line.txt
echo "allowed=$ALLOWED" | tee ARTIFACTS/allowed_strategy_keys_line.txt

echo "[VM] cycle strategy switching across ALL allowed keys then revert" | tee ARTIFACTS/strategy_switch_cycle.log
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

echo "[VM] revert to original: $ORIG" | tee -a ARTIFACTS/strategy_switch_cycle.log
curl -s -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"active_strategy_key\":\"$ORIG\"}" | jq '.' | tee ARTIFACTS/revert_response.json

curl -s http://127.0.0.1:8787/api/status | jq '.' | tee ARTIFACTS/vm_status_after_revert.json

jq -n --arg orig "$ORIG" --arg allowed "$ALLOWED" '{original_strategy:$orig, allowed_keys:($allowed|split(" "))}' > ARTIFACTS/DASHBOARD_SWITCHING_PROOF.json

curl -s http://127.0.0.1:8787/api/status | jq '{mode,execution_enabled,accounts_loaded,accounts_execution_capable,active_strategy_key}' > ARTIFACTS/VM_TRUTH.json

echo ""

# ============================================================================
# Phase 3: Strategies and Accounts Limits Proof
# ============================================================================
echo "=== Phase 3: Strategies and Accounts Limits ==="

echo "[LIMITS] STRATEGIES: runtime count and code definition"
python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
vm_strat=p/'vm_strategies.json'
obj={}
if vm_strat.exists():
    d=json.loads(vm_strat.read_text())
    allowed=d.get('allowed',[])
    obj['runtime_allowed_count']=len(allowed)
    obj['runtime_allowed_keys']=allowed
    obj['runtime_default']=d.get('default')
else:
    obj['runtime_allowed_count']=None
    obj['runtime_allowed_keys']=[]
    obj['runtime_default']=None
p.joinpath('STRATEGIES_LIMITS_PROOF.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/STRATEGIES_LIMITS_PROOF.json')
PY

echo "[LIMITS] ACCOUNTS: prove supported shape (single vs multi) via code + runtime"
rg -n "accounts_loaded|accounts_execution_capable|account(s)?\b|OANDA|practice|fxpractice|ACCOUNT_ID|ACCESS_TOKEN" src scripts templates 2>/dev/null | head -400 | tee ARTIFACTS/accounts_code_hits.txt || echo "no matches" | tee ARTIFACTS/accounts_code_hits.txt

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
truth=json.loads((p/'VM_TRUTH.json').read_text()) if (p/'VM_TRUTH.json').exists() else {}
hits=(p/'accounts_code_hits.txt').read_text().splitlines() if (p/'accounts_code_hits.txt').exists() else []
obj={
 'runtime_accounts_loaded': truth.get('accounts_loaded'),
 'runtime_accounts_execution_capable': truth.get('accounts_execution_capable'),
 'code_hits_preview': hits[:200]
}
(p/'ACCOUNTS_LIMITS_PROOF.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/ACCOUNTS_LIMITS_PROOF.json')
PY

echo ""

# ============================================================================
# Phase 4: Secrets Cleanliness and Historical Artifact Quarantine
# ============================================================================
echo "=== Phase 4: Secrets Scan (Redacted) ==="

echo "[SECRETS] Redacted pattern scan (do not print secrets)"
rg -n --hidden --no-ignore-vcs -S "sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{30,}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|TELEGRAM_BOT_TOKEN\s*[:=]|OANDA_(API_KEY|ACCESS_TOKEN|ACCOUNT_ID)\s*[:=]|api-fxpractice\.oanda\.com" . 2>/dev/null | head -500 | tee ARTIFACTS/secrets_scan_raw_hits.txt || echo "no matches" | tee ARTIFACTS/secrets_scan_raw_hits.txt

python3 << 'PY'
import re, json
from pathlib import Path
raw=Path('ARTIFACTS/secrets_scan_raw_hits.txt')
lines=raw.read_text().splitlines() if raw.exists() else []
red=[]
for ln in lines:
    ln2=re.sub(r'(sk-[A-Za-z0-9]{10})[A-Za-z0-9]{10,}', r'\1…REDACTED', ln)
    ln2=re.sub(r'(AIza[0-9A-Za-z\-_]{6})[0-9A-Za-z\-_]{10,}', r'\1…REDACTED', ln2)
    ln2=re.sub(r'((?:BOT_TOKEN|API_KEY|ACCESS_TOKEN|ACCOUNT_ID)\s*[:=]\s*)[^\s]+', r'\1REDACTED', ln2, flags=re.I)
    red.append(ln2)
obj={'hit_count':len(lines),'hits_redacted':red[:300]}
Path('ARTIFACTS/SECRETS_FINDINGS_REDACTED.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/SECRETS_FINDINGS_REDACTED.json')
PY

echo "[SECRETS] Identifying historical forensic files"
python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
candidates=[]
for path in Path('.').rglob('*.json'):
    name=path.name.lower()
    if 'forensic' in name or 'audit' in name or 'snapshot' in name:
        candidates.append(str(path))
(p/'historical_json_candidates.txt').write_text('\n'.join(candidates))
print(f'Found {len(candidates)} historical JSON candidates')
print('wrote ARTIFACTS/historical_json_candidates.txt')
PY

echo ""

# ============================================================================
# Phase 5: Telegram Verification
# ============================================================================
echo "=== Phase 5: Telegram Verification ==="

python3 << 'PY'
import os, json
from pathlib import Path
keys=['TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID']
obj={k:('SET' if os.getenv(k) else 'MISSING') for k in keys}
Path('ARTIFACTS/telegram_env_presence.json').write_text(json.dumps(obj,indent=2))
print(json.dumps(obj,indent=2))
PY

rg -n "TELEGRAM|telegram|sendMessage|chat_id|bot_token" src scripts 2>/dev/null | head -300 | tee ARTIFACTS/telegram_code_hits.txt || echo "no matches" | tee ARTIFACTS/telegram_code_hits.txt

if [ "${TELEGRAM_SEND_TEST:-0}" = "1" ]; then 
  python3 << 'PY'
import os, requests
from pathlib import Path
if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
    raise SystemExit('telegram env missing')
tok=os.getenv('TELEGRAM_BOT_TOKEN')
chat=os.getenv('TELEGRAM_CHAT_ID')
text='AI-QUANT TEST: Telegram alert pipeline OK ✅ (cloud readiness proof)'
r=requests.post(f'https://api.telegram.org/bot{tok}/sendMessage', data={'chat_id':chat,'text':text}, timeout=15)
Path('ARTIFACTS/telegram_send_test_http.txt').write_text(f'status={r.status_code}\nbody_prefix={r.text[:200]}')
print('status', r.status_code)
print(r.text[:200])
PY
else
  echo "send_test=skipped (set TELEGRAM_SEND_TEST=1 to run)" | tee ARTIFACTS/telegram_send_test_http.txt
fi

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
env=json.loads((p/'telegram_env_presence.json').read_text()) if (p/'telegram_env_presence.json').exists() else {}
code=(p/'telegram_code_hits.txt').read_text().splitlines()[:200] if (p/'telegram_code_hits.txt').exists() else []
send=(p/'telegram_send_test_http.txt').read_text() if (p/'telegram_send_test_http.txt').exists() else ''
obj={'env_presence':env,'code_hits_preview':code,'send_test_result':send}
(p/'TELEGRAM_PROOF.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/TELEGRAM_PROOF.json')
PY

echo ""

# ============================================================================
# Phase 6: Daily/Weekly/Monthly Reports Verification
# ============================================================================
echo "=== Phase 6: Reports Verification ==="

rg -n "daily|weekly|monthly|report|summary|targets|planner|guidance|schedule|cron|timer" src scripts templates 2>/dev/null | head -500 | tee ARTIFACTS/reports_code_hits.txt || echo "no matches" | tee ARTIFACTS/reports_code_hits.txt

find . -maxdepth 5 -type f \( -iname '*report*' -o -iname '*daily*' -o -iname '*weekly*' -o -iname '*monthly*' \) 2>/dev/null | head -200 | tee ARTIFACTS/reports_files_find.txt || echo "no matches" | tee ARTIFACTS/reports_files_find.txt

rg -n "apscheduler|schedule\.|crontab|systemd.*timer" src scripts 2>/dev/null | head -300 | tee ARTIFACTS/reports_scheduler_hits.txt || echo "no matches" | tee ARTIFACTS/reports_scheduler_hits.txt

mkdir -p ARTIFACTS/reports_dry_run
echo "dry_run_attempt=none" > ARTIFACTS/reports_dry_run/result.txt

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
obj={
 'code_hits_preview': (p/'reports_code_hits.txt').read_text().splitlines()[:200] if (p/'reports_code_hits.txt').exists() else [],
 'files_found': (p/'reports_files_find.txt').read_text().splitlines()[:200] if (p/'reports_files_find.txt').exists() else [],
 'scheduler_hits_preview': (p/'reports_scheduler_hits.txt').read_text().splitlines()[:200] if (p/'reports_scheduler_hits.txt').exists() else [],
 'dry_run_note': (p/'reports_dry_run/result.txt').read_text().strip() if (p/'reports_dry_run/result.txt').exists() else ''
}
(p/'REPORTS_PROOF.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/REPORTS_PROOF.json')
PY

echo ""

# ============================================================================
# Phase 7: AI Cloud Readiness Verification
# ============================================================================
echo "=== Phase 7: AI Cloud Readiness ==="

rg -n "openai|gpt|gemini|google-genai|anthropic|llm|prompt|completion|chat" src scripts 2>/dev/null | head -500 | tee ARTIFACTS/ai_code_hits.txt || echo "no matches" | tee ARTIFACTS/ai_code_hits.txt

python3 << 'PY'
import os, json
from pathlib import Path
keys=['OPENAI_API_KEY','GOOGLE_API_KEY','GEMINI_API_KEY','MARKETAUX_API_KEY','MARKETAUX_API_KEYS']
obj={k:('SET' if os.getenv(k) else 'MISSING') for k in keys}
Path('ARTIFACTS/ai_env_presence.json').write_text(json.dumps(obj,indent=2))
print(json.dumps(obj,indent=2))
PY

curl -s -o /dev/null -w "egress_google=%{http_code}\n" https://www.google.com | tee ARTIFACTS/ai_egress_check.txt || true
curl -s -o /dev/null -w "egress_openai=%{http_code}\n" https://api.openai.com | tee -a ARTIFACTS/ai_egress_check.txt || true
curl -s -o /dev/null -w "egress_gemini=%{http_code}\n" https://generativelanguage.googleapis.com | tee -a ARTIFACTS/ai_egress_check.txt || true

rg -n "/api/(ai|llm|predict|analysis)" src/control_plane templates 2>/dev/null | head -100 | tee ARTIFACTS/ai_internal_endpoints_find.txt || echo "no matches" | tee ARTIFACTS/ai_internal_endpoints_find.txt

if [ "${AI_E2E_TEST:-0}" = "1" ]; then 
  echo "AI_E2E_TEST requested but only allowed if there is a safe internal endpoint. If none exists, skip." | tee ARTIFACTS/ai_e2e_test.log
else
  echo "AI_E2E_TEST skipped" | tee ARTIFACTS/ai_e2e_test.log
fi

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')
obj={
 'env_presence': json.loads((p/'ai_env_presence.json').read_text()) if (p/'ai_env_presence.json').exists() else {},
 'code_hits_preview': (p/'ai_code_hits.txt').read_text().splitlines()[:200] if (p/'ai_code_hits.txt').exists() else [],
 'egress_check': (p/'ai_egress_check.txt').read_text() if (p/'ai_egress_check.txt').exists() else '',
 'internal_endpoints_find_preview': (p/'ai_internal_endpoints_find.txt').read_text().splitlines()[:200] if (p/'ai_internal_endpoints_find.txt').exists() else [],
 'e2e_test_log': (p/'ai_e2e_test.log').read_text() if (p/'ai_e2e_test.log').exists() else ''
}
(p/'AI_CLOUD_PROOF.json').write_text(json.dumps(obj,indent=2))
print('wrote ARTIFACTS/AI_CLOUD_PROOF.json')
PY

echo ""

# ============================================================================
# Phase 8: Generate Final Cloud Readiness Report and GO/NO-GO
# ============================================================================
echo "=== Phase 8: Generate Final Report ==="

python3 << 'PY'
import json
from pathlib import Path
p=Path('ARTIFACTS')

def j(name):
    f=p/name
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except Exception:
        return None

vm_truth=j('VM_TRUTH.json') or {}
dup=j('VM_DUPLICATE_TRUTH_SCAN.json') or {}
strat=j('STRATEGIES_LIMITS_PROOF.json') or {}
acct=j('ACCOUNTS_LIMITS_PROOF.json') or {}
switch=j('DASHBOARD_SWITCHING_PROOF.json') or {}
tele=j('TELEGRAM_PROOF.json') or {}
rep=j('REPORTS_PROOF.json') or {}
ai=j('AI_CLOUD_PROOF.json') or {}
sec=j('SECRETS_FINDINGS_REDACTED.json') or {}

# Determine statuses conservatively
paper_ok = (vm_truth.get('mode')=='paper' and vm_truth.get('execution_enabled') is False)
no_dup_ok = True
try:
    hits=dup.get('vm',{})
    if hits:
        if len(hits.get('start_script_hits',[]))>1 or len(hits.get('api_py_hits',[]))>1:
            no_dup_ok=False
except Exception:
    pass

telegram_env = tele.get('env_presence',{}) if isinstance(tele,dict) else {}
telegram_set = all(v=='SET' for v in telegram_env.values()) if telegram_env else False
telegram_send_ok = ('status=200' in (tele.get('send_test_result','') if isinstance(tele,dict) else ''))
telegram_verified = telegram_set and telegram_send_ok

reports_has_hits = bool(rep.get('code_hits_preview')) or bool(rep.get('files_found')) or bool(rep.get('scheduler_hits_preview'))
ai_has_hits = bool(ai.get('code_hits_preview'))
ai_env = ai.get('env_presence',{}) if isinstance(ai,dict) else {}
ai_configured = any(v=='SET' for v in ai_env.values())

secrets_hit_count = int(sec.get('hit_count',0) or 0)

gaps=[]
if not telegram_verified:
    gaps.append('Telegram not fully verified (env missing or send test not run/confirmed).')
if not reports_has_hits:
    gaps.append('Daily/weekly/monthly reports not proven (no generator/scheduler evidence found).')
if not (ai_has_hits and ai_configured):
    gaps.append('AI not proven in cloud (code may exist but env not configured and/or no safe e2e endpoint proof).')

no_go_reasons=[]
if not paper_ok:
    no_go_reasons.append('Safety invariant failed: mode!=paper or execution_enabled!=false.')
if not no_dup_ok:
    no_go_reasons.append('Duplicate truth detected on VM: multiple copies of key entrypoints.')
# Secrets scan: flag strongly but require human review
if secrets_hit_count>0:
    no_go_reasons.append('Secrets scan had hits (redacted). Requires manual classification + rotation if real secrets exist.')

verdict = 'GO' if (paper_ok and no_dup_ok and len(no_go_reasons)==0) else 'NO-GO'

md=[]
md.append('# FINAL Cloud Readiness Report — FXG AI-QUANT Control Plane (Non-Destructive)')
md.append('')
md.append(f'**Audit Date**: {Path(p/"vm_run_timestamp_utc.txt").read_text().strip() if (p/"vm_run_timestamp_utc.txt").exists() else "N/A"}')
md.append(f'**VM Repo Path**: {Path(p/"vm_repo_path.txt").read_text().strip() if (p/"vm_repo_path.txt").exists() else "N/A"}')
md.append('')
md.append('## Safety invariants')
md.append(f"- mode: **{vm_truth.get('mode','N/A')}**")
md.append(f"- execution_enabled: **{vm_truth.get('execution_enabled','N/A')}**")
md.append(f"- ✅ Paper mode OK: {paper_ok}")
md.append('')
md.append('## Strategy switching')
md.append(f"- original_strategy: **{switch.get('original_strategy','N/A')}**")
md.append(f"- allowed_keys_count: **{len(switch.get('allowed_keys',[]))}**")
md.append(f"- allowed_keys: {', '.join(switch.get('allowed_keys',[]))}")
md.append('')
md.append('## Accounts & strategies limits')
md.append(f"- strategies_allowed_count (runtime): **{strat.get('runtime_allowed_count','N/A')}**")
md.append(f"- accounts_loaded (runtime): **{acct.get('runtime_accounts_loaded','N/A')}**")
md.append(f"- accounts_execution_capable (runtime): **{acct.get('runtime_accounts_execution_capable','N/A')}**")
md.append('')
md.append('## Telegram')
md.append(f"- env_presence: {telegram_env}")
md.append(f"- verified: **{telegram_verified}**")
md.append('')
md.append('## Reports (daily/weekly/monthly)')
md.append(f"- evidence_found: **{reports_has_hits}**")
md.append(f"- note: VERIFIED requires runnable generator + artifacts")
md.append('')
md.append('## AI in cloud')
md.append(f"- code_hits_found: **{ai_has_hits}**")
md.append(f"- env_configured_any: **{ai_configured}**")
md.append(f"- note: VERIFIED requires safe invoked proof")
md.append('')
md.append('## Secrets scan (redacted)')
md.append(f"- hit_count: **{secrets_hit_count}**")
md.append(f"- action: classify hits; rotate if any real credentials")
md.append('')
md.append('## Duplicate truth scan')
try:
    hits=dup.get('vm',{})
    start_hits=len(hits.get('start_script_hits',[]))
    api_hits=len(hits.get('api_py_hits',[]))
    md.append(f"- start_script_hits: {start_hits}")
    md.append(f"- api_py_hits: {api_hits}")
    md.append(f"- ✅ No duplicates OK: {no_dup_ok}")
except Exception:
    md.append("- duplicate scan: error")
md.append('')
md.append('## Verdict')
md.append(f"**{verdict}**")
md.append('')
if no_go_reasons:
    md.append('### NO-GO reasons')
    md.extend([f"- {r}" for r in no_go_reasons])
    md.append('')
if gaps:
    md.append('### Gaps / Not proven')
    md.extend([f"- {g}" for g in gaps])
    md.append('')

Path('FINAL_CLOUD_READINESS_REPORT.md').write_text('\n'.join(md))

go_no_go={
 'verdict': verdict,
 'paper_ok': paper_ok,
 'no_duplicate_truth_ok': no_dup_ok,
 'telegram_verified': telegram_verified,
 'reports_proven': reports_has_hits,
 'ai_configured_any': ai_configured,
 'secrets_scan_hit_count': secrets_hit_count,
 'no_go_reasons': no_go_reasons,
 'gaps': gaps
}
Path('GO_NO_GO.json').write_text(json.dumps(go_no_go,indent=2))

print('wrote FINAL_CLOUD_READINESS_REPORT.md')
print('wrote GO_NO_GO.json')
print('')
print(f'=== VERDICT: {verdict} ===')
if no_go_reasons:
    print('NO-GO reasons:')
    for r in no_go_reasons:
        print(f'  - {r}')
if gaps:
    print('Gaps:')
    for g in gaps:
        print(f'  - {g}')
PY

echo ""
echo "✅ Complete cloud readiness audit finished. Check FINAL_CLOUD_READINESS_REPORT.md and GO_NO_GO.json"
