# FXG Research Environment Audit
**Date:** 2026-03-11  
**Purpose:** Audit current repo for backtesting/tournament/Monte Carlo infrastructure  
**Status:** IN PROGRESS

## AUDIT RESULTS

### Files Found
- **Backtesting entrypoints:** NOT FOUND
- **Tournament entrypoints:** NOT FOUND  
- **Dataset cache builders:** NOT FOUND
- **Monte Carlo runners:** NOT FOUND
- **Research directory:** NOT FOUND

### Entrypoints Found
- **Production trading:** `runner_src/runner/main.py` (canonical entrypoint)
- **Market data:** `src/control_plane/market_data_provider.py` (get_candles function)
- **Strategies:** `src/strategies/*.py` (multiple strategy implementations)

### Path Resolution Truth
- **REPO_ROOT:** Resolved via `Path(__file__).resolve().parents[2]` in `runner_src/runner/main.py`
- **ARTIFACTS:** No centralized ARTIFACTS path resolution found
- **Runtime paths:** Uses `os.getenv("RUNTIME_PATH", "runtime")` in some places

### Environment Dependency Truth
- **OANDA_API_KEY:** Required in `src/core/settings.py` (load_settings function)
- **OANDA_ACCOUNT_ID:** Required in `src/core/settings.py`
- **OANDA_ENV:** Required in `src/core/settings.py` (defaults to "practice")
- **Cached mode check:** NOT FOUND - no `--use-cached-candles` flag exists

### Monte Carlo Status
- **Existing implementation:** NOT FOUND
- **Resampling tools:** NOT FOUND
- **Need to create:** YES

### Market Data Capabilities
- **Live candle fetching:** ✅ `get_candles()` in `src/control_plane/market_data_provider.py`
- **Historical data support:** ✅ Supports count parameter (up to 500 candles)
- **Cached candle support:** ❌ NOT IMPLEMENTED

## CONCLUSION

**Status:** Research infrastructure does not exist. Must be created.

**Action Required:**
1. Create `src/research/` directory structure
2. Implement dataset cache builder
3. Implement tournament runner
4. Implement backtest core with cached candle support
5. Implement Monte Carlo runner
6. Create local layout and sync scripts
7. Patch env dependency checks for cached mode
