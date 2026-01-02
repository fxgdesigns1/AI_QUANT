#!/usr/bin/env python3
"""
DEPRECATED: Legacy runner shim

The canonical entrypoint is now: python -m runner_src.runner.main

This file is a strict deprecation notice and does NOT forward automatically
to avoid import path conflicts.
"""

import sys


def main() -> int:
    print("", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("⚠️  DEPRECATED RUNNER", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("", file=sys.stderr)
    print("This runner (python -m src.runner.main) is deprecated.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Please use the canonical runner:", file=sys.stderr)
    print("", file=sys.stderr)
    print("    python -m runner_src.runner.main", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or with environment variables:", file=sys.stderr)
    print("", file=sys.stderr)
    print("    MAX_ITERATIONS=1 TRADING_MODE=paper python -m runner_src.runner.main", file=sys.stderr)
    print("", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
