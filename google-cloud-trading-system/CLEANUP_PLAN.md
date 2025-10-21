# CLEANUP PLAN - REMOVING CONFUSION

## FILES TO DELETE (Duplicates/Confusion):

### Duplicate Account Managers:
- `src/core/account_manager.py` - Old hardcoded version (DELETE)
- Keep ONLY: `src/core/dynamic_account_manager.py` (YAML loader)

### Backup Directories (Causing confusion):
- `clean_deploy/` - Old backup (DELETE)
- `cloud_run_deploy/` - Old backup (DELETE)
- `minimal_deploy/` - Old backup (DELETE)
- `analytics/` - Separate analytics system (KEEP if needed, or DELETE)

### Old Strategy Files:
- `src/strategies/*_optimized.py` files (if not in use)
- Old group strategy files (if superseded)

---

## FINAL CLEAN ARCHITECTURE:

```
google-cloud-trading-system/
├── accounts.yaml ← SINGLE SOURCE OF TRUTH
├── main.py
├── requirements.txt
├── app.yaml
├── .gcloudignore
│
├── src/
│   ├── core/
│   │   ├── dynamic_account_manager.py ← Loads accounts from YAML
│   │   ├── candle_based_scanner.py ← Runs strategies
│   │   ├── oanda_client.py ← OANDA API
│   │   ├── config_loader.py ← YAML parser
│   │   └── [other core files]
│   │
│   ├── strategies/ ← ALL INDEPENDENT
│   │   ├── gold_scalping.py ← Gold strategy
│   │   ├── gbp_usd_optimized.py ← GBP Ranks 1,2,3
│   │   ├── ultra_strict_forex.py ← EUR/GBP strict
│   │   ├── momentum_trading.py ← USD/JPY momentum
│   │   └── [keep only active strategies]
│   │
│   └── dashboard/
│       ├── advanced_dashboard.py
│       └── [dashboard files]
│
└── verification/
    ├── verify_scanner_config.py
    ├── pre_deployment_checklist.py
    └── post_deployment_verify.py
```

---

## TO CHANGE THINGS (MODULAR):

**Change Strategy:**
1. Edit: `src/strategies/your_strategy.py`
2. Deploy
3. Only that strategy affected

**Change Account Config:**
1. Edit: `accounts.yaml`
2. Deploy
3. Only that account affected

**No code changes needed for:**
- Adding/removing accounts
- Changing risk settings
- Enabling/disabling accounts
- Switching strategies

---

## CLEANUP ACTIONS:

1. Delete duplicate account managers
2. Delete old backup directories
3. Keep only active strategy files
4. Document what each file does
5. Create SINGLE_FILE_GUIDE.md

Result: Crystal clear system, no confusion


