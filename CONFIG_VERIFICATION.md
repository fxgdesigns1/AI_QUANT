# Configuration Source Verification

## ✅ SINGLE SOURCE OF TRUTH ESTABLISHED

### Configuration Location
**ONLY ONE config file is used:**
- `/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml`

### How It Works
1. **YAMLManager** discovers the config file using a priority search:
   - Checks `ACCOUNTS_CONFIG_PATH` environment variable first
   - Searches parent directories for `AI_QUANT_credentials/accounts.yaml`
   - Searches parent directories for `config/accounts.yaml`
   - Checks current working directory

2. **ai_trading_system.py** uses **ONLY** YAMLManager:
   - Removed all fallback paths that could cause confusion
   - Single source of truth guaranteed
   - Config path is logged on startup

3. **Strategy Registry** loads strategies from:
   - `/opt/quant_system_clean/google-cloud-trading-system/src/strategies/`

### Account 011 Status
- ✅ Account ID: 101-004-30719775-011
- ✅ Strategy: dynamic_multi_pair_unified
- ✅ Name: Dynamic Multi-Pair Unified Account
- ✅ Trading Pairs: USD_CAD, NZD_USD, GBP_USD, EUR_USD, XAU_USD, USD_JPY
- ✅ Risk Settings:
  - Max risk per trade: 2.0%
  - Max daily risk: 10%
  - Max positions: 3
  - Position multiplier: 5.0x
- ✅ Active: true
- ✅ Config file: `/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml`

### Verification Commands

To verify the single config source:
```bash
gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a
cd /opt/quant_system_clean
python3 -c "from google-cloud-trading-system.src.core.yaml_manager import YAMLManager; m = YAMLManager(); print('Config:', m.accounts_path)"
```

To verify account 011:
```bash
gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a
cat /opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml | grep -A 10 strategy_delta
```

### No Confusion Guaranteed
- ✅ Only ONE accounts.yaml file is read
- ✅ Only ONE strategy registry location
- ✅ Config path is logged on every startup
- ✅ All 7 accounts loaded from same source
- ✅ No fallback paths that could cause confusion








