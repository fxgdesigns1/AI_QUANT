# runner_src/runner/main.py

from __future__ import annotations

import os
import sys
import uuid
import logging

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return int(v.strip())
    except Exception:
        return default


def _load_env_files() -> None:
    """Load environment files opportunistically (no failure if missing)
    
    Loads in order with override=False (first value wins):
    1. .env
    2. .env.local
    3. google-cloud-trading-system/oanda_config.env
    4. google-cloud-trading-system/.env
    
    Never logs env var values, only filenames loaded.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("WARNING: python-dotenv not installed; .env files will not be loaded")
        return
    
    # Try loading env files in order (override=False means first wins)
    env_candidates = [
        '.env',
        '.env.local',
        'google-cloud-trading-system/oanda_config.env',
        'google-cloud-trading-system/.env',
    ]
    
    loaded_files = []
    for env_file in env_candidates:
        if os.path.exists(env_file):
            load_dotenv(env_file, override=False)
            loaded_files.append(env_file)
    
    if loaded_files:
        print(f"INFO: Loaded environment from: {', '.join(loaded_files)}")
    else:
        print("INFO: No .env files found; using system environment only")


def main() -> int:
    # Set up basic logging early (before imports that might log)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # RUN_ID propagates into ExecutionGate logs
    os.environ.setdefault("RUN_ID", f"run_{uuid.uuid4().hex[:12]}")

    # Load environment files before anything else
    _load_env_files()

    # Optional for safe verification:
    #   MAX_ITERATIONS=1 python -m runner_src.runner.main
    max_iter = _env_int("MAX_ITERATIONS", 0)

    # Add google-cloud-trading-system to path if it exists
    # CRITICAL: Must prioritize google-cloud-trading-system/src over repo-root/src
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
