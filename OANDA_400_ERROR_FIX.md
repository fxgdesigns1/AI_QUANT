# OANDA 400 Error Fix

## Problem Identified

**Error:** `Failed to get prices: 400`  
**Account:** `101-004-30719775-010` (Trade With Pat ORB Lane)  
**Root Cause:** Invalid instrument name in configuration

---

## The Issue

### Invalid Instrument Name
The account configuration had:
```yaml
trading_pairs: ["GBP_USD", "EUR_USD", "XAU_USD", "US500_USD", "NAS100_USD"]
```

**Problem:** `US500_USD` is **NOT a valid OANDA instrument name**

### OANDA's Response
```json
{"errorMessage":"Invalid Instrument US500_USD"}
```

When the system tried to fetch prices for all instruments together, OANDA rejected the entire request because of the invalid instrument.

---

## The Fix

### Correct Instrument Name
OANDA uses `SPX500_USD` for the S&P 500 index, not `US500_USD`.

**Fixed configuration:**
```yaml
trading_pairs: ["GBP_USD", "EUR_USD", "XAU_USD", "SPX500_USD", "NAS100_USD"]
```

### Verification
```bash
# Test individual instruments
US500_USD: 400 ❌ - {"errorMessage":"Invalid Instrument US500_USD"}
SPX500_USD: 200 ✅ VALID!
NAS100_USD: 200 ✅ VALID!
```

---

## Impact

### Before Fix
- Account `101-004-30719775-010`:
  - ❌ Every price request returned 400 error
  - ❌ Trading cycles failed to get prices
  - ❌ No trades could be executed
  - ❌ Error logged every 60 seconds

### After Fix
- Account `101-004-30719775-010`:
  - ✅ Price requests succeed (200 status)
  - ✅ Trading cycles can get prices
  - ✅ Trades can be executed
  - ✅ No more 400 errors

---

## Files Changed

**File:** `AI_QUANT_credentials/accounts.yaml`  
**Line:** 114  
**Change:** `US500_USD` → `SPX500_USD`

---

## OANDA Instrument Names Reference

### Valid Index Instruments
- ✅ `SPX500_USD` - S&P 500 (US SPX 500)
- ✅ `NAS100_USD` - NASDAQ 100
- ❌ `US500_USD` - **INVALID** (does not exist)
- ❌ `SP500_USD` - **INVALID** (does not exist)

### How to Find Valid Instruments
```python
import requests

API_KEY = "your_key"
BASE_URL = "https://api-fxpractice.oanda.com"
ACCOUNT_ID = "your_account"

headers = {"Authorization": f"Bearer {API_KEY}"}
url = f"{BASE_URL}/v3/accounts/{ACCOUNT_ID}/instruments"
response = requests.get(url, headers=headers)

instruments = response.json().get("instruments", [])
for inst in instruments:
    print(f"{inst['name']} - {inst['displayName']}")
```

---

## Deployment

**Status:** ✅ **FIXED and DEPLOYED**

1. ✅ Fixed `accounts.yaml` locally
2. ✅ Deployed to Google Cloud VM
3. ✅ Service restarted
4. ✅ Verification: No more 400 errors

---

## Prevention

### Best Practices
1. **Always verify instrument names** before adding to config
2. **Test API calls** with new instruments before deploying
3. **Check OANDA documentation** for valid instrument names
4. **Use the `/instruments` endpoint** to list available instruments

### Quick Test Script
```python
# Test instruments before adding to config
instruments = ["GBP_USD", "EUR_USD", "XAU_USD", "SPX500_USD", "NAS100_USD"]
for inst in instruments:
    r = requests.get(f"{BASE_URL}/v3/accounts/{ACCOUNT_ID}/pricing", 
                     params={"instruments": inst}, headers=headers)
    if r.status_code != 200:
        print(f"❌ {inst} is INVALID: {r.text}")
    else:
        print(f"✅ {inst} is valid")
```

---

**Date:** November 16, 2025  
**Status:** ✅ Resolved  
**Impact:** Account 101-004-30719775-010 now working correctly






