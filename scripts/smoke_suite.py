#!/usr/bin/env python3
"""
Lightweight smoke-test suite for cloud deployment.
Runs non-destructive checks: OANDA data fetch, accounts.yaml sanity, news feed, ai_trading.service health,
backup engine status, and health endpoint responsiveness.
"""
import json, os, subprocess, time, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
PERF_SCRIPT = ROOT / "get_strategy_performance_since.py"
HEALTH_ENDPOINT = "http://localhost:5000/api/health"

def run(cmd, shell=False, timeout=15):
    res = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def smoke_oanda():
    print("SMOKE: OANDA data fetch for 24h (non-destructive).\n")
    code, out, err = run([sys.executable, str(PERF_SCRIPT), "--smoke"])
    return {"code": code, "stdout": out, "stderr": err}

def find_accounts_yaml_paths():
    """Return a prioritized list of plausible accounts.yaml locations on the cloud."""
    candidates = [
        "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml",
        "/opt/quant_system_clean/AI_QUANT_credentials/accounts.yaml",
        "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/AI_QUANT_credentials/accounts.yaml",
        str(Path(__file__).resolve().parents[2] / "google-cloud-trading-system" / "AI_QUANT_credentials" / "accounts.yaml"),
    ]
    # Allow override via env var
    env_path = os.environ.get("ACCOUNTS_YAML_PATH")
    if env_path:
        candidates.insert(0, env_path)
    return candidates

def locate_accounts_yaml():
    for path in find_accounts_yaml_paths():
        try:
            if Path(path).exists():
                return path
        except Exception:
            continue
    return None

def smoke_accounts():
    print("SMOKE: Load accounts.yaml sanity.\n")
    try:
        import yaml
        accounts_yaml_path = locate_accounts_yaml()
        if not accounts_yaml_path:
            return {"status":"skipped","reason":"accounts.yaml not found in known cloud paths"}
        with open(accounts_yaml_path,"r") as f:
            data = yaml.safe_load(f) or {}
        accounts = data.get("accounts", {})
        active = [name for name, cfg in accounts.items() if cfg.get("active", True)]
        return {"status":"ok","path": accounts_yaml_path, "count": len(active), "active": active}
    except Exception as e:
        return {"status":"fail","error": str(e)}

def smoke_news():
    url = os.getenv("NEWS_API_URL")
    if not url:
        return {"status":"skipped","reason":"NEWS_API_URL not configured"}
    try:
        r = requests.get(url, timeout=5)
        return {"status":"ok","code": getattr(r,"status_code", None)}
    except Exception as e:
        return {"status":"fail","error": str(e)}

def smoke_health():
    print("SMOKE: Health endpoint (health_api.py).\n")
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=5)
        if r.status_code == 200:
            return {"status":"ok","body": r.json()}
        return {"status":"fail","code": r.status_code}
    except Exception as e:
        return {"status":"fail","error": str(e)}

def smoke_service():
    print("SMOKE: ai_trading.service health (VM).\n")
    return {"status":"unknown","note":"Requires VM environment (not available in this sandbox)"}

def run_all():
    report = {}
    report["oanda_smoke"] = smoke_oanda()
    report["accounts_smoke"] = smoke_accounts()
    report["news_smoke"] = smoke_news()
    report["health_smoke"] = smoke_health()
    report["service_smoke"] = smoke_service()
    # Backup engine health (on VM)
    try:
        res = subprocess.run(["systemctl","is-active","automated_trading.service"], capture_output=True, text=True, timeout=10)
        report["backup_engine"] = {"status": res.stdout.strip()}
    except Exception as e:
        report["backup_engine"] = {"status":"unknown","error":str(e)}
    return report

def main():
    report = run_all()
    print("\nSMOKE REPORT SUMMARY:")
    print(json.dumps(report, indent=2))
    with open("/tmp/smoke_report.json","w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()


