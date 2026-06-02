# Changelog

## [2026-01-19] - Trade Selection Observability & Config Fixes

### Added
- **API Endpoint**: `GET /api/trade_selection/preview` to inspect the Top-N candidate pool.
  - Supports `limit` query parameter to adjust view depth (e.g., top 1, 3, 10).
  - Returns `TruthEnvelope` with real-time pool data from `status.json`.

### Fixed
- **Configuration Validation**: Removed deprecated `buffer_window_minutes` from `runtime/config.yaml` to fix Pydantic validation errors.
- **Strategy Keys**: Corrected strategy keys in `runtime/config.yaml` (`gold_scalping` -> `gold`, `range_trading` -> `range`) to match registry.
- **System Startup**: Verified clean startup of API and Runner in `TOP_N_DAILY` mode with 5 active accounts.

### Verified
- **Signal Filtering**: Confirmed low-confidence signals (<0.65) are rejected.
- **Pool Population**: Confirmed high-quality signals (e.g., Momentum V2 on XAU_USD) are added to the pool.
- **Execution Logic**: Confirmed delayed execution (waiting for cutoff or exceptional score).

## [2026-01-19] - Quality Over Speed & Execution Fixes

### Fixed
- **Execution Constants**: Restored missing `MIN_TP_DISTANCE_PCT_FX` and `MIN_TP_DISTANCE_PCT_METALS` constants by creating a single source of truth in `src/core/constants.py`. Fixed `NameError` in `working_trading_system.py` during execution.
- **Trade Selection**: Fixed configuration loading issue where `QUALITY_OVER_SPEED` mode was not being applied.

### Added
- **Top-N Daily Selection**: Replaced time-based signal buffering with `TOP_N_DAILY` selection logic.
    - Maintains a rolling daily pool of top candidates.
    - Executes at session cutoff (`NY_CLOSE`) or immediately for exceptional signals (`>0.85` confidence).
    - Allows late-session high-quality signals to displace earlier weaker ones.
- **Quality Over Speed**: Enforced `QUALITY_OVER_SPEED` mode in `runtime/config.yaml` with:
    - Daily trade limit: 3
    - Buffer window: 90 minutes
    - Min confidence: 0.65
    - Early session penalty: 60 minutes
- **Constants Module**: Added `src/core/constants.py` for centralized management of execution safety thresholds.

### Verified
- Validated `runtime/config.yaml` loading.
- Verified signal buffering, displacement, and exceptional execution logic.
- Verified `WorkingTradingSystem` initialization without constant-related errors.
