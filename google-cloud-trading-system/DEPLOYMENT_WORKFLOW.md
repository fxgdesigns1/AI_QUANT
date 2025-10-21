# 🚀 MANDATORY DEPLOYMENT WORKFLOW

**NEVER deploy without following these steps. EVER.**

This workflow prevents the scanner mismatch disaster that cost $12-19K on Oct 13, 2025.

---

## ⚠️ CRITICAL RULES

1. **NEVER modify `candle_based_scanner.py` manually** - Use the config loader instead
2. **ALWAYS run pre-deployment checklist** - No exceptions
3. **ALWAYS verify after deployment** - Confirm it actually works
4. **NEVER skip traffic routing verification** - Multiple versions = confusion
5. **ALWAYS keep only 1 active version** - Delete old versions after migration

---

## 📋 STEP-BY-STEP DEPLOYMENT PROCESS

### **STEP 1: Modify Strategies (if needed)**

```bash
# Edit strategy files
nano src/strategies/gold_scalping.py
nano src/strategies/gbp_usd_optimized.py
# etc.
```

**DO NOT TOUCH `candle_based_scanner.py` unless adding new strategy support**

---

### **STEP 2: Update accounts.yaml (if needed)**

```bash
# Edit configuration
nano accounts.yaml

# Add/modify accounts or strategies
# The scanner will auto-load from this file
```

**Remember:** `accounts.yaml` is the SINGLE SOURCE OF TRUTH

---

### **STEP 3: RUN PRE-DEPLOYMENT CHECKLIST** ⚠️ MANDATORY

```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system

# Run the checklist
python3 pre_deployment_checklist.py
```

**Expected output:**
```
✅ Scanner Configuration Match - PASSED
✅ Python Syntax Check - PASSED
✅ Strategy Files Exist - PASSED
✅ .gcloudignore File Exists - PASSED
✅ Large Files Check - PASSED
✅ accounts.yaml Validation - PASSED
✅ No Hardcoded Strategy Calls - PASSED

✅ ALL CHECKS PASSED - DEPLOYMENT APPROVED
```

**IF ANY CHECK FAILS:** Fix it before proceeding. NO EXCEPTIONS.

---

### **STEP 4: Deploy to Google Cloud**

```bash
# Deploy with descriptive version name
# Format: YYMMDD-description
gcloud app deploy --version=$(date +%y%m%d)-your-description --quiet

# Example:
# gcloud app deploy --version=251014-gold-optimized --quiet
```

**Wait for deployment to complete** (usually 2-3 minutes)

---

### **STEP 5: Route 100% Traffic to New Version** ⚠️ CRITICAL

```bash
# Get your new version name
VERSION="251014-gold-optimized"  # Replace with your version

# Route 100% traffic
gcloud app services set-traffic default --splits=$VERSION=1 --quiet
```

**Verify traffic routing:**
```bash
gcloud app versions list --service=default --filter="TRAFFIC_SPLIT>0"
```

**Expected output:**
```
SERVICE  VERSION.ID              TRAFFIC_SPLIT  SERVING_STATUS
default  251014-gold-optimized   1.00           SERVING
```

**Only ONE version should have traffic!**

---

### **STEP 6: Verify Deployment** ⚠️ MANDATORY

```bash
# Run post-deployment verification
python3 post_deployment_verify.py 251014-gold-optimized
```

**Expected output:**
```
✅ System is online
✅ All 6 accounts active
✅ Data feed active
✅ ALL CHECKS PASSED - Deployment verified!
```

**IF VERIFICATION FAILS:** Investigate immediately, don't wait!

---

### **STEP 7: Monitor for First Trade**

```bash
# Watch logs for 5-10 minutes
gcloud app logs tail --service=default

# Look for:
# - "Trading scanner initialized"
# - "Active strategies: ..."
# - Trade signals from strategies
```

**If no trades after 15 minutes:** Run diagnostics (see Troubleshooting section)

---

### **STEP 8: Clean Up Old Versions**

After 24 hours of successful operation:

```bash
# List all versions
gcloud app versions list --service=default

# Delete old versions (keep only current and 1 backup)
gcloud app versions delete VERSION_ID_1 VERSION_ID_2 --quiet
```

**Keep:** Current version + 1 recent backup  
**Delete:** Everything else

---

## 🔍 VERIFICATION CHECKLIST

After deployment, manually verify:

- [ ] Only 1 version receiving traffic (100%)
- [ ] All 6 accounts show as active
- [ ] Correct strategies loaded for each account
- [ ] Data feed status = "active"
- [ ] No errors in logs
- [ ] Dashboard accessible
- [ ] First trade signal within 15 minutes

---

## 🚨 TROUBLESHOOTING

### **No Trades After 15 Minutes**

```bash
# 1. Check which strategies are loaded
curl https://ai-quant-trading.uc.r.appspot.com/api/status | jq '.trading_systems'

# 2. Verify scanner configuration
python3 verify_scanner_config.py

# 3. Check logs for errors
gcloud app logs read --service=default --limit=200 | grep ERROR

# 4. Verify correct version is serving
gcloud app versions list --service=default --filter="TRAFFIC_SPLIT>0"
```

### **Multiple Versions Receiving Traffic**

```bash
# Route 100% to correct version immediately
gcloud app services set-traffic default --splits=CORRECT_VERSION=1 --quiet
```

### **Scanner Mismatch Errors**

```bash
# Re-run verification
python3 verify_scanner_config.py

# If errors found, fix candle_based_scanner.py
# Then redeploy following full workflow
```

---

## 📝 DEPLOYMENT LOG TEMPLATE

Keep a log of each deployment:

```
Date: 2025-10-14 15:00 BST
Version: 251014-gold-optimized
Changes: 
  - Optimized gold scalping thresholds
  - Fixed GBP news filter
  
Pre-deployment: ✅ All checks passed
Deployment: ✅ Successful (2m 34s)
Traffic routing: ✅ 100% to new version
Post-verification: ✅ All systems active
First trade: ✅ 15:12 BST (Gold BUY)

Issues: None
Notes: Clean deployment, trades started immediately
```

---

## 🎯 WHY THIS WORKFLOW EXISTS

**Oct 13, 2025 Disaster:**
- Scanner hardcoded to wrong strategies
- Traffic split between 3 versions
- 5+ hours with 0 trades
- $12-19K in missed opportunities

**This workflow prevents:**
- Strategy mismatches
- Traffic confusion
- Silent failures
- Deployment errors
- Configuration drift

---

## ✅ GOLDEN RULES

1. **Pre-deployment checklist is MANDATORY**
2. **Only 1 version gets traffic at a time**
3. **Verify after every deployment**
4. **accounts.yaml is the source of truth**
5. **Never modify scanner manually**
6. **Clean up old versions regularly**
7. **Monitor first 15 minutes after deployment**
8. **Keep deployment logs**

---

**Last updated:** October 13, 2025  
**Created by:** AI Assistant (after learning the hard way)  
**Never skip this workflow. EVER.**


