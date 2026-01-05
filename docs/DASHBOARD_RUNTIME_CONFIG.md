# Dashboard Runtime Config Integration

## Overview

The AI_QUANT dashboard now integrates with the Control Plane API for real-time configuration management. Strategy switching, config updates, and log monitoring happen live without restarting the trading system.

## Features

### 1. Strategy Switching (Hot-Reload)

**Dashboard UI**: Click strategy cards in "Strategy Selection" section

**Behind the Scenes**:
```
User clicks "Gold Scalping" button
  ↓
POST /api/strategy/activate {"strategy_key": "gold"}
  ↓
ConfigStore atomically writes to runtime/config.yaml
  ↓
Runner detects change before next scan iteration
  ↓
Runner reloads config and switches to gold strategy
  ↓
Dashboard refreshes and shows new active strategy
```

**Safety**: Strategy switching is safe in signals-only mode. No execution components are initialized.

### 2. Config Hot-Reload

**Dashboard UI**: Update settings in "Runtime Config" section and click "Save Config"

**Supported Settings**:
- Scan interval (1-3600 seconds)
- Max risk per trade (0.1-10%)
- Max positions (1-20)
- Risk management thresholds

**Behind the Scenes**:
```
User updates scan interval to 60s and clicks Save
  ↓
POST /api/config {"scan_interval_seconds": 60}
  ↓
API validates config (rejects if invalid)
  ↓
ConfigStore atomically writes + creates backup
  ↓
Runner detects change in run_forever loop
  ↓
Runner applies new scan interval (next iteration waits 60s)
  ↓
Dashboard polls status and shows updated interval
```

**Validation**: Invalid values are rejected server-side. Old config is preserved if validation fails.

### 3. Live Log Streaming

**Dashboard UI**: "Live Terminal" section shows real-time logs

**Technology**: Server-Sent Events (SSE)

**Behind the Scenes**:
```
Dashboard opens EventSource('/api/logs/stream')
  ↓
API tails logs/ai_quant.log
  ↓
New log lines are pushed to browser as SSE events
  ↓
Secret patterns are redacted before streaming
  ↓
Dashboard appends lines to terminal UI
```

**Secret Redaction**: Automatic redaction of:
- OANDA_API_KEY
- Passwords
- Tokens
- Other sensitive patterns

### 4. System Status Monitoring

**Dashboard UI**: Status chips at top show mode, execution status, accounts

**Polling**: Dashboard fetches `/api/status` every 10 seconds

**Status Indicators**:

| Chip Color | Meaning |
|-----------|---------|
| 🔵 Blue (Paper) | Signals-only mode (safe) |
| 🟢 Green (Live) | Live trading enabled |
| 🔴 Red (Blocked) | Execution blocked by gate |
| 🟠 Orange (Weekend) | Markets closed |

**Execution Capability Count**:
- Shows `0` in signals-only mode
- Shows `N` when execution enabled and valid brokers available

## Dashboard Architecture

```
┌────────────────────────────────────────────┐
│           Browser (Dashboard UI)           │
│                                            │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │ Strategy     │  │  Config Editor   │  │
│  │ Selector     │  │                  │  │
│  └──────┬───────┘  └────────┬─────────┘  │
│         │                    │            │
│         └────────┬───────────┘            │
│                  │ HTTP POST              │
└──────────────────┼────────────────────────┘
                   │
          ┌────────▼─────────┐
          │  Control Plane   │
          │  API (FastAPI)   │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │ runtime/         │
          │ config.yaml      │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │  Runner (main)   │
          │  Hot-reload      │
          └──────────────────┘
```

## Safety Features

### 1. Signals-Only Warning Banner

When execution is disabled (signals-only mode), dashboard shows:

```
⚠️ Signals-only mode — no execution possible.
   Signals will be generated but not executed.
```

### 2. Execution Gate Enforcement

**CRITICAL**: Dashboard CANNOT enable live trading alone.

Live trading requires:
1. `LIVE_TRADING=true` (environment)
2. `LIVE_TRADING_CONFIRM=true` (environment)
3. Valid broker credentials
4. Non-placeholder account IDs

Changing `execution_policy` in dashboard config is **advisory only**.

### 3. Weekend Indicator

Dashboard detects weekends and shows warning:

```
🟠 Weekend detected — markets closed.
   Signals-only mode recommended.
```

### 4. Config Validation

Invalid configs are rejected:

```javascript
// User tries to set scan_interval_seconds = -1
POST /api/config {"scan_interval_seconds": -1}

// Response: 400 Bad Request
{
  "detail": "Config validation failed: scan_interval_seconds must be >= 1"
}
```

Old config is preserved; no changes applied.

## Usage Workflow

### Scenario 1: Change Strategy from Momentum to Gold

**Steps**:
1. Open dashboard: `http://127.0.0.1:8787/`
2. Locate "Strategy Selection" card
3. Click "Gold Scalping" button
4. Strategy button turns green (active)
5. Watch "Live Terminal" for reload message:
   ```
   🔄 Runtime config changed - reloading...
      Strategy changed: momentum → gold
   ✅ Runtime config reloaded successfully
   ```
6. Next scan uses gold strategy

**Time**: < 1 second (no restart required)

### Scenario 2: Increase Scan Interval

