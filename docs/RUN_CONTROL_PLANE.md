# Control Plane Runbook

**Quick Start Guide for Starting, Stopping, and Verifying the Control Plane API**

## Overview

The Control Plane API runs on `http://127.0.0.1:8787` and requires a Bearer token for POST operations (e.g., strategy switching, config updates).

## Prerequisites

- Python 3 with FastAPI, uvicorn, pydantic, pyyaml installed
- Port 8787 available (or use scripts to stop existing listeners)

## Quick Start

### 1. Stop Any Existing Server

```bash
bash scripts/stop_control_plane.sh
```

**Expected output:**
```
🔍 Checking for listeners on port 8787...
✅ Port 8787 is now free
```

If a process was found, it will be stopped gracefully (SIGTERM, then SIGKILL if needed).

---

### 2. Start Server with Fresh Token

```bash
bash scripts/start_control_plane_clean.sh
```

**Expected output:**
```
🛑 Stopping any existing listeners on port 8787...
✅ Port 8787 is now free
🔑 Generating new CONTROL_PLANE_TOKEN...
   Token generated (first 8 chars: a1b2c3d4...)

⚠️  IMPORTANT: Save this token for dashboard Settings:
   Full token: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
   Or export: export CONTROL_PLANE_TOKEN="a1b2c3d4..."

🚀 Starting Control Plane server...
   Listening on: http://127.0.0.1:8787
   Token (first 8): a1b2c3d4...
```

**Important:** Copy the full token shown. You'll need it for:
- Dashboard Settings modal
- Manual curl testing
- Verification script

**Note:** The token is also saved to `/tmp/control_plane_token_current.txt` for the verification script.

**To run in background:** Append `&` or use `nohup`:
```bash
nohup bash scripts/start_control_plane_clean.sh > /tmp/control_plane.log 2>&1 &
```

---

### 3. Verify Server is Running

```bash
# Check listener
lsof -nP -iTCP:8787 -sTCP:LISTEN

# Test health endpoint
curl -s http://127.0.0.1:8787/health | python3 -m json.tool

# Test status endpoint
curl -s http://127.0.0.1:8787/api/status | python3 -m json.tool
```

**Expected status response:**
```json
{
    "mode": "paper",
    "execution_enabled": false,
    "accounts_loaded": 0,
    "accounts_execution_capable": 0,
    "active_strategy_key": "momentum",
    "last_scan_at": null,
    "last_signals_generated": 0,
    "last_executed_count": 0,
    "weekend_indicator": true,
    "config_mtime": 1767470761.438021
}
```

---

### 4. Verify Authentication Works

```bash
# Use token from start script output or /tmp/control_plane_token_current.txt
TOKEN=$(cat /tmp/control_plane_token_current.txt)

# Run verification script
bash scripts/verify_control_plane.sh "$TOKEN"
```

**Expected output:**
```
🔍 Verifying Control Plane...

1️⃣  Checking port 8787 listener...
   ✅ Listener found: PID 12345

2️⃣  Testing GET /api/status...
   ✅ Status: mode=paper, execution_enabled=False, active_strategy=momentum

2.5️⃣ Testing GET /api/strategies...
   ✅ Strategies catalog: 5 allowed keys: eur_usd_5m_safe,gold,momentum,momentum_v2,range

3️⃣  Testing POST /api/config with Bearer token...
   ✅ POST /api/config succeeded

4️⃣  Verifying active_strategy_key updated...
   ✅ active_strategy_key = gold (updated successfully)

✅ All verification tests passed!
```

---

## Manual Testing

### Test POST /api/config with curl

```bash
# Set token
export CONTROL_PLANE_TOKEN="your-token-here"

# Update strategy
curl -s -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"active_strategy_key":"gold"}' | python3 -m json.tool
```

**Expected response:**
```json
{
    "status": "ok",
    "message": "Config updated successfully",
    "config": {
        "active_strategy_key": "gold",
        ...
    }
}
```

**Valid strategy keys:** `gold`, `momentum`, `range`, `eur_usd_5m_safe`, `momentum_v2`

**Get allowed keys from backend (authoritative source):**
```bash
curl -s http://127.0.0.1:8787/api/strategies | python3 -m json.tool
```

