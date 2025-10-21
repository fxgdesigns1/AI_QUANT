# BACKTESTING SYSTEM UPDATE INSTRUCTIONS

## Date: 2025-10-13 19:11:25

## Updates Applied: 10

### To Apply These Updates:

1. **Backup your current optimization_results.json:**
   ```bash
   cp optimization_results.json optimization_results_BACKUP_20251013_191125.json
   ```

2. **Replace with new version:**
   ```bash
   cp /Users/mac/quant_system_clean/google-cloud-trading-system/backtesting_updates/optimization_results_UPDATED_20251013_191125.json optimization_results.json
   ```

3. **Restart your backtesting system** to load new parameters

4. **Verify results** after 24 hours of live trading

## Changes Made:


### UltraStrictForex - EUR_USD
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 5.6% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### UltraStrictForex - GBP_USD
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 0.0% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### UltraStrictForex - GBP_USD
- **Parameter:** `enabled`
- **Old Value:** `True`
- **New Value:** `False`
- **Reason:** Negative P&L -0.0055 - disable this pair
- **Confidence:** 85.0%
- **Action:** DISABLE_INSTRUMENT


### UltraStrictForex - USD_JPY
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 9.1% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### UltraStrictForex - USD_JPY
- **Parameter:** `enabled`
- **Old Value:** `True`
- **New Value:** `False`
- **Reason:** Negative P&L -0.1420 - disable this pair
- **Confidence:** 85.0%
- **Action:** DISABLE_INSTRUMENT


### UltraStrictForex - AUD_USD
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 0.0% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### UltraStrictForex - USD_CAD
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 0.0% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### UltraStrictForex - NZD_USD
- **Parameter:** `min_signal_strength`
- **Old Value:** `0.35`
- **New Value:** `0.39999999999999997`
- **Reason:** Win rate 0.0% too low - increasing threshold
- **Confidence:** 80.0%
- **Action:** TIGHTEN_ENTRY


### Momentum - NZD_USD
- **Parameter:** `enabled`
- **Old Value:** `True`
- **New Value:** `False`
- **Reason:** Negative P&L -0.0052 - disable this pair
- **Confidence:** 85.0%
- **Action:** DISABLE_INSTRUMENT


### Gold - XAU_USD
- **Parameter:** `enabled`
- **Old Value:** `True`
- **New Value:** `False`
- **Reason:** Negative P&L -16.7372 - disable this pair
- **Confidence:** 85.0%
- **Action:** DISABLE_INSTRUMENT

