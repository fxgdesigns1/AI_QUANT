# Control Plane Setup Guide

## Overview

The AI_QUANT Control Plane provides a web-based dashboard and API for managing the trading system without restarting the runner. It enables:

- **Strategy Switching**: Change active strategy from dashboard (hot-reload)
- **Config Management**: Update scan intervals, risk settings, etc.
- **Live Monitoring**: Real-time log streaming via SSE
- **Safe by Default**: Signals-only mode is preserved; execution requires dual-confirm environment variables

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Dashboard     │◄───────►│  Control Plane   │
│   (Browser)     │  HTTP   │   API (FastAPI)  │
└─────────────────┘         └────────┬─────────┘
                                     │
                                     ▼
                            runtime/config.yaml
                                     │
                                     ▼ (hot-reload)
                            ┌─────────────────┐
                            │  Runner (main)  │
                            │  working_trading│
                            │     _system.py  │
                            └─────────────────┘
```

## Installation

### Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn pydantic pyyaml python-dotenv
```

### Directory Structure

```
repo-root/
├── src/control_plane/
│   ├── __init__.py
│   ├── api.py              # FastAPI service
│   ├── schema.py           # Config schema & validation
│   ├── config_store.py     # Atomic config manager
│   ├── strategy_registry.py # Strategy metadata
│   └── log_stream.py       # SSE log streaming
├── runtime/
│   ├── config.yaml         # Runtime config (hot-reload)
│   └── config.example.yaml # Example template
├── dashboard/
│   └── control_plane.html  # Dashboard UI
├── logs/
│   └── ai_quant.log        # Log file (streamed to dashboard)
└── scripts/
    └── run_control_plane.sh # Startup script
```

## Running Locally

### 1. Set Environment Variables (Optional)

```bash
# Control plane configuration
export CONTROL_PLANE_HOST="127.0.0.1"  # Default: localhost only
export CONTROL_PLANE_PORT="8787"       # Default: 8787
export CONTROL_PLANE_TOKEN="your-secure-token-here"  # REQUIRED for production

# Config and log paths
export RUNTIME_CONFIG_PATH="runtime/config.yaml"  # Default
export LOG_FILE_PATH="logs/ai_quant.log"          # Default
```

### 2. Start Control Plane API

```bash
# Option A: Using startup script
./scripts/run_control_plane.sh

# Option B: Direct Python
python -m src.control_plane.api
```

### 3. Access Dashboard

```
http://127.0.0.1:8787/
```

API documentation: `http://127.0.0.1:8787/docs`

## Running on VM (Production)

### 1. SSH Tunnel (Recommended)

```bash
# On your local machine
ssh -L 8787:127.0.0.1:8787 user@vm-hostname

# Access dashboard locally
# http://localhost:8787/
```

### 2. Systemd Service (Optional)

Create `/etc/systemd/system/ai-quant-control-plane.service`:

```ini
[Unit]
Description=AI_QUANT Control Plane API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/repo
Environment="CONTROL_PLANE_TOKEN=your-secure-token"
Environment="CONTROL_PLANE_HOST=127.0.0.1"
Environment="CONTROL_PLANE_PORT=8787"
ExecStart=/usr/bin/python3 -m src.control_plane.api
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable ai-quant-control-plane
sudo systemctl start ai-quant-control-plane
sudo systemctl status ai-quant-control-plane
```

### 3. Nginx Reverse Proxy (Optional)

If you want to expose the API externally (with auth):

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # Important for SSE
    }
}
```

## How Runner Hot-Reload Works

1. **Config File Modified**: Dashboard POSTs update to `/api/config` or `/api/strategy/activate`
2. **Atomic Write**: ConfigStore writes to temp file → fsync → atomic rename (with backup)
3. **Change Detection**: Runner checks config file mtime before each scan iteration
4. **Reload**: If changed, runner loads new config and applies settings deterministically
5. **No Restart Required**: Strategy selection, scan interval, risk settings update without downtime

### Runner Integration Points

In `working_trading_system.py`:

```python
# Before each scan (in run_forever loop)
system._check_config_reload()  # Detects config changes

# Strategy selection (in scan_and_execute)
strategy = system._get_active_strategy_instance()  # Maps config key to instance
```

### What Can Be Hot-Reloaded

✅ **Hot-Reloadable** (no restart):
- Active strategy selection
- Scan interval
- Risk settings (max_risk, max_positions, etc.)
- News integration toggles
- UI preferences

❌ **Requires Restart**:
- Account configurations (YAML-based)
- Strategy code changes (Python files)
- Environment variables (execution gates)

## API Endpoints

### GET /api/status

Returns current system status:

```json
{
  "mode": "paper",
  "execution_enabled": false,
  "accounts_loaded": 0,
  "accounts_execution_capable": 0,
  "active_strategy_key": "momentum",
  "last_scan_at": "2026-01-03T10:30:00Z",
  "last_signals_generated": 3,
  "last_executed_count": 0,
  "weekend_indicator": true,
  "config_mtime": 1704276000.0
}
```

### GET /api/config

Returns sanitized runtime config (NO SECRETS):

```json
{
  "active_strategy_key": "momentum",
  "scan_interval_seconds": 30,
  "default_instruments": ["EUR_USD", "GBP_USD", "XAU_USD"],
  "risk": {
    "max_risk_per_trade_pct": 1.0,
    "max_positions": 3,
    "max_daily_loss_pct": 5.0,
    "max_drawdown_pct": 10.0
  },
  "execution_policy": {
    "signals_only": true,
    "paper_execution_enabled": false,
    "live_trading_allowed": false
  }
}
```

### GET /api/strategies

Returns available strategies with metadata:

```json
{
  "strategies": [
    {
      "key": "momentum",
      "name": "Momentum Trading",
      "description": "Trend-following strategy using momentum indicators",
      "instruments": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
      "risk_level": "medium",
      "session_preference": "any"
    }
  ]
}
```

### POST /api/config

Update runtime config (requires auth):

```bash
curl -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_interval_seconds": 60,
    "risk": {
      "max_risk_per_trade_pct": 2.0,
      "max_positions": 5
    }
  }'
