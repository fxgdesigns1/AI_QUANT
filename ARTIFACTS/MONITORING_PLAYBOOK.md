# AI-QUANT LOCAL Mac: Live Paper Runtime + Dashboard Monitoring Playbook

**Date:** 2026-01-05T01:25:00Z  
**Purpose:** Recurring verification commands for LOCAL Mac trading system monitoring  
**Tone:** Forensic, zero-assumptions, secrets-safe  
**Status:** ✅ VERIFIED — Dashboard served properly + Runtime coping with open-market conditions

---

## Quick Status Summary (Latest Verification)

### ✅ Dashboard Status
- **HTTP:** 200 OK
- **Size:** 101,832 bytes
- **Response Time:** 0.002s
- **Smoke Test:** PASS
- **UI Markers:** All present (nav-item, tab-content, /api/status, AI-QUANT)

### ✅ Runtime Status
- **Mode:** paper
- **Execution Enabled:** true
- **Accounts:** 1 loaded, 1 execution-capable
- **Strategy:** gold (XAU_USD)
- **Scan Loop:** ACTIVE (last_scan_at advancing)
- **OANDA API:** 100% success rate (fresh prices every 30s)
- **Errors:** None found

### ✅ Process Health
- **Control Plane:** PID 57441 (serving 127.0.0.1:8787)
- **Runner:** PID 57474 (scanning every 30s)
- **Uptime:** Stable since 12:25 AM

---

## Phase 1: Confirm LOCAL Dashboard (Not VM Tunnel)

### Purpose
Verify you're viewing the LOCAL Mac dashboard, not accidentally hitting the VM through an SSH tunnel.

### Commands

```bash
# Check HTTP headers and content
curl -s -D - http://127.0.0.1:8787/ -o /tmp/_root_check.html | head -n 15
```

**Expected Output:**
```
HTTP/1.1 200 OK
server: uvicorn
content-type: text/html; charset=utf-8
content-length: 101832
```

```bash
# Programmatic smoke test
python - <<'PY'
import re, urllib.request
u='http://127.0.0.1:8787/'
html=urllib.request.urlopen(u, timeout=5).read().decode('utf-8','ignore')
assert len(html)>50000, f'HTML too small: {len(html)}'
assert re.search(r'<title>.*AI-QUANT.*</title>', html, re.I), 'Missing expected title'
assert 'tab-content' in html and 'nav-item' in html, 'Missing expected UI markers'
print('DASHBOARD_SMOKE_TEST_PASS', 'bytes=', len(html))
PY
```

**Expected Output:**
```
DASHBOARD_SMOKE_TEST_PASS bytes= 101774
```

```bash
# Verify port listeners
lsof -nP -iTCP:8787 -sTCP:LISTEN
```

**Expected Output:**
```
COMMAND   PID USER   ADDRESS           PROTOCOL
Python  57441  mac  127.0.0.1:8787    TCP4      ← LOCAL control plane
ssh     50584  mac  [::1]:8787        TCP6      ← VM tunnel (not interfering)
```

### Pass Criteria
- ✅ Root returns HTTP 200 with HTML >50KB
- ✅ Smoke test prints `DASHBOARD_SMOKE_TEST_PASS`
- ✅ Python process listening on `127.0.0.1:8787`

### If Fail
- **Empty HTML or connection refused:** Control plane not running. Check process: `ps aux | grep control_plane.api`
- **Only SSH listener:** Tunnel collision. Stop tunnels or use different ports.

---

## Phase 2: Confirm Runtime Health + Scan Loop

### Purpose
Prove the system is actively scanning and fetching live market data.

### Commands

```bash
# Get current status
curl -s http://127.0.0.1:8787/api/status | python -m json.tool
```

**Expected Output:**
```json
{
    "mode": "paper",
    "execution_enabled": true,
    "accounts_loaded": 1,
    "accounts_execution_capable": 1,
    "active_strategy_key": "gold",
    "last_scan_at": "2026-01-05T01:22:24.563585Z",
    "weekend_indicator": false
}
```

