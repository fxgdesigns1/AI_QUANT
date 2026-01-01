Remote Cloud Health Check
========================

Purpose
- Validate reachability and health of remote cloud services used by the trading system.
- Produce a machine-readable report suitable for automation and alerting.

Prerequisites
- Python 3.x
- PyYAML (optional for config)
- SSH access to remote hosts (key-based or agent)

Usage
- Run locally:
  ```bash
  python3 scripts/remote_health_check.py
  ```
- Optional: override config with environment variable:
  ```bash
  CLOUD_REMOTE_HEALTH_CONFIG=/path/to/config.yaml python3 scripts/remote_health_check.py
  ```
- Sample config available at `config/remote_health_config.yaml`.

Output
- JSON report with per-endpoint health_status and details.
- Example:
```json
{
  "timestamp": "2025-11-21T12:34:56.789Z",
  "endpoints": {
    "remote_host_1": {
      "host": "remote.example.com",
      "port": 22,
      "health_status": "running",
      "active_line": "Active: active (running) since ...",
      "stdout": "...",
      "stderr": ""
    }
  }
}
```

Notes
- Replace placeholder hosts with real cloud endpoints and ensure SSH access works from the host running this script.





























