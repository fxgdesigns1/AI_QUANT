#!/usr/bin/env python3
"""
Pre-deployment validator
- Ensures accounts.yaml exists and has at least one active account
- Surfaces env flags that can silently block execution (LIVE_TRADING, DRY_RUN, ACCOUNT_DISABLED)
- Confirms OANDA API key presence via app.yaml env_variables
Exit non-zero on failure so CI/deploy scripts stop early.
"""
import sys
import os
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("❌ PyYAML missing. Install with: pip install pyyaml")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
GCLOUD_DIR = REPO_ROOT / 'google-cloud-trading-system'
ACCOUNTS_YAML = GCLOUD_DIR / 'accounts.yaml'
APP_YAML = GCLOUD_DIR / 'app.yaml'

errors = []
warnings = []

# 1) accounts.yaml must exist and have at least one active account
if not ACCOUNTS_YAML.exists():
    errors.append(f"Missing {ACCOUNTS_YAML}")
else:
    try:
        data = yaml.safe_load(ACCOUNTS_YAML.read_text()) or {}
        accounts = data.get('accounts') or []
        active = [a for a in accounts if a and a.get('active') is True]
        if not accounts:
            errors.append(f"{ACCOUNTS_YAML} has no 'accounts' entries")
        elif not active:
            errors.append(f"{ACCOUNTS_YAML} has no active: true accounts")
        else:
            print(f"✓ accounts.yaml OK — {len(accounts)} accounts, {len(active)} active")
    except Exception as e:
        errors.append(f"Failed parsing {ACCOUNTS_YAML}: {e}")

# 2) app.yaml should include OANDA_API_KEY and OANDA_ENVIRONMENT=practice
if not APP_YAML.exists():
    warnings.append(f"Missing {APP_YAML} — will rely on environment/secret manager")
else:
    try:
        app_cfg = yaml.safe_load(APP_YAML.read_text()) or {}
        env_vars = app_cfg.get('env_variables') or {}
        api_key = env_vars.get('OANDA_API_KEY')
        env_name = (env_vars.get('OANDA_ENV') or env_vars.get('OANDA_ENVIRONMENT') or 'practice').lower()
        if api_key:
            print("✓ OANDA_API_KEY present in app.yaml")
        else:
            warnings.append("OANDA_API_KEY not set in app.yaml (ok if provided via secrets)")
        if env_name != 'practice':
            warnings.append(f"OANDA_ENV is '{env_name}' (must be 'practice' for execution path)")
    except Exception as e:
        warnings.append(f"Failed parsing {APP_YAML}: {e}")

# 3) Warn about env flags that block execution
live_trading = (os.getenv('LIVE_TRADING') or '').lower()
dry_run = (os.getenv('DRY_RUN') or '').lower()
account_disabled = (os.getenv('ACCOUNT_DISABLED') or '').lower()
if live_trading == 'true':
    warnings.append("LIVE_TRADING=true will be blocked by OrderManager — unset it")
if dry_run == 'true':
    warnings.append("DRY_RUN=true blocks execution — unset it")
if account_disabled == 'true':
    warnings.append("ACCOUNT_DISABLED=true blocks all orders — unset it")

# Output and exit code
if warnings:
    for w in warnings:
        print(f"⚠ {w}")
if errors:
    for e in errors:
        print(f"❌ {e}")
    sys.exit(2)
print("✅ Predeploy validation passed")
