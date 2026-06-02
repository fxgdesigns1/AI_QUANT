#!/usr/bin/env python3
"""
DEPRECATED: This entrypoint is deprecated.

Use the canonical entrypoint instead:
    python -m runner_src.runner.main

This file exists for backwards compatibility but should not be used.
"""

import sys

def main():
    print("=" * 70)
    print("❌ DEPRECATED ENTRYPOINT")
    print("=" * 70)
    print()
    print("This entrypoint (src/runner/main.py) is deprecated.")
    print()
    print("Use the canonical entrypoint instead:")
    print("  python -m runner_src.runner.main")
    print()
    print("The canonical entrypoint ensures:")
    print("  ✅ Proper safety gates")
    print("  ✅ Correct environment loading")
    print("  ✅ Execution controls")
    print("  ✅ Path resolution")
    print()
    print("=" * 70)
    sys.exit(1)

if __name__ == "__main__":
    main()