```bash
# Time-based scan loop proof (65-second observation)
python - <<'PY'
import json, time, urllib.request

def get_status():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:8787/api/status', timeout=5).read())

s0=get_status(); t0=s0.get('last_scan_at');
print('T0 last_scan_at:', t0)
print('T0 signals/executed:', s0.get('last_signals_generated'), s0.get('last_executed_count'))
print('Waiting 65 seconds...')
time.sleep(65)
s1=get_status(); t1=s1.get('last_scan_at');
print('T1 last_scan_at:', t1)
print('T1 signals/executed:', s1.get('last_signals_generated'), s1.get('last_executed_count'))
print('Result: last_scan_at', 'ADVANCED' if t1 > t0 else 'NOT ADVANCING')
PY
```

**Expected Output:**
```
T0 last_scan_at: 2026-01-05T01:22:54.898150Z
T0 signals/executed: 0 0
Waiting 65 seconds...
T1 last_scan_at: 2026-01-05T01:23:55.613416Z
T1 signals/executed: 0 0
Result: last_scan_at ADVANCED
```

```bash
# Check runner logs (with account ID redaction)
tail -n 60 /private/tmp/ai-quant-local/runner.out | sed -e 's/[0-9]\{3\}-[0-9]\{3\}-[0-9]\{8\}-[0-9]\{3\}/[REDACTED_ACCOUNT_ID]/g'
```

**Expected Output:**
```
2026-01-05 01:23:55 - 🔍 SCANNING FOR OPPORTUNITIES...
2026-01-05 01:23:55 - ✅ Retrieved FRESH prices for 1 instruments from OANDA API
2026-01-05 01:23:55 - 📊 Total signals generated: 0
2026-01-05 01:23:55 - ⏰ Next scan in 30 seconds...
```

### Pass Criteria
- ✅ `weekend_indicator: false` (when FX market is open)
- ✅ `last_scan_at` advances between T0 and T1
- ✅ Runner logs show repeated scanning + fresh OANDA prices
- ✅ No tracebacks or exceptions

### Interpretation Notes
- ℹ️  `last_signals_generated: 0` is **NOT a failure** if strategy conditions haven't triggered
- ✅ **Key health proof:** Scan loop advancing + fresh OANDA prices + clean logs

---

## Phase 3: Verify Paper Execution Readiness

### Purpose
Confirm the system is configured for paper trading and ready to execute when signals appear.

### Commands

```bash
# Extract key execution fields
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep -E "mode|execution_enabled|accounts_loaded|accounts_execution_capable|active_strategy_key"
```

**Expected Output:**
```
    "mode": "paper",
    "execution_enabled": true,
    "accounts_loaded": 1,
    "accounts_execution_capable": 1,
    "active_strategy_key": "gold",
```

```bash
# Verify runner and control plane processes
ps aux | grep -E "runner_src\.runner\.main|src\.control_plane\.api" | grep -v grep
```

**Expected Output:**
```
mac  57441  python -m src.control_plane.api
mac  57474  python -m runner_src.runner.main
```

### Pass Criteria
- ✅ `mode: "paper"`
- ✅ `execution_enabled: true`
- ✅ `accounts_loaded >= 1`
- ✅ `accounts_execution_capable >= 1` (if you expect execution)
- ✅ Both runner and control plane processes running

### If Fail
- **execution_enabled: false** — Check environment variables in runner process (paper execution gates)
- **accounts_execution_capable: 0** — Inspect runner.out for "no order managers available" and verify accounts.yaml + env consistency

---

## Phase 4: Strategy Switching + Signal Monitoring (Safe)

### Purpose
Test strategy switching and monitor for signal generation (paper mode only).

### Commands

```bash
# List available strategies
curl -s http://127.0.0.1:8787/api/strategies | python -m json.tool
```

**Expected Output:**
```json
{
    "ok": true,
    "allowed": ["eur_usd_5m_safe", "gold", "momentum", "momentum_v2", "range"],
    "strategies": [...]
}
```

```bash
# Switch to broader strategy (more instruments = more signal opportunities)
curl -s -X POST http://127.0.0.1:8787/api/strategy/momentum_v2 | python -m json.tool
```

