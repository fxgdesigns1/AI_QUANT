# FXG Alpha VM — Account Control Commands + Command Pack (v2)

Generated: **2026-02-08 13:27:22Z** (UTC)

This document contains **copy/paste safe command packs** you can run on the VM to:
- verify runner health,
- verify TradeSelector compile + config,
- verify selector behavior (pre/post probes),
- diagnose repeats (pool/executed persistence),
- change runtime config safely (with backups),
- restart services safely.

> Notes
> - Repo root: `/opt/ai-quant`
> - Commands avoid secrets and fail-fast.

---

## 0) Quick Safety Snapshot (read-only)

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
echo "===== QUICK SAFETY SNAPSHOT ====="
date -u; hostname; echo

echo "== Runner status =="
systemctl is-active ai-quant-runner --no-pager || true
systemctl show ai-quant-runner -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ActiveEnterTimestamp --no-pager || true
PID="$(systemctl show -p MainPID --value ai-quant-runner)"
echo "MainPID=$PID"
ps -p "$PID" -o lstart,etime,args= || true
echo

echo "== runtime/status.json (if present) =="
if [ -f "$ROOT/runtime/status.json" ]; then
  sudo -n cat "$ROOT/runtime/status.json" | jq '{mode, execution_enabled, market_closed, no_trade_reason, accounts: (.accounts|length)}' || true
else
  echo "status.json not found"
fi

echo "===== DONE ====="
BASH
```

---

## 1) Locate Latest TradeSelector Backup (read-only)

```bash
sudo -n ls -td /opt/ai-quant/_ARCHIVE/trade_selector_fix_* | head -n 5
sudo -n test -f "$(ls -td /opt/ai-quant/_ARCHIVE/trade_selector_fix_* | head -n 1)/trade_selector.py.pre" && echo "backup pre exists"
```

---

## 2) Restore TradeSelector from Known-Good Backup + Compile + Restart Runner

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
LIVE="$ROOT/src/core/trade_selector.py"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ARCH="$ROOT/_ARCHIVE/trade_selector_restore_$TS"

echo "===== RESTORE LIVE trade_selector.py + VERIFY ====="
date -u; hostname; echo
echo "LIVE: $LIVE"
mkdir -p "$ARCH"

GOOD_SRC="$(ls -td $ROOT/_ARCHIVE/trade_selector_fix_*/trade_selector.py.pre 2>/dev/null | head -n 1 || true)"
if [ -z "$GOOD_SRC" ]; then
  GOOD_SRC="$(ls -td $ROOT/_ARCHIVE/trade_selector_restore_*/trade_selector.py.source_backup 2>/dev/null | head -n 1 || true)"
fi
[ -n "$GOOD_SRC" ] || { echo "ERROR: no known-good TradeSelector backup found"; exit 1; }

echo "GOOD_SRC: $GOOD_SRC"
cp -a "$LIVE" "$ARCH/trade_selector.py.pre_restore" 2>/dev/null || true
cp -a "$GOOD_SRC" "$ARCH/trade_selector.py.source_backup"
cp -a "$GOOD_SRC" "$LIVE"

cd "$ROOT"
source .venv/bin/activate
python -m py_compile "$LIVE"
echo "PASS: Compile OK"

systemctl restart ai-quant-runner
systemctl is-active ai-quant-runner --no-pager

echo
echo "== Last 80 runner lines =="
journalctl -u ai-quant-runner -n 80 --no-pager | tail -n 80 || true
echo "===== DONE ====="
BASH
```

Rollback:
```bash
# Replace <ARCH_DIR> with the printed restore folder
sudo -n cp -a <ARCH_DIR>/trade_selector.py.pre_restore /opt/ai-quant/src/core/trade_selector.py
cd /opt/ai-quant && source .venv/bin/activate && python -m py_compile src/core/trade_selector.py
sudo -n systemctl restart ai-quant-runner
```

---