**Steps**:
1. Locate "Runtime Config" card
2. Change "Scan Interval" from 30 to 60
3. Click "💾 Save Config" button
4. Watch for confirmation in terminal:
   ```
   ✅ Config saved successfully
   🔄 Runtime config changed - reloading...
      Scan interval changed: 30s → 60s
   ```
5. Next iteration waits 60 seconds instead of 30

### Scenario 3: Monitor Live Signals

**Steps**:
1. Scroll to "Live Terminal" section
2. Terminal auto-scrolls as new logs appear
3. Watch for scan cycle logs:
   ```
   [10:30:00] 🔍 SCANNING FOR OPPORTUNITIES...
   [10:30:02] 📊 momentum generated 2 signals for account ***
   [10:30:02] 📄 Execution disabled (signals-only) — signals generated: 2, executed: 0
   [10:30:02] ⏰ Next scan in 30 seconds...
   ```

## Technical Details

### API Integration Code

Dashboard uses standard Fetch API:

```javascript
// Fetch status
const res = await fetch('/api/status');
const status = await res.json();

// Activate strategy (requires auth if CONTROL_PLANE_TOKEN set)
const res = await fetch('/api/strategy/activate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'  // If required
  },
  body: JSON.stringify({
    strategy_key: 'gold',
    scope: 'global'
  })
});

// SSE log streaming
const eventSource = new EventSource('/api/logs/stream');
eventSource.onmessage = (event) => {
  addLogLine(event.data);
};
```

### Runner Hot-Reload Logic

In `working_trading_system.py`:

```python
def run_forever(max_iterations: int = 0):
    system = WorkingTradingSystem()
    
    while True:
        # HOT-RELOAD: Check for config changes before each scan
        system._check_config_reload()
        
        executed = system.scan_and_execute()
        
        # Use dynamically loaded scan interval
        scan_interval = system._scan_interval
        time.sleep(scan_interval)
```

Config reload logic:

```python
def _check_config_reload(self):
    config_store = ConfigStore()
    current_mtime = config_store.get_mtime()
    
    if current_mtime > self._config_last_mtime:
        config = config_store.load()
        self._active_strategy_key = config.active_strategy_key
        self._scan_interval = config.scan_interval_seconds
        self._config_last_mtime = current_mtime
        logger.info("✅ Runtime config reloaded successfully")
```

## Limitations

### What is NOT Hot-Reloadable

❌ **Account Configurations**: Accounts are loaded once at startup from YAML. Adding/removing accounts requires runner restart.

❌ **Strategy Code**: Changing Python code in `src/strategies/*.py` requires restart. Hot-reload only switches between existing strategies.

❌ **Environment Variables**: Execution gates (`LIVE_TRADING`, `PAPER_EXECUTION_ENABLED`) are read at startup. Changing these requires restart.

❌ **Broker Credentials**: `OANDA_API_KEY` is loaded at startup. Changes require restart.

### Performance

- **Config Check Overhead**: Minimal (~1ms per scan iteration)
- **File Watch**: Uses mtime check, not inotify (portable across OS)
- **Reload Time**: < 100ms for config reload
- **No Code Reload**: Does not use `importlib.reload()` (safe, deterministic)

## Troubleshooting

### Strategy change not applied

**Check runner logs**:
```bash
tail -f logs/ai_quant.log | grep -i "config changed"
```

Expected output:
```
🔄 Runtime config changed - reloading...
   Strategy changed: momentum → gold
✅ Runtime config reloaded successfully
```

**Verify config file**:
```bash
cat runtime/config.yaml | grep active_strategy_key
```

### Config save fails with validation error

**Check API response** in browser console:
```
Failed to save config: Config validation failed: scan_interval_seconds must be >= 1
```

**Fix**: Correct invalid values in dashboard form.

### Log stream not updating

**Check browser console** for errors:
```
EventSource failed
```

**Fix**:
1. Verify API is running: `curl http://127.0.0.1:8787/health`
2. Check log file exists: `ls -lh logs/ai_quant.log`
3. Verify runner is writing logs: `tail -f logs/ai_quant.log`

### Dashboard shows wrong status

**Force refresh**: Dashboard polls status every 10 seconds. Wait or refresh browser.

**Check API directly**:
```bash
curl http://127.0.0.1:8787/api/status | jq
```

## Best Practices

1. **Use SSH Tunnel on VM**: Don't expose control plane publicly without reverse proxy + TLS
2. **Set Auth Token in Production**: Always set `CONTROL_PLANE_TOKEN` on VM
3. **Monitor Hot-Reload Logs**: Watch for config reload messages in terminal
4. **Backup Config Before Major Changes**: `cp runtime/config.yaml runtime/config.yaml.backup`
5. **Test in Signals-Only First**: Verify strategy changes work before enabling execution

## Future Enhancements

Potential future features (not implemented yet):

- [ ] Multi-account strategy assignment (per-account strategy keys)
- [ ] Historical config version browser
- [ ] Strategy performance metrics in dashboard
- [ ] Real-time signal preview (what signals would be generated now)
- [ ] Config diff viewer (show what changed)
- [ ] Role-based access (read-only vs admin users)

## See Also

- [CONTROL_PLANE_SETUP.md](CONTROL_PLANE_SETUP.md) - API setup and deployment
- [DEV_SETUP_AI.md](DEV_SETUP_AI.md) - Execution gates and safety
- Control Plane Dashboard: `http://127.0.0.1:8787/`
- API Docs: `http://127.0.0.1:8787/docs`
