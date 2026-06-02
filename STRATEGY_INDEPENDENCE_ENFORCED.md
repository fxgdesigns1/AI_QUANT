# Strategy Independence Enforced

## Verification Report

### 1. Registry Verification
- `gold` strategy restricted to `['XAU_USD']`.
- `eur_usd_5m_safe` strategy restricted to `['EUR_USD']`.
- `momentum` strategy restricted to majors.

### 2. Runner Strictness
- Legacy fallback to "momentum" REMOVED from `working_trading_system.py`.
- If a strategy assignment refers to an unknown strategy key, it is SKIPPED (fail closed).
- No global default behavior for unassigned accounts (accounts must be assigned to run).

### 3. Instrument Isolation
- `scan_and_execute` retrieves instruments from Registry.
- Market data is FILTERED to only include those instruments before passing to strategy.
- Verified via test: Account A (Gold) does NOT receive EUR_USD data; Account B (EUR) does NOT receive XAU_USD data.

### 4. Deduplication Logic
- Updated signal fingerprinting to use the `strategy_key` from the signal, ensuring independent deduplication per strategy/account.

## Status
✅ STRICT MODE ENFORCED.
Tests passed on 2026-01-15.
