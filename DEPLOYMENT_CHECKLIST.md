# Deployment Checklist

## Pre-Deployment Verification

### 1. Code Review ✅
- [x] All new code files created and reviewed
- [x] No breaking changes to existing functionality
- [x] Backward compatibility maintained
- [x] Logging and error handling in place

### 2. Testing Checklist

#### Unit Tests
- [ ] ConfigAPIManager endpoints work
- [ ] CredentialsManager methods function
- [ ] StrategyLifecycleManager operations successful
- [ ] YAML manager read/write operations

#### Integration Tests
- [ ] API configuration loads correctly
- [ ] Strategy loading works end-to-end
- [ ] Dashboard navigation renders properly
- [ ] No import errors in dashboard

#### System Tests
- [ ] Trading system continues operating
- [ ] No disruptions to active trades
- [ ] Configuration changes persist
- [ ] Backup system functions

---

## Deployment Steps

### Phase 1: Backup Current State

```bash
# 1. Backup configuration files
cd /Users/mac/quant_system_clean/google-cloud-trading-system
cp accounts.yaml accounts.yaml.backup_$(date +%Y%m%d)
cp app.yaml app.yaml.backup_$(date +%Y%m%d)

# 2. Backup environment files
cp oanda_config.env oanda_config.env.backup
cp news_api_config.env news_api_config.env.backup

# 3. Create Git checkpoint
cd /Users/mac/quant_system_clean
git add -A
git commit -m "Pre-consolidation checkpoint"
```

### Phase 2: Local Deployment

```bash
# 1. Navigate to project root
cd /Users/mac/quant_system_clean

# 2. Start local dashboard
python dashboard/advanced_dashboard.py

# 3. Verify dashboard loads
# Open: http://localhost:8080

# 4. Test API configuration panel
# Navigate to Configuration → API Configuration
# Click Test on each API service

# 5. Verify navigation structure
# Check all 4 groups render correctly
# Test navigation between sections
```

**Expected Results:**
- ✅ Dashboard starts without errors
- ✅ Navigation shows 4 groups
- ✅ API config panel loads
- ✅ No console errors

---

### Phase 3: Google Cloud Deployment

#### 3.1 Prepare Cloud Deployment

```bash
# 1. Ensure Google Cloud SDK installed
gcloud --version

# 2. Login and set project
gcloud auth login
gcloud config set project ai-quant-trading

# 3. Verify credentials
gcloud auth application-default login
```

#### 3.2 Deploy to App Engine

```bash
# 1. Navigate to cloud system
cd /Users/mac/quant_system_clean/google-cloud-trading-system

# 2. Review app.yaml configuration
cat app.yaml | grep -A5 "env_variables"

# 3. Deploy to App Engine
gcloud app deploy --version v1 --no-promote

# 4. Monitor deployment
gcloud app logs tail -s default
```

**Expected Results:**
- ✅ Deployment succeeds without errors
- ✅ Application starts successfully
- ✅ Health checks pass
- ✅ Dashboard accessible at cloud URL

#### 3.3 Promote to Production

```bash
# Wait 5 minutes, verify functionality

# Promote to production
gcloud app versions migrate v1 --service default

# Verify:
curl https://ai-quant-trading.uc.r.appspot.com/api/health
```

---

### Phase 4: Configuration Migration

#### 4.1 Migrate API Keys

**Option A: Via Dashboard**
1. Open cloud dashboard
2. Navigate to Configuration → API Configuration
3. Edit each API key individually
4. Test each connection

**Option B: Via Secret Manager**
```bash
# 1. Update Secret Manager
gcloud secrets versions add oanda-api-key --data-file=oanda_key.txt
gcloud secrets versions add marketaux-api-key --data-file=marketaux_key.txt
gcloud secrets versions add telegram-token --data-file=telegram_token.txt

# 2. Verify secrets exist
gcloud secrets list

# 3. Force reload
curl -X POST https://ai-quant-trading.uc.r.appspot.com/api/reload-config
```

#### 4.2 Verify Configuration

```bash
# Check credentials loaded
curl https://ai-quant-trading.uc.r.appspot.com/api/config/credentials

# Test connections
curl -X POST https://ai-quant-trading.uc.r.appspot.com/api/config/test-multiple \
  -H "Content-Type: application/json" \
  -d '{"services": ["oanda", "marketaux", "telegram"]}'
```

---

### Phase 5: Monitoring & Validation

#### 5.1 Health Checks

```bash
# 1. System health
curl https://ai-quant-trading.uc.r.appspot.com/api/health

# 2. Trading status
curl https://ai-quant-trading.uc.r.appspot.com/api/accounts

# 3. Active strategies
curl https://ai-quant-trading.uc.r.appspot.com/api/strategies/active

# 4. API usage
curl https://ai-quant-trading.uc.r.appspot.com/api/config/usage
```