## 3) Set `trade_selection.execution_cutoff=IMMEDIATE` (safe edit + backup)

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
CFG="$ROOT/runtime/config.yaml"
BAK="$ROOT/runtime/config.yaml.bak"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ARCH="$ROOT/_ARCHIVE/cutoff_immediate_verify_$TS"
mkdir -p "$ARCH"

echo "===== SET execution_cutoff=IMMEDIATE (SAFE) ====="
date -u; hostname; echo
echo "Backup: $ARCH"
cp -a "$CFG" "$ARCH/config.yaml.pre"
[ -f "$BAK" ] && cp -a "$BAK" "$ARCH/config.yaml.bak.pre" || true

sudo -n -u aiquant bash -lc "
  set -euo pipefail
  cd '$ROOT'
  source .venv/bin/activate
  python3 - <<'PY'
import yaml
from pathlib import Path

p=Path('runtime/config.yaml')
d=yaml.safe_load(p.read_text()) or {}
tsel=d.get('trade_selection') or {}
tsel['execution_cutoff']='IMMEDIATE'
d['trade_selection']=tsel
p.write_text(yaml.safe_dump(d, sort_keys=False))
print('SET trade_selection.execution_cutoff=', tsel.get('execution_cutoff'))
print('min_confidence_threshold=', tsel.get('min_confidence_threshold'))
print('mode=', tsel.get('mode'))
PY
"

cp -a "$CFG" "$BAK"
chown aiquant:aiquant "$CFG" "$BAK" || true
chmod 0664 "$CFG" "$BAK" || true

systemctl restart ai-quant-runner
echo "Runner: $(systemctl is-active ai-quant-runner --no-pager)"

echo
echo "== Selector probe lines (last 60) =="
journalctl -u ai-quant-runner -n 300 --no-pager | egrep -i "PRE_SELECTOR_PROBE|POST_SELECTOR_PROBE|POOL ADD|EXECUTING|Trade Selection" | tail -n 60 || true
echo "===== DONE ====="
BASH
```

Rollback:
```bash
sudo -n cp -a /opt/ai-quant/runtime/config.yaml.bak /opt/ai-quant/runtime/config.yaml
sudo -n systemctl restart ai-quant-runner
```

---

## 4) Verify TradeSelector Compile + Config Unwrap + Log Behavior (single shot)

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
F="$ROOT/src/core/trade_selector.py"

echo "===== VERIFY: TradeSelector + runner behavior ====="
date -u; hostname; echo

echo "== 1) Runner active + ExecStart + PID =="
systemctl is-active ai-quant-runner --no-pager || true
systemctl show ai-quant-runner -p WorkingDirectory -p ExecStart -p MainPID -p NRestarts --no-pager || true
PID="$(systemctl show -p MainPID --value ai-quant-runner)"
echo "MainPID=$PID"
ps -p "$PID" -o lstart,etime,args= || true
echo

echo "== 2) Compile check (service venv) =="
cd "$ROOT"
source .venv/bin/activate
python -m py_compile "$F"
echo "PASS: py_compile OK"
echo

echo "== 3) Runtime config unwrap sanity =="
python3 - <<'PY'
import yaml
from src.core.trade_selector import TradeSelector
cfg = yaml.safe_load(open('runtime/config.yaml','r').read()) or {}
a = TradeSelector()
print("A ok:", isinstance(a.config, dict), "mode=", a.config.get("mode"), "cutoff=", a.config.get("execution_cutoff"), "min_conf=", a.config.get("min_confidence_threshold"))
b = TradeSelector(cfg)
print("B ok:", isinstance(b.config, dict), "mode=", b.config.get("mode"), "cutoff=", b.config.get("execution_cutoff"), "min_conf=", b.config.get("min_confidence_threshold"))
PY
echo

echo "== 4) Selector evidence in logs (last 80) =="
journalctl -u ai-quant-runner -n 400 --no-pager | egrep -i "PRE_SELECTOR_PROBE|POST_SELECTOR_PROBE|POOL ADD|EXECUTING|Trade Selection|CONF_REJECT|POOL REJECT" | tail -n 80 || true
echo "===== DONE ====="
BASH
```

