# 📅 WEEKLY TRADING SYSTEM PREPARATION CHECKLIST

**Purpose:** Comprehensive pre-week system verification and optimization  
**Recommended Time:** Sunday evening or Monday morning before markets open

---

## 🔍 PHASE 1: SYSTEM HEALTH VERIFICATION

### 1.1 Cloud Deployment Status
```bash
# Check if cloud instance is running
curl https://ai-quant-trading.uc.r.appspot.com/api/health

# Check cloud logs for errors
gcloud app logs tail --limit=50 --service=default

# Verify deployment version
gcloud app versions list --service=default
```

**✅ Expected:** Health endpoint returns 200, no critical errors in logs

---

### 1.2 Local System Status
```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system
python3 verify_all_systems.py
```

**✅ Expected:** All systems verified, all accounts connected

---

### 1.3 Account Connectivity
```bash
# Check all accounts
python3 check_current_market_status.py

# Verify positions
python3 check_positions_and_opportunities.py
```

**✅ Expected:** All 10 accounts connected, balances visible, no connection errors

---

## 📊 PHASE 2: DATA & MARKET READINESS

### 2.1 Live Data Feed Verification
- [ ] Verify OANDA API connection is active
- [ ] Check that price data is streaming (not stale)
- [ ] Confirm all 54 instruments are updating
- [ ] Verify market hours alignment (check if markets are open)

### 2.2 Market Schedule Check
**Current Week Important Times:**
- [ ] **Monday:** Market open verification (London 8am, NY 1pm London time)
- [ ] **Wednesday:** CPI release time (typically 13:30 London) - Consider position management
- [ ] **Thursday:** GDP/economic releases - Review schedule
- [ ] **Friday:** End-of-week positions review

**Prime Trading Hours (London time):**
- **1pm-5pm:** London/NY overlap (highest liquidity)
- **8am-5pm:** London session (good activity)
- **10pm-8am:** Asian session (avoid/low activity)

---

## 🤖 PHASE 3: STRATEGY & SCANNER STATUS

### 3.1 Scanner Status
```bash
# Check scanner is running
curl https://ai-quant-trading.uc.r.appspot.com/api/status | grep scanner

# Or check logs
gcloud app logs tail --limit=20 | grep -i scan
```

**✅ Expected:** Scanner running every 5 minutes, recent scan timestamps

---

### 3.2 Strategy Configuration Verification
- [ ] All 10 strategies loaded correctly
- [ ] Risk parameters verified (check config files)
- [ ] Position limits confirmed
- [ ] Stop-loss/take-profit settings reviewed
- [ ] Strategy instruments match intended pairs

---

### 3.3 Signal Generation Test
```bash
# Check recent opportunities
python3 google-cloud-trading-system/check_current_opportunities.py

# Verify signal quality
python3 google-cloud-trading-system/verify_quality_config.py
```

---

## 📱 PHASE 4: MONITORING & ALERTS

### 4.1 Telegram Integration
- [ ] Test Telegram bot is responding
- [ ] Verify chat ID is correct
- [ ] Test alert delivery
- [ ] Check scheduled reports are configured

### 4.2 Dashboard Access
- [ ] **Main Dashboard:** https://ai-quant-trading.uc.r.appspot.com
- [ ] **Analytics:** https://analytics-dot-ai-quant-trading.uc.r.appspot.com
- [ ] **Health Check:** https://ai-quant-trading.uc.r.appspot.com/api/health
- [ ] **Status API:** https://ai-quant-trading.uc.r.appspot.com/api/status

**✅ Expected:** All dashboards load within 2-3 seconds, data displays correctly

---

## 🔧 PHASE 5: CONFIGURATION REVIEW

### 5.1 Account Configuration
- [ ] Review `google-cloud-trading-system/config/accounts.yaml`
- [ ] Verify all account IDs and API keys are valid
- [ ] Confirm all accounts are in "practice" mode (demo)
- [ ] Check account balances are expected

### 5.2 Strategy Configuration
- [ ] Review `google-cloud-trading-system/config/strategies.yaml`
- [ ] Verify risk per trade settings (typically 0.5-2%)
- [ ] Check max positions per strategy
- [ ] Review instrument lists for each strategy
- [ ] Confirm quality filters are appropriate

### 5.3 Risk Management Settings
- [ ] Portfolio risk limits verified
- [ ] Max daily trades per account checked
- [ ] Stop-loss distances confirmed
- [ ] Take-profit levels reviewed
- [ ] Position sizing rules validated

---

## 📝 PHASE 6: LOG REVIEW & ERROR CHECK

### 6.1 Recent Error Scan
```bash
# Check for errors in last 24 hours
gcloud app logs read --limit=200 --service=default | grep -i error

# Check for warnings
gcloud app logs read --limit=200 --service=default | grep -i warn
```

