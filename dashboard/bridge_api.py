#!/usr/bin/env python3
"""
Bridge Dashboard API (FastAPI).
Local-only; never logs secrets. Serves bridge state, accounts, secrets (set only), verification.
"""
import json
import os
import subprocess
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_CACHE_SEC = 2
_state_cache = {}
_state_cache_ts = 0


def _emit_state():
    """Generate bridge state (cached 2s)."""
    global _state_cache, _state_cache_ts
    now = time.time()
    if now - _state_cache_ts < STATE_CACHE_SEC and _state_cache:
        return _state_cache
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from dashboard.bridge_state_emitter import emit_bridge_state
        _state_cache = emit_bridge_state()
        _state_cache_ts = now
        return _state_cache
    except Exception as e:
        return {"error": str(e), "schema": "bridge_state_v1"}


def _load_accounts():
    cfg_path = PROJECT_ROOT / "configs" / "bridge_accounts.json"
    if not cfg_path.exists():
        return {"schema": "bridge_accounts_v1", "accounts": [], "default_account_id": None}
    with open(cfg_path, "r") as f:
        return json.load(f)


def _save_accounts(data):
    cfg_path = PROJECT_ROOT / "configs" / "bridge_accounts.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


app = FastAPI(title="Bridge Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "bridge-dashboard"}


@app.get("/api/bridge/state")
def get_bridge_state():
    """Returns bridge_state.json (generated on demand, cached 2s)."""
    return _emit_state()


@app.get("/api/accounts")
def get_accounts():
    """List accounts (no secrets)."""
    return _load_accounts()


class AccountUpdate(BaseModel):
    account_id: str | None = None
    id: str | None = None
    enabled: bool | None = None
    label: str | None = None
    set_default: bool | None = None


class AccountEnable(BaseModel):
    id: str
    enabled: bool


@app.post("/api/accounts")
def post_accounts(body: AccountUpdate):
    """Enable/disable account or set default."""
    aid = body.account_id or body.id
    if not aid:
        raise HTTPException(status_code=400, detail="account_id or id required")
    data = _load_accounts()
    for acc in data.get("accounts", []):
        if (acc.get("id") or acc.get("account_id")) == aid:
            if body.enabled is not None:
                acc["enabled"] = body.enabled
            if body.label is not None:
                acc["label"] = body.label
            if body.set_default:
                data["default_account_id"] = aid
            _save_accounts(data)
            return {"ok": True, "account_id": aid}
    raise HTTPException(status_code=404, detail="Account not found")


@app.post("/api/accounts/enable")
def post_accounts_enable(body: AccountEnable):
    """Enable or disable an account by id."""
    data = _load_accounts()
    for acc in data.get("accounts", []):
        if (acc.get("id") or acc.get("account_id")) == body.id:
            acc["enabled"] = body.enabled
            _save_accounts(data)
            return {"ok": True, "id": body.id, "enabled": body.enabled}
    raise HTTPException(status_code=404, detail="Account not found")


class MasterFeedUpdate(BaseModel):
    oanda_account_id: str


@app.post("/api/master_feed")
def post_master_feed(body: MasterFeedUpdate):
    """Set OANDA master feed account id."""
    data = _load_accounts()
    if "master_feed" not in data:
        data["master_feed"] = {}
    data["master_feed"]["oanda_account_id"] = body.oanda_account_id
    _save_accounts(data)
    return {"ok": True, "oanda_account_id": body.oanda_account_id}


class SecretSet(BaseModel):
    ref: str
    value: str


@app.post("/api/secrets")
def post_secrets(body: SecretSet):
    """Set secret. NEVER log value."""
    if not body.ref or not body.value:
        raise HTTPException(status_code=400, detail="ref and value required")
    try:
        sys_path = str(PROJECT_ROOT)
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        from scripts.secrets import set_secret
        ref = body.ref if body.ref.startswith("keychain:") else f"keychain:fxg/mt5/{body.ref}"
        ok, msg = set_secret(ref, body.value)
        if ok:
            return {"ok": True}
        raise HTTPException(status_code=500, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bridge/verify")
def post_verify(bridge_account: str = "ftmo_demo_01", timeout: int = 90):
    """Run verify_bridge_end_to_end.py."""
    script = PROJECT_ROOT / "scripts" / "verify_bridge_end_to_end.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail="Verification script not found")
    try:
        result = subprocess.run(
            ["python3", str(script), "--bridge-account", bridge_account, "--timeout", str(timeout)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "output": out,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "output": "Verification timed out"}
    except Exception as e:
        return {"ok": False, "exit_code": -1, "output": str(e)}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8788)


if __name__ == "__main__":
    main()