#### 5.2 Monitor Logs

```bash
# View real-time logs
gcloud app logs tail -s default --stream

# Check for errors
gcloud app logs read --service default --limit 100 | grep ERROR

# Monitor warnings
gcloud app logs read --service default --limit 100 | grep WARNING
```

#### 5.3 Verification Checklist

**Trading System:**
- [ ] All 10 accounts accessible
- [ ] Strategy scanner running (checks every 5 min)
- [ ] Trades executing normally
- [ ] P&L calculations correct

**Dashboard:**
- [ ] Real-time data updates
- [ ] WebSocket connections working
- [ ] No JavaScript errors in console
- [ ] Navigation working correctly

**API Configuration:**
- [ ] All credentials loaded
- [ ] Test connections successful
- [ ] Usage statistics updating
- [ ] No authentication errors

**Backup System:**
- [ ] Config backups creating automatically
- [ ] Backup directory accessible
- [ ] Last 10 backups preserved
- [ ] Recovery process tested

---

## Rollback Procedure

### If Issues Detecte

#### Step 1: Stop Trading (If Critical)

```bash
# Deactivate all accounts
from google_cloud_trading_system.src.core.yaml_manager import get_yaml_manager

yaml_mgr = get_yaml_manager()
accounts = yaml_mgr.get_all_accounts()

for acc in accounts:
    yaml_mgr.toggle_account(acc['id'], active=False)
```

#### Step 2: Rollback Deployment

```bash
# Revert to previous version
gcloud app versions migrate v0 --service default

# Or delete current deployment
gcloud app versions delete v1 --service default
```

#### Step 3: Restore Configuration

```bash
# Restore from backup
cp accounts.yaml.backup_20241216 accounts.yaml

# Restore environment files
cp oanda_config.env.backup oanda_config.env
cp news_api_config.env.backup news_api_config.env
```

#### Step 4: Restart Services

```bash
# Local services
pkill -f "advanced_dashboard.py"
python dashboard/advanced_dashboard.py &

# Cloud services
gcloud app versions stop v1
gcloud app versions start v0
```

---

## Post-Deployment Tasks

### 1. Documentation Update
- [ ] Update team on new features
- [ ] Share API configuration guide
- [ ] Provide strategy management tutorial
- [ ] Document rollback procedures

### 2. User Training
- [ ] Dashboard navigation walkthrough
- [ ] API configuration demonstration
- [ ] Strategy management tutorial
- [ ] Troubleshooting guide

### 3. Monitoring Setup
- [ ] Set up alerting for errors
- [ ] Monitor API usage trends
- [ ] Track system performance
- [ ] Review daily logs

### 4. Optimization
- [ ] Performance benchmarks
- [ ] Resource usage analysis
- [ ] Cost optimization review
- [ ] Security audit

---

## Maintenance Schedule

### Daily
- [ ] Check API usage statistics
- [ ] Review error logs
- [ ] Verify trading activity
- [ ] Monitor system health

### Weekly
- [ ] Review strategy performance
- [ ] Check configuration backups
- [ ] Update documentation
- [ ] Security review

### Monthly
- [ ] Rotate API keys
- [ ] Review and archive logs
- [ ] Performance optimization
- [ ] System updates

---

## Success Criteria

### Technical Metrics
- ✅ Zero downtime during deployment
- ✅ All services operational
- ✅ No data loss
- ✅ Performance maintained

### Functional Metrics
- ✅ API configuration accessible
- ✅ Strategy management working
- ✅ Navigation intuitive
- ✅ All features operational

### Business Metrics
- ✅ Trading continuity maintained
- ✅ No revenue impact
- ✅ User satisfaction positive
- ✅ Cost within budget

---

## Emergency Contacts

**Development Team:**
- Primary: [Contact Info]
- Secondary: [Contact Info]

**Google Cloud Support:**
- Console: https://console.cloud.google.com/support
- Status: https://status.cloud.google.com

**OANDA Support:**
- Email: support@oanda.com
- Phone: [Number]

---

## Additional Resources

- **System Architecture:** `SYSTEM_CONSOLIDATION_STATUS.md`
- **API Configuration:** `API_CONFIGURATION_GUIDE.md`
- **Strategy Management:** `STRATEGY_MANAGEMENT_GUIDE.md`
- **Google Cloud Docs:** https://cloud.google.com/docs
- **Trading System Docs:** `/Users/mac/quant_system_clean/README.md`

---

**Last Updated:** December 2024  
**Version:** 1.0  
**Status:** Ready for Deployment