**✅ Expected:** No critical errors, warnings are acceptable if explained

---

### 6.2 Trade Execution Logs
```bash
# Check recent trades
gcloud app logs read --limit=100 | grep -i "trade\|signal\|execut"
```

**Review:**
- [ ] Trades executing as expected
- [ ] Stop-losses being set correctly
- [ ] Risk management working
- [ ] No execution failures

---

## 💾 PHASE 7: BACKUP & SAFETY

### 7.1 Configuration Backup
```bash
# Backup current configs
cd /Users/mac/quant_system_clean/google-cloud-trading-system/config
cp accounts.yaml accounts.yaml.backup.$(date +%Y%m%d)
cp strategies.yaml strategies.yaml.backup.$(date +%Y%m%d)
```

### 7.2 System State Snapshot
- [ ] Document current positions
- [ ] Record account balances
- [ ] Save current strategy performance metrics
- [ ] Note any manual interventions needed

---

## 🎯 PHASE 8: WEEKLY GOALS & EXPECTATIONS

### 8.1 Performance Targets
- [ ] Review previous week's performance
- [ ] Set realistic weekly targets
- [ ] Identify which strategies performed best
- [ ] Plan any strategy adjustments

### 8.2 Market Conditions Assessment
- [ ] Review economic calendar for the week
- [ ] Identify high-impact news events
- [ ] Plan position management around events
- [ ] Consider volatility expectations

---

## ⚡ QUICK VERIFICATION SCRIPT

Run this comprehensive check:

```bash
#!/bin/bash
echo "🚀 WEEKLY SYSTEM CHECK"
echo "======================"

# Health check
echo "1. Cloud Health..."
curl -s https://ai-quant-trading.uc.r.appspot.com/api/health | head -5

# Status check
echo -e "\n2. System Status..."
curl -s https://ai-quant-trading.uc.r.appspot.com/api/status | python3 -m json.tool | head -20

# Account check
echo -e "\n3. Running local verification..."
cd /Users/mac/quant_system_clean/google-cloud-trading-system
python3 verify_all_systems.py

echo -e "\n✅ Weekly check complete!"
```

---

## ✅ FINAL PRE-WEEK VERIFICATION

Before markets open Monday:

- [ ] ✅ Cloud deployment is live and responsive
- [ ] ✅ All 10 accounts connected and accessible
- [ ] ✅ Scanner running automatically every 5 minutes
- [ ] ✅ Dashboard loads and shows current data
- [ ] ✅ Telegram alerts configured and tested
- [ ] ✅ No critical errors in logs
- [ ] ✅ Risk management parameters reviewed
- [ ] ✅ Configurations backed up
- [ ] ✅ Economic calendar reviewed
- [ ] ✅ Market schedule confirmed

---

## 🔔 WEEKLY REMINDERS

### Monday Morning
- Markets reopen - system should auto-detect
- First hour: Monitor scanner activity
- Verify signals are generating if conditions met

### Mid-Week (Wed-Thu)
- High-impact news events
- Consider reducing positions before major releases
- Monitor volatility spikes

### Friday Afternoon
- End-of-week position review
- Assess weekly performance
- Plan next week's adjustments

---

## 📊 EXPECTED SYSTEM STATE

**Healthy System Indicators:**
- ✅ Scanner: Running every 5 minutes
- ✅ Response Time: <3 seconds for dashboard
- ✅ Error Rate: <1% of requests
- ✅ Account Connectivity: 100% (10/10 accounts)
- ✅ Data Freshness: <60 seconds behind live prices
- ✅ Signal Quality: Only high-probability setups (75%+ WR strategies)

---

## 🆘 TROUBLESHOOTING QUICK REFERENCE

### Cloud 503 Error
```bash
# Wake up cloud instance
curl https://ai-quant-trading.uc.r.appspot.com/api/health
# Wait 30-60 seconds for cold start
```

### Account Connection Issues
```bash
# Verify API keys
python3 google-cloud-trading-system/pre_deploy_check.py
```

### Scanner Not Running
```bash
# Check logs
gcloud app logs tail | grep scanner
# Redeploy if needed
cd google-cloud-trading-system
gcloud app deploy app.yaml --quiet
```

---

## 📞 SUPPORT RESOURCES

- **Dashboard:** https://ai-quant-trading.uc.r.appspot.com
- **Health API:** https://ai-quant-trading.uc.r.appspot.com/api/health
- **Status API:** https://ai-quant-trading.uc.r.appspot.com/api/status
- **Logs:** `gcloud app logs tail --service=default`

---

**Last Updated:** Weekly Preparation Checklist v1.0  
**Recommended Review:** Every Sunday evening / Monday morning

---

**🎯 Goal:** Start each week with complete confidence that your system is operational, optimized, and ready to trade.