**Expected response:**
```json
{
    "ok": true,
    "allowed": ["eur_usd_5m_safe", "gold", "momentum", "momentum_v2", "range"],
    "default": "momentum",
    "strategies": [...]
}
```

**Note:** The `allowed` array is the authoritative source of valid strategy keys. The frontend validates against this list before POSTing `/api/config`.

---

## Using Token in Dashboard

1. **Start server** (see step 2 above) and copy the full token
2. **Open dashboard:** http://127.0.0.1:8787/
3. **Click Settings** (⚙️ button in top bar)
4. **Paste token** into the "Control Plane Token" field
5. **Click Save** (token stored in `localStorage.control_plane_token`)
6. **Strategy catalog loads automatically:** Dashboard fetches `/api/strategies` on boot to validate strategy keys
7. **Test strategy switch:** Click a strategy button (GOLD_SCALPER_v4.2, MEAN_REV_CORE, BREAKOUT_HUNTER) to verify POST works
   - Frontend validates the mapped key against the backend catalog before POSTing
   - If catalog load fails, strategy switching is blocked to prevent invalid keys

---

## Troubleshooting

### Problem: "address already in use" (port 8787)

**Solution:**
```bash
bash scripts/stop_control_plane.sh
```

If that doesn't work, manually find and kill:
```bash
lsof -t -iTCP:8787 -sTCP:LISTEN | xargs kill -9
```

---

### Problem: "Invalid authentication token" on POST

**Causes:**
1. Token mismatch: Server was started with different token than you're using
2. Token not set: Server started without `CONTROL_PLANE_TOKEN` (auth disabled)
3. Wrong token: Typo or wrong token pasted

**Solution:**
1. **Check what token server has:**
   - If you started with `start_control_plane_clean.sh`, check `/tmp/control_plane_token_current.txt`
   - Or restart server with known token: `export CONTROL_PLANE_TOKEN="your-token" && bash scripts/start_control_plane_clean.sh`

2. **Verify token format:**
   - Should be 64 hex characters (32 bytes = 64 hex chars)
   - Example: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2`

3. **Test with curl:**
   ```bash
   curl -v -X POST http://127.0.0.1:8787/api/config \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"active_strategy_key":"gold"}'
   ```
   - If you see `401 Unauthorized` → token mismatch
   - If you see `200 OK` → token works

---

### Problem: "Invalid config: Invalid active_strategy_key"

**Cause:** Strategy key doesn't exist in registry.

**Valid keys:** `gold`, `momentum`, `range`, `eur_usd_5m_safe`, `momentum_v2`

**Solution:** Use a valid strategy key from the list above.

---

### Problem: Logs not appearing

**Expected location:** `logs/ai_quant.log`

**Check:**
```bash
ls -la logs/
tail -f logs/ai_quant.log
```

**Note:** Log file is created when first log entry is written. Directory is created automatically on startup.

---

### Problem: Server won't start

**Check dependencies:**
```bash
python3 -c "import fastapi, uvicorn, pydantic, yaml"
```

**Install if missing:**
```bash
pip install fastapi uvicorn pydantic pyyaml
```

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/stop_control_plane.sh` | Stop any listener on port 8787 |
| `scripts/start_control_plane_clean.sh` | Start server with fresh token |
| `scripts/verify_control_plane.sh [token]` | Verify server + auth works |

---

## Security Notes

- **Token is never logged** to committed files (only printed to stdout/stderr)
- **Token is stored** in `/tmp/control_plane_token_current.txt` (temporary, user can delete)
- **Dashboard stores token** in `localStorage.control_plane_token` (browser-only, not sent to server except in Authorization header)
- **No secrets in logs:** Log stream redacts API keys, tokens, passwords
- **Signals-only default:** `execution_enabled=false`, `mode=paper` by default

---

## Complete Example Workflow

```bash
# 1. Stop any existing server
bash scripts/stop_control_plane.sh

# 2. Start with fresh token
bash scripts/start_control_plane_clean.sh &
# Copy the token from output

# 3. Wait for server to start (3-5 seconds)
sleep 5

# 4. Verify everything works
TOKEN=$(cat /tmp/control_plane_token_current.txt)
bash scripts/verify_control_plane.sh "$TOKEN"

# 5. Open dashboard and paste token in Settings
open http://127.0.0.1:8787/
```

---

**Last Updated:** 2026-01-04  
**Status:** ✅ Verified Working