---

## 5) Diagnose “Repeats” (Why does EXECUTING fire again?)

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
F="$ROOT/src/core/trade_selector.py"

echo "===== VERIFY WHY IT REPEATS ====="
date -u; hostname; echo

echo "== 1) Is runner restarting? (NRestarts + start time) =="
systemctl show ai-quant-runner -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ActiveEnterTimestamp --no-pager
PID="$(systemctl show -p MainPID --value ai-quant-runner)"
echo "PID=$PID"
ps -p "$PID" -o lstart,etime,args= || true
echo

echo "== 2) Show executed state logic in TradeSelector =="
grep -nE "executed|executed_at|executed_ttl|max_execute|_candidate_key|POOL ADD|EXECUTING" "$F" | head -n 120 || true
echo

echo "== 3) Last selector logs =="
journalctl -u ai-quant-runner -n 500 --no-pager | egrep -i "PRE_SELECTOR_PROBE|POST_SELECTOR_PROBE|POOL ADD|EXECUTING|Trade Selection" | tail -n 80 || true

echo "===== END ====="
BASH
```

---

## 6) Command Pack (single “copy/paste + save” bundle)

```bash
sudo -n bash -s <<'BASH'
set -euo pipefail
export SYSTEMD_PAGER=
export PAGER=cat

ROOT=/opt/ai-quant
F="$ROOT/src/core/trade_selector.py"

echo "===== FXG COMMAND PACK (ALL-IN-ONE) ====="
date -u; hostname; echo

echo "== Runner status =="
systemctl is-active ai-quant-runner --no-pager || true
systemctl show ai-quant-runner -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ActiveEnterTimestamp --no-pager || true
PID="$(systemctl show -p MainPID --value ai-quant-runner)"
echo "MainPID=$PID"
ps -p "$PID" -o lstart,etime,args= || true
echo

echo "== TradeSelector compile (service venv) =="
cd "$ROOT"
source .venv/bin/activate
python -m py_compile "$F"
echo "PASS: TradeSelector compiles"
echo

echo "== TradeSelection config values (from YAML) =="
python3 - <<'PY'
import yaml
cfg = yaml.safe_load(open('runtime/config.yaml','r').read()) or {}
ts = (cfg.get("trade_selection") or {})
print("mode:", ts.get("mode"))
print("execution_cutoff:", ts.get("execution_cutoff"))
print("min_confidence_threshold:", ts.get("min_confidence_threshold"))
print("daily_trade_limit:", ts.get("daily_trade_limit"))
print("max_execute_per_account_per_cycle:", ts.get("max_execute_per_account_per_cycle"))
print("executed_ttl_seconds:", ts.get("executed_ttl_seconds"))
print("confidence_missing_policy:", ts.get("confidence_missing_policy"))
PY
echo

echo "== Selector logs (last 120 selector lines) =="
journalctl -u ai-quant-runner -n 800 --no-pager | egrep -i "PRE_SELECTOR_PROBE|POST_SELECTOR_PROBE|POOL ADD|EXECUTING|Trade Selection|CONF_REJECT|POOL REJECT" | tail -n 120 || true

echo "===== DONE ====="
BASH
```

---

## Dashboard Controls (what to add)

Controls you asked for in the dashboard:
- **Risk caps editor** (max_positions, max_daily_trades_per_account)
- **Trade selection editor** (mode, cutoff, min_conf, daily_trade_limit, max_execute_per_account_per_cycle, executed_ttl_seconds, confidence_missing_policy)
- **Account lanes editor** (enable/disable each lane, daily limit overrides)
- **Command Pack viewer** (render the command pack, copy/download)

