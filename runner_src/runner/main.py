# src/runner/main.py

from __future__ import annotations

import os
import uuid


def _env_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return int(v.strip())
    except Exception:
        return default


def main() -> int:
    # RUN_ID propagates into ExecutionGate logs
    os.environ.setdefault("RUN_ID", f"run_{uuid.uuid4().hex[:12]}")

    # Optional for safe verification:
    #   MAX_ITERATIONS=1 python -m src.runner.main
    max_iter = _env_int("MAX_ITERATIONS", 0)

    # Add google-cloud-trading-system to path if it exists
    # CRITICAL: Must prioritize google-cloud-trading-system/src over repo-root/src
    import sys
    _gcloud_path = os.path.join(os.getcwd(), 'google-cloud-trading-system')
    _repo_root = os.getcwd()
    
    if os.path.exists(_gcloud_path):
        # Remove repo root temporarily to avoid src/ namespace collision
        if _repo_root in sys.path:
            sys.path.remove(_repo_root)
        # Add google-cloud-trading-system FIRST
        if _gcloud_path not in sys.path:
            sys.path.insert(0, _gcloud_path)
        # Add repo root back AFTER google-cloud-trading-system
        if _repo_root not in sys.path:
            sys.path.insert(1, _repo_root)

    # Import late to avoid side effects at import time
    import working_trading_system  # repo-root module

    if hasattr(working_trading_system, "run_forever"):
        working_trading_system.run_forever(max_iterations=max_iter)
        return 0

    # Fallback: if legacy runner doesn't expose run_forever, call a best-effort main/run
    if hasattr(working_trading_system, "main"):
        return int(working_trading_system.main() or 0)

    raise RuntimeError("working_trading_system.py must expose run_forever(max_iterations=...) or main().")


if __name__ == "__main__":
    raise SystemExit(main())
