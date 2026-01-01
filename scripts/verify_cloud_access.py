#!/usr/bin/env python3
import json
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

CONFIG_PATH_DEFAULT = "config/verify_cloud_access.yaml"

def load_config() -> dict:
    """
    Load a lightweight cloud access verification config.
    Falls back to a minimal default if PyYAML isn't available or config missing.
    """
    import os
    default = {
        "endpoints": [
            {"name": "GCP", "type": "gcp"},
            {"name": "Internal_API", "host": "localhost", "port": 8000}
        ],
        "http_test_url": None
    }
    config_path = Path(os.environ.get("VERIFY_CLOUD_CONFIG", CONFIG_PATH_DEFAULT))
    if yaml is None or not config_path.exists():
        return default
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        endpoints = cfg.get("endpoints")
        if isinstance(endpoints, list) and endpoints:
            default["endpoints"] = endpoints
        if isinstance(cfg.get("http_test_url"), str) and cfg["http_test_url"]:
            default["http_test_url"] = cfg["http_test_url"]
    except Exception:
        pass
    return default

def test_tcp(host: str, port: int, timeout: int = 4):
    try:
        start = time.time()
        with socket.create_connection((host, int(port)), timeout=timeout):
            latency = int((time.time() - start) * 1000)
            return True, latency
    except Exception:
        return False, None

def test_gcp_access() -> dict:
    result = {"available": False, "accounts": [], "error": None}
    try:
        proc = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        if proc.returncode == 0:
            data = None
            try:
                data = json.loads(proc.stdout)
            except Exception:
                data = None
            if isinstance(data, list) or isinstance(data, dict):
                result["available"] = True
                # Normalize to a list of accounts if possible
                if isinstance(data, list):
                    result["accounts"] = [str(item.get("account")) for item in data if isinstance(item, dict) and item.get("account")]
                elif isinstance(data, dict) and "accounts" in data:
                    result["accounts"] = data.get("accounts")
        else:
            result["error"] = proc.stderr.strip() or "gcloud not configured"
    except FileNotFoundError:
        result["error"] = "gcloud not installed"
    except Exception as exc:
        result["error"] = str(exc)
    return result

def verify_internal_endpoint(host: str, port: int, timeout: int = 4) -> dict:
    reachable, latency = test_tcp(host, port, timeout)
    return {
        "host": host,
        "port": port,
        "reachable": reachable,
        "latency_ms": latency
    }

def main():
    import os
    config = load_config()
    report = {"timestamp": datetime.utcnow().isoformat() + "Z", "endpoints": {}}

    # GCP health
    gcp_status = test_gcp_access()
    report["endpoints"]["GCP"] = {
        "accessible": gcp_status.get("available", False),
        "accounts": gcp_status.get("accounts", []),
        "error": gcp_status.get("error")
    }

    # Internal API health
    for ep in config.get("endpoints", []):
        if ep.get("name") == "GCP":
            continue
        host = ep.get("host", "")
        port = ep.get("port", 80)
        if host:
            report["endpoints"][ep.get("name", "internal")] = verify_internal_endpoint(host, port)

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()


