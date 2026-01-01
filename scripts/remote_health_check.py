#!/usr/bin/env python3
import json
import subprocess
import time
import os
from datetime import datetime
from typing import List, Dict, Any

try:
    import yaml
except Exception:
    yaml = None

CONFIG_PATH_DEFAULT = "config/remote_health_config.yaml"

def load_config() -> Dict[str, Any]:
    """
    Load remote health check configuration.
    If PyYAML is unavailable or the config file is missing, use a minimal default.
    """
    default_config: Dict[str, Any] = {
        "endpoints": [
            {
                "name": "remote_host_1",
                "host": "remote.example.com",
                "user": "ubuntu",
                "port": 22,
                "key_path": "~/.ssh/id_rsa",
            }
        ]
    }
    config_path = os.environ.get("CLOUD_REMOTE_HEALTH_CONFIG", CONFIG_PATH_DEFAULT)

    if yaml is None or not os.path.exists(config_path):
        return default_config

    try:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
        endpoints = user_config.get("endpoints")
        if isinstance(endpoints, list) and endpoints:
            default_config["endpoints"] = endpoints
    except Exception:
        # If anything goes wrong, fall back to defaults
        pass
    return default_config

def expand_user_path(path: str) -> str:
    return os.path.expanduser(path) if path else path

def run_remote_health(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    """
    SSH into the remote host and run:
      systemctl status ai_trading.service --no-pager
    Return a dict with health info.
    """
    host = endpoint.get("host")
    user = endpoint.get("user")
    port = endpoint.get("port", 22)
    key_path = endpoint.get("key_path", "")

    ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-p", str(port)]
    if key_path:
        ssh_cmd.extend(["-i", expand_user_path(key_path)])
    ssh_target = f"{user}@{host}"
    remote_command = "systemctl status ai_trading.service --no-pager"
    full_cmd = ssh_cmd + [ssh_target, remote_command]

    try:
        result = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        # Basic health inference: look for "Active:" line
        active_line = next((line for line in stdout.splitlines() if line.strip().startswith("Active: ")), "")
        is_running = "running" in active_line.lower()
        health_status = "running" if is_running else "not_running"
        details = {
            "host": host,
            "port": port,
            "health_status": health_status,
            "active_line": active_line.strip(),
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        details = {
            "host": host,
            "port": port,
            "health_status": "timeout",
            "stdout": "",
            "stderr": "command timed out",
        }
    except Exception as exc:
        details = {
            "host": host,
            "port": port,
            "health_status": "error",
            "stdout": "",
            "stderr": str(exc),
        }
    return details

def main():
    config = load_config()
    report: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": {}
    }

    for ep in config.get("endpoints", []):
        name = ep.get("name", "unnamed")
        report["endpoints"][name] = run_remote_health(ep)

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()