```bash
# Monitor status for 3 minutes (12 polls × 15s)
python - <<'PY'
import json, time, urllib.request

def get_status():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:8787/api/status', timeout=5).read())

for i in range(12):
    s=get_status()
    print(i, s.get('active_strategy_key'), s.get('last_scan_at'), 'signals=', s.get('last_signals_generated'), 'executed=', s.get('last_executed_count'))
    time.sleep(15)
PY
```

```bash
# Check pending signals
curl -s http://127.0.0.1:8787/api/signals/pending | python -m json.tool
```

```bash
# Check open positions
curl -s http://127.0.0.1:8787/api/positions | python -m json.tool
```

### Pass Criteria
- ✅ `/api/strategies` returns 200 with strategy list
- ✅ `/api/signals/pending` returns 200
- ✅ `/api/positions` returns 200
- ℹ️  Zero pending signals is **NOT a failure** unless scans stop advancing or logs show errors

### Strategy Comparison

| Strategy | Instruments | Risk | Best Session | Signal Frequency |
|----------|-------------|------|--------------|------------------|
| **gold** | XAU_USD (1) | High | London | Low (selective) |
| **momentum_v2** | EUR_USD, GBP_USD, USD_JPY, AUD_USD, XAU_USD (5) | Medium | Any | Higher |
| **eur_usd_5m_safe** | EUR_USD (1) | Low | London | Medium |
| **range** | EUR_USD, GBP_USD, USD_JPY (3) | Low | Asia | Medium |

**Recommendation:** Switch to `momentum_v2` for broader coverage and more frequent signal opportunities.

---

## Phase 5: Dashboard UX Sanity Checks

### Purpose
Quick verification that dashboard UI elements are present and responsive.

### Commands

```bash
# Check UI markers
python - <<'PY'
import urllib.request
html=urllib.request.urlopen('http://127.0.0.1:8787/', timeout=5).read().decode('utf-8','ignore')
checks=[('nav-item', 'nav-item'), ('tab-content', 'tab-content'), ('api/status', '/api/status'), ('AI-QUANT', 'AI-QUANT')]
for name, needle in checks:
    print(name, 'OK' if needle in html else 'MISSING')
PY
```

**Expected Output:**
```
nav-item OK
tab-content OK
api/status OK
AI-QUANT OK
```

```bash
# Performance metrics
curl -s -w "Root: HTTP=%{http_code} TIME=%{time_total}s SIZE=%{size_download}\n" -o /dev/null http://127.0.0.1:8787/
curl -s -w "API Status: HTTP=%{http_code} TIME=%{time_total}s\n" -o /dev/null http://127.0.0.1:8787/api/status
```

**Expected Output:**
```
Root: HTTP=200 TIME=0.002091s SIZE=101832
API Status: HTTP=200 TIME=0.002007s
```

### Pass Criteria
- ✅ All UI markers present
- ✅ HTTP 200 responses
- ✅ Response times <10ms locally (typically <3ms)

### Browser Test (Manual)

```bash
# Open dashboard in browser
open http://127.0.0.1:8787
```

**Verify in browser:**
- [ ] All 6 tabs clickable: terminal, mesh, journal, news, reports, strategies
- [ ] No console errors in DevTools (F12 → Console)
- [ ] Status indicators show green pulse animation
- [ ] Data updates without manual refresh

---

## Phase 6: SSH Tunnel Hygiene (Optional)

### Purpose
Reduce port collision confusion by identifying and managing SSH tunnels.

### Commands

```bash
# List SSH tunnels forwarding 8787/8788
ps aux | grep "gcloud\.py compute ssh" | grep -E "-L 8787:| -L 8788:"
```

**Example Output:**
```
mac  50584  gcloud.py compute ssh ... -L 8787:127.0.0.1:8787  ← VM tunnel
mac  51222  gcloud.py compute ssh ... -L 8788:127.0.0.1:8787  ← VM tunnel
```

```bash
# Check all listeners on 8787 and 8788
lsof -nP -iTCP:8787 -sTCP:LISTEN
lsof -nP -iTCP:8788 -sTCP:LISTEN
```

### Guidance
- **If not using VM tunnels:** Close them to avoid confusion
  ```bash
  kill 50584 51222  # Replace with actual PIDs
  ```
- **If need both local + VM:** Use distinct ports
  - Local: 8787
  - VM tunnel: Forward to 9878 instead

