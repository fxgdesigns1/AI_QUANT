#!/usr/bin/env python3
"""Run Windows Sidecar Bridge. Execute from repo root: python bridges/windows_sidecar/run.py"""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

# Load sidecar .env first - use absolute path so it works regardless of cwd
sidecar_dir = Path(__file__).resolve().parent
env_path = sidecar_dir / ".env"
from dotenv import load_dotenv
load_dotenv(env_path, override=True)

# Read bind config directly - do not rely on config module import order
BIND_HOST = os.getenv("BIND_HOST", "127.0.0.1")
BIND_PORT = int(os.getenv("BIND_PORT", os.getenv("SIDECAR_PORT", "8877")))

# Import app after env is loaded
from bridges.windows_sidecar.service.main import app

if __name__ == "__main__":
    import uvicorn
    print(f"Sidecar binding to {BIND_HOST}:{BIND_PORT}", file=sys.stderr)
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT)
