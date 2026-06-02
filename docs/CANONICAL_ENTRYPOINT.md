# Canonical Entrypoint

## The One Truth

**ONLY supported entrypoint for production trading system:**

```bash
python -m runner_src.runner.main
```

## Why This Matters

The canonical entrypoint ensures:
- ✅ Proper safety gates are initialized
- ✅ Environment variables are loaded correctly
- ✅ Execution controls are enforced
- ✅ Logging is configured properly
- ✅ Path resolution works correctly

## Deprecated Entrypoints

### `src/runner/main.py` (DEPRECATED)

**Status:** Deprecated - should only print guidance

If you attempt to use `python -m src.runner.main`, it should:
1. Print a clear error message
2. Direct you to use `python -m runner_src.runner.main`
3. Exit with non-zero code

### Direct Script Execution (BLOCKED)

**Status:** Blocked - all direct script execution is blocked

Scripts like `working_trading_system.py` have guards that prevent direct execution:

```python
if __name__ == "__main__":
    print("❌ BLOCKED: Direct execution bypasses canonical entrypoint")
    print("   Use: python -m runner_src.runner.main")
    sys.exit(1)
```

## Other Scripts

All other top-level scripts (`.py` files in repo root) are:
- **Tools** - One-off utilities, diagnostics, experiments
- **NOT for production** - Do not use for live trading
- **May bypass safety gates** - Use at your own risk

Examples:
- `check_positions_and_opportunities.py` - Diagnostic tool
- `test_*.py` - Test scripts
- `execute_*.py` - Experimental execution scripts
- `*.sh` - Shell scripts for specific tasks

## Verification

To verify you're using the canonical entrypoint:

```bash
# Should work
python -m runner_src.runner.main

# Should fail with clear error
python -m src.runner.main

# Should fail with clear error
python working_trading_system.py
```

## Environment Variables

The canonical entrypoint loads environment files in this order:
1. `.env`
2. `.env.local`
3. `google-cloud-trading-system/oanda_config.env`
4. `google-cloud-trading-system/.env`

First value wins (override=False).

## Namespace Package Setup

The system uses PEP 420 namespace packages to support two `src` directories:
- `repo_root/src/control_plane/` - Control plane modules (API, config store, status snapshot)
- `google-cloud-trading-system/src/core/` - Core trading modules (scanner, strategies, execution)

Both parent directories are added to `sys.path` at module load time, enabling:
- `src.core.*` imports resolve from `google-cloud-trading-system/src/core/`
- `src.control_plane.*` imports resolve from `repo_root/src/control_plane/`

**Important:** Top-level `src/__init__.py` files must NOT exist (they break namespace packaging).

To verify namespace package resolution:
```bash
python -m runner_src.runner.main --debug-imports
```

## Safety Gates

The canonical entrypoint ensures:
- Paper mode by default
- Dual-confirm required for live trading
- Kill switch support
- Proper execution gate initialization

## Questions?

If you're unsure which entrypoint to use, **always use**:
```bash
python -m runner_src.runner.main
```