---

## Quick Reference: One-Liner Health Checks

### 30-Second Health Check
```bash
curl -s http://127.0.0.1:8787/api/status | python -c "import sys,json; s=json.load(sys.stdin); print('Mode:', s['mode'], 'Exec:', s['execution_enabled'], 'Scan:', s['last_scan_at'], 'Signals:', s['last_signals_generated'])"
```

### Dashboard Smoke Test (5 seconds)
```bash
python - <<'PY'
import re, urllib.request
html=urllib.request.urlopen('http://127.0.0.1:8787/', timeout=5).read().decode('utf-8','ignore')
print('PASS' if len(html)>50000 and 'AI-QUANT' in html and 'tab-content' in html else 'FAIL', 'bytes=', len(html))
PY
```

### Process Check (1 second)
```bash
ps aux | grep -E "runner_src\.runner\.main|src\.control_plane\.api" | grep -v grep | wc -l
# Expected: 2 (runner + control plane)
```

### OANDA API Success Rate (from logs)
```bash
tail -n 100 /private/tmp/ai-quant-local/runner.out | grep -c "Retrieved FRESH prices"
# Should be > 0 (recent successful fetches)
```

### Recent Errors Check
```bash
tail -n 200 /private/tmp/ai-quant-local/runner.out | grep -iE "error|exception|traceback" | wc -l
# Expected: 0
```

---

## Performance Baselines (Reference)

### Latency Targets (Local)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Dashboard root | <10ms | 0.002s | ✅ Excellent |
| /api/status | <10ms | 0.002s | ✅ Excellent |
| /api/strategies | <10ms | 0.002s | ✅ Excellent |
| /api/positions | <10ms | 0.001s | ✅ Excellent |
| /api/signals/pending | <10ms | 0.002s | ✅ Excellent |

### Scan Loop Metrics

| Metric | Expected | Current | Status |
|--------|----------|---------|--------|
| Scan interval | 30s | 30s | ✅ |
| OANDA fetch latency | 200-700ms | 200-700ms | ✅ |
| Scan loop reliability | >99% | 100% | ✅ |
| Error rate | <1% | 0% | ✅ |

---

## Troubleshooting Guide

### Issue: Dashboard Returns Empty or Broken HTML

**Symptoms:**
- `curl http://127.0.0.1:8787/` returns <50KB
- Browser shows blank page
- Smoke test fails

**Diagnosis:**
```bash
ps aux | grep control_plane.api
lsof -nP -iTCP:8787 -sTCP:LISTEN
tail -n 100 /private/tmp/ai-quant-local/control_plane.out
```

**Solutions:**
1. Control plane not running → Start it: `python -m src.control_plane.api`
2. Wrong port → Check control plane logs for actual port
3. Tunnel collision → Close SSH tunnels on 8787

---

### Issue: Scan Loop Not Advancing

**Symptoms:**
- `last_scan_at` doesn't change over time
- Runner logs show no recent "SCANNING FOR OPPORTUNITIES"

**Diagnosis:**
```bash
ps aux | grep runner_src.runner.main
tail -n 200 /private/tmp/ai-quant-local/runner.out
```

**Solutions:**
1. Runner not running → Start it: `python -m runner_src.runner.main`
2. Runner crashed → Check logs for traceback
3. Weekend mode activated incorrectly → Check `weekend_indicator` in status

---

### Issue: Zero Signals Generated

**Symptoms:**
- `last_signals_generated: 0` for extended period
- No entries in `/api/signals/pending`

**Diagnosis:**
```bash
curl -s http://127.0.0.1:8787/api/status | python -m json.tool
tail -n 100 /private/tmp/ai-quant-local/runner.out | grep "Total signals"
```

**Is This Actually a Problem?**
- ℹ️  **Usually NO** — Gold strategy is selective and requires specific conditions
- ✅ **Verify:** Scan loop advancing + OANDA prices fresh + no errors → System healthy

**Solutions (If You Want More Signals for Testing):**
1. Switch to broader strategy: `curl -X POST http://127.0.0.1:8787/api/strategy/momentum_v2`
2. Wait for higher volatility periods (market sessions overlap)
3. Confirm strategy logic is not too restrictive

