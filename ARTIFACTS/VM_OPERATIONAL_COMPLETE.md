# VM Operational Status Report

**Date:** 2026-01-06  
**VM:** fxg-quant-paper-e2-micro (us-east1-b)  
**Project:** fxg-ai-trading

---

## ✅ COMPLETED SETUP STEPS

### 1. Repository Setup
- **Location:** `/opt/ai-quant`
- **User:** `aiquant`
- **Ownership:** Correctly set to `aiquant:aiquant`
- **Status:** ✅ Complete

### 2. Environment Configuration
- **.env location:** `/etc/ai-quant/.env`
- **Permissions:** 600 (correct)
- **Git status:** ✅ `.env` is git-ignored (added to `.gitignore` on VM)
- **Status:** ✅ Complete

### 3. Systemd Units
- **Units installed:**
  - `ai-quant-control-plane.service`
  - `ai-quant-runner.service`
- **Location:** `/etc/systemd/system/`
- **Status:** ✅ Installed and enabled

### 4. Dependencies
- **Python:** 3.9.2
- **Venv:** Created at `/opt/ai-quant/.venv`
- **Requirements:** Installed from `requirements.txt`
- **Status:** ✅ Complete

### 5. Services Status

#### Control Plane Service
- **Status:** ⚠️ Starting (may need restart after snapshot_store.py sync)
- **Port:** 8787
- **Health endpoint:** `/health`
- **Issue resolved:** Added `snapshot_store.py` module (was missing)

#### Runner Service
- **Status:** ✅ Active
- **Accounts loaded:** ✅ Working (`accounts_loaded: 1`)
- **Scan interval:** 30 seconds
- **Mode:** Paper (signals-only by default)

---

## 📋 VERIFICATION COMMANDS

### Service Status
```bash
sudo systemctl status ai-quant-control-plane.service
sudo systemctl status ai-quant-runner.service
```

### Service Management
```bash
# Start services
sudo systemctl start ai-quant-control-plane.service
sudo systemctl start ai-quant-runner.service

# Stop services
sudo systemctl stop ai-quant-control-plane.service
sudo systemctl stop ai-quant-runner.service

# Restart services
sudo systemctl restart ai-quant-control-plane.service
sudo systemctl restart ai-quant-runner.service

# View logs
sudo journalctl -u ai-quant-control-plane.service -f
sudo journalctl -u ai-quant-runner.service -f
```

### Health Checks
```bash
# Control plane health
curl -fsS http://127.0.0.1:8787/health

# System status
curl -fsS http://127.0.0.1:8787/api/status | python3 -m json.tool

# Live prices
curl -fsS http://127.0.0.1:8787/api/sidebar/live-prices | python3 -m json.tool
```

### Full Stack Verification
```bash
cd /opt/ai-quant
ENV_FILE=/etc/ai-quant/.env bash scripts/verify_vm_full_stack.sh
ENV_FILE=/etc/ai-quant/.env bash scripts/verify_telegram.sh
```

---

## 🔒 SAFETY GATES (VERIFIED)

1. **TRADING_MODE:** Defaults to `paper` ✅
2. **PAPER_EXECUTION_ENABLED:** Defaults to `false` ✅
3. **Execution status:** `execution_enabled: false` (signals-only) ✅
4. **No order placement in verification scripts** ✅

---

## ⚠️ KNOWN ISSUES / NEXT STEPS

### 1. Control Plane Module Import
- **Issue:** `snapshot_store.py` was missing (now copied)
- **Action:** Control plane service may need restart after file sync
- **Status:** ⚠️ In progress

### 2. Live Prices
- **Issue:** `live_prices` may be empty initially
- **Expected:** Prices populate after runner completes first scan cycle (30s interval)
- **Action:** Wait for runner to complete scan and check again
- **Status:** ⚠️ Monitoring

### 3. Verification Scripts
- **Issue:** Permission handling for `/etc/ai-quant/.env` (0600)
- **Action:** Updated scripts to handle sudo-based env loading
- **Status:** ✅ Fixed

---

## 📊 EXPECTED OUTPUTS

### `/api/status` Response
```json
{
  "mode": "paper",
  "execution_enabled": false,
  "accounts_loaded": 1,
  "accounts_execution_capable": 0,
  "active_strategy_key": "gold",
  "last_scan_at": "2026-01-06T...",
  "weekend_indicator": false
}
```

### `/api/sidebar/live-prices` Response
```json
{
  "success": true,
  "prices": {
    "XAU_USD": {
      "bid": ...,
      "ask": ...,
      "mid": ...,
      "time": ...
    }
  },
  "warning": "none" | "market_closed" | "no_prices_available" | ...
}
```

---

## 🔧 TROUBLESHOOTING

### If services fail to start:
1. Check logs: `sudo journalctl -u <service-name> -n 50`
2. Verify env file exists: `sudo ls -la /etc/ai-quant/.env`
3. Verify repo exists: `ls -la /opt/ai-quant`
4. Restart services: `sudo systemctl restart <service-name>`

### If accounts_loaded is 0:
1. Check `.env` has `OANDA_ACCOUNT_ID` set (not placeholder)
2. Check runner logs for account loading errors
3. Verify account ID is valid OANDA practice account

### If live_prices is empty:
1. Wait for runner to complete first scan (30s)
2. Check runner logs for market data fetch errors
3. Verify OANDA_API_KEY is set correctly
4. Check snapshot: `sudo -u aiquant cat /opt/ai-quant/runtime/status.json`

---

## 📝 FILES MODIFIED/CREATED

### System Files
- `/etc/systemd/system/ai-quant-control-plane.service`
- `/etc/systemd/system/ai-quant-runner.service`
- `/etc/ai-quant/.env` (0600)

### Repository Files
- `/opt/ai-quant/working_trading_system.py` (updated to use snapshot_store)
- `/opt/ai-quant/src/control_plane/api.py` (updated for warning logic)
- `/opt/ai-quant/src/control_plane/snapshot_store.py` (copied)
- `/opt/ai-quant/scripts/verify_vm_full_stack.sh` (permission fix)
- `/opt/ai-quant/scripts/verify_telegram.sh` (permission fix)

---

## ✅ VERIFICATION CHECKLIST

- [x] Systemd units installed
- [x] .env configured and secure (0600)
- [x] Dependencies installed
- [x] Venv created
- [x] Runner service active
- [x] Accounts loading (accounts_loaded > 0)
- [x] Control plane module dependencies resolved
- [x] Verification scripts updated
- [ ] Control plane service fully operational (may need restart)
- [ ] Live prices populated (monitoring)
- [ ] All verification commands passing

---

**Last Updated:** 2026-01-06  
**Next Action:** Restart control plane service and verify all endpoints respond correctly.
