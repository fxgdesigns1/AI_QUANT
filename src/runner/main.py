#!/usr/bin/env python3
"""
DEPRECATED: Legacy runner shim

The canonical entrypoint is now: python -m runner_src.runner.main

This file forwards to the new runner for backwards compatibility.
"""

import sys
import os


def main() -> int:
    print("⚠️  DEPRECATED: src.runner.main is deprecated", file=sys.stderr)
    print("   Use: python -m runner_src.runner.main", file=sys.stderr)
    print("   Forwarding to new runner...", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Forward to new runner
    try:
        # Add repo root to path
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        
        # Import and run new runner
        from runner_src.runner import main as new_main
        return new_main.main()
    except Exception as e:
        print(f"❌ Failed to forward to new runner: {e}", file=sys.stderr)
        print("   Please run: python -m runner_src.runner.main", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