```

### POST /api/strategy/activate

Activate a strategy (requires auth):

```bash
curl -X POST http://127.0.0.1:8787/api/strategy/activate \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_key": "gold", "scope": "global"}'
```

### GET /api/logs/stream

Server-Sent Events log stream (with secret redaction):

```bash
curl http://127.0.0.1:8787/api/logs/stream
```

Browser:

```javascript
const eventSource = new EventSource('/api/logs/stream');
eventSource.onmessage = (event) => {
  console.log(event.data);
};
```

## Security

### Authentication

- **Bearer Token Required**: All POST endpoints require `Authorization: Bearer <token>` header
- **Token Configuration**: Set `CONTROL_PLANE_TOKEN` environment variable
- **Default Binding**: `127.0.0.1` only (not exposed externally by default)

### Secret Redaction

- **Config Files**: Never contain secrets (OANDA_API_KEY comes from environment only)
- **API Responses**: Sanitized to remove any secret patterns
- **Log Streaming**: Automatic redaction of API keys, passwords, tokens

Redacted patterns:
- `OANDA_API_KEY=***REDACTED***`
- `token=***REDACTED***`
- `password=***REDACTED***`

### Execution Safety

**CRITICAL**: Control plane CANNOT bypass execution gates.

Execution requires ALL of:
1. Correct environment variables (`LIVE_TRADING=true` + `LIVE_TRADING_CONFIRM=true` for live)
2. Valid broker credentials
3. Non-placeholder account IDs
4. Execution gate approval

Changing `execution_policy` in config is **ADVISORY ONLY** — runner enforces actual gates.

## Troubleshooting

### Dashboard shows "Loading..." forever

- Check API is running: `curl http://127.0.0.1:8787/health`
- Check browser console for CORS or network errors
- Verify `dashboard/control_plane.html` exists

### Config changes not applied

- Check runner logs for hot-reload messages: `🔄 Runtime config changed - reloading...`
- Verify config file is valid YAML: `python -c "import yaml; yaml.safe_load(open('runtime/config.yaml'))"`
- Check config validation errors in API logs

### Log stream not working

- Verify log file exists and is being written: `tail -f logs/ai_quant.log`
- Check `LOG_FILE_PATH` environment variable
- Ensure runner is actually running and logging

### Strategies not appearing

- Check strategy registry: `python -c "from src.control_plane.strategy_registry import STRATEGIES; print(STRATEGIES.keys())"`
- Verify strategy imports in `working_trading_system.py`

## Testing

### Unit Tests

```bash
# Run all control plane tests
pytest tests/test_control_plane_config.py -v
pytest tests/test_config_store.py -v
pytest tests/test_hot_reload_integration.py -v
```

### Integration Test: Signals-Only Mode

```bash
# Run runner in signals-only mode for 1 iteration
MAX_ITERATIONS=1 \
TRADING_MODE=paper \
PAPER_EXECUTION_ENABLED=false \
PAPER_ALLOW_OANDA_NETWORK=true \
python -m runner_src.runner.main 2>&1 | \
rg -n "Order manager initialized|EXECUTED|place_market_order|Submitting|ORDER_CREATE|TRADE_OPEN|TRADE_CLOSE" && \
echo "❌ UNEXPECTED: Execution markers found in signals-only mode" || \
echo "✅ OK: Signals-only mode is safe"
```

### API Test

```bash
# Test API is running and responding
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/api/status
curl http://127.0.0.1:8787/api/strategies

# Test config update (with auth)
curl -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scan_interval_seconds": 45}'
```

## Maintenance

### Config Backup

Config backups are created automatically at `runtime/config.yaml.bak` on every save.

Manual backup:

```bash
cp runtime/config.yaml runtime/config.yaml.backup.$(date +%Y%m%d_%H%M%S)
```

### Log Rotation

Set up log rotation for `logs/ai_quant.log`:

```bash
# /etc/logrotate.d/ai-quant
/path/to/repo/logs/ai_quant.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 user user
    postrotate
        # No need to restart - log stream will detect file recreation
    endscript
}
```

## Next Steps

1. Set `CONTROL_PLANE_TOKEN` for production
2. Configure SSH tunnel or reverse proxy for remote access
3. Test strategy switching from dashboard
4. Monitor hot-reload behavior in runner logs
5. Set up systemd service for auto-start

## Support

For issues, check:
- Control plane logs: `journalctl -u ai-quant-control-plane -f` (if using systemd)
- Runner logs: `tail -f logs/ai_quant.log`
- API docs: `http://127.0.0.1:8787/docs`