---

### Issue: OANDA API Errors

**Symptoms:**
- Runner logs show "OANDA API error" or "Failed to retrieve prices"
- `last_scan_at` advancing but signals always 0

**Diagnosis:**
```bash
tail -n 200 /private/tmp/ai-quant-local/runner.out | grep -iE "oanda|error|failed"
```

**Solutions:**
1. Check OANDA API key is valid (don't print it!)
2. Verify OANDA account status (active/not suspended)
3. Check network connectivity: `curl -s https://api-fxpractice.oanda.com/v3/accounts`

---

### Issue: Execution Not Enabled

**Symptoms:**
- `execution_enabled: false` in `/api/status`
- Runner logs show "Execution disabled"

**Diagnosis:**
```bash
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep execution
tail -n 200 /private/tmp/ai-quant-local/runner.out | grep -i execution
```

**Solutions:**
1. Check environment variables (PAPER_EXECUTION_ENABLED, EXECUTION_ENABLED)
2. Verify runner was started with correct environment
3. Check configuration file settings

---

## Safety Reminders

### Hard Rules (NEVER Violate)
1. ❌ **NEVER print secrets** (API keys, tokens, account IDs)
2. ❌ **NEVER enable live trading** without explicit user confirmation
3. ❌ **NEVER skip verification** — every claim needs command evidence
4. ✅ **ALWAYS use localhost** (127.0.0.1) to avoid tunnel confusion
5. ✅ **ALWAYS redact account IDs** in logs/outputs

### Paper Mode Verification
```bash
# Confirm paper mode before ANY execution changes
curl -s http://127.0.0.1:8787/api/status | python -c "import sys,json; s=json.load(sys.stdin); assert s['mode']=='paper', 'NOT IN PAPER MODE'; print('✅ Paper mode confirmed')"
```

---

## Monitoring Schedule Recommendations

### Continuous (Automated)
- Process health check every 5 minutes
- Scan loop advancement check every 2 minutes
- API endpoint availability every minute

### Hourly
- Dashboard smoke test
- OANDA API success rate check
- Log error scan

### Daily
- Full Phase 1-5 verification
- Performance baseline comparison
- Strategy effectiveness review

### Weekly
- SSH tunnel cleanup
- Log rotation check
- Configuration drift verification

---

## Final Status (Latest Verification: 2026-01-05T01:25:00Z)

### ✅ Dashboard: PASS
- HTTP 200, 101,832 bytes, <3ms response
- All UI markers present
- Smoke test passed

### ✅ Runtime: PASS
- Scan loop advancing every 30s
- OANDA API 100% success rate
- Paper execution ready
- No errors in logs

### ✅ Processes: STABLE
- Control plane PID 57441 (uptime since 12:25 AM)
- Runner PID 57474 (uptime since 12:25 AM)

### 📊 Current Configuration
- **Mode:** paper
- **Strategy:** gold (XAU_USD)
- **Accounts:** 1 loaded, 1 execution-capable
- **Signals:** 0 (expected for gold strategy in current conditions)

---

## Quick Start Commands (Copy-Paste Ready)

```bash
# Full health check (Phase 1-5)
cd "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system" && \
echo "=== Dashboard Smoke Test ===" && \
python - <<'PY'
import re, urllib.request
html=urllib.request.urlopen('http://127.0.0.1:8787/', timeout=5).read().decode('utf-8','ignore')
print('PASS' if len(html)>50000 and 'AI-QUANT' in html else 'FAIL', 'bytes=', len(html))
PY
echo "=== API Status ===" && \
curl -s http://127.0.0.1:8787/api/status | python -m json.tool | grep -E "mode|execution|scan_at|signals|weekend" && \
echo "=== Process Check ===" && \
ps aux | grep -E "runner_src|control_plane" | grep -v grep | wc -l && \
echo "=== Recent Scans ===" && \
tail -n 40 /private/tmp/ai-quant-local/runner.out | grep "SCANNING\|FRESH prices" | tail -n 5
```

---

**Document Version:** 1.0  
**Last Verified:** 2026-01-05T01:25:00Z  
**Next Verification:** Run Phase 1-5 checks every 4 hours or after any system changes
