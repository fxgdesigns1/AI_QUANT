# Analytics Dashboard - Google Cloud Deployment Guide

## 🚀 Deploy Analytics Dashboard to Google Cloud

The analytics dashboard can run as a **separate service** on Google Cloud, allowing you to access your trading performance from anywhere.

---

## 📋 Prerequisites

1. **Google Cloud Project**: `ai-quant-trading` (or your project ID)
2. **gcloud CLI**: Installed and configured
3. **App Engine**: Enabled for your project

---

## 🎯 Quick Deployment

### One-Command Deploy:
```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system
./deploy_analytics_cloud.sh
```

This will:
1. ✅ Verify all files are present
2. ✅ Create deployment configuration
3. ✅ Deploy to Google Cloud as separate service
4. ✅ Provide access URLs

---

## 🌐 Access Your Analytics Dashboard

After deployment, your analytics dashboard will be available at:

### Main URL:
```
https://analytics-dot-ai-quant-trading.uc.r.appspot.com
```

### Specific Pages:
- **Overview**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/overview
- **PRIMARY Account**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/account/PRIMARY
- **GOLD_SCALP Account**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/account/GOLD_SCALP
- **STRATEGY_ALPHA Account**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/account/STRATEGY_ALPHA
- **Health Check**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/health
- **API Status**: https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/stats

---

## 🔧 Manual Deployment (if needed)

If you prefer manual control:

```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system/analytics

# Deploy to Google Cloud
gcloud app deploy app_analytics.yaml --quiet
```

---

## 📊 Service Configuration

### Deployed As:
- **Service Name**: `analytics` (separate from trading system)
- **Runtime**: Python 3.9
- **Instance**: F2 (1 vCPU, 1GB RAM)
- **Auto-scaling**: 1-3 instances based on load
- **Mode**: Read-Only (cannot execute trades)

### Resources:
- **CPU**: 1 vCPU
- **Memory**: 1GB RAM
- **Storage**: 10GB disk
- **Network**: Session affinity enabled

---

## 🔒 Security Features

### Read-Only Access:
- ✅ Cannot place orders
- ✅ Cannot close trades
- ✅ Cannot modify positions
- ✅ Only reads performance data

### Isolation:
- ✅ Separate service from trading system
- ✅ Independent database
- ✅ Separate scaling configuration
- ✅ No interference with trading

### HTTPS:
- ✅ All traffic encrypted (HTTPS only)
- ✅ Google Cloud SSL certificates
- ✅ Secure data transmission

---

## 📈 What's Deployed

### Data Collection:
- Account balances (every 1 minute)
- Trade history (every 5 minutes)
- Performance metrics (every 15 minutes)
- Strategy changes (real-time)

### Analytics:
- Sharpe/Sortino/Calmar ratios
- Drawdown analysis
- Win rate & profit factor
- Trade statistics
- Strategy comparison
- Change impact analysis

### Dashboard:
- Overview page (all accounts)
- Account detail pages
- Strategy performance
- Real-time updates
- API endpoints

---

## 🎯 Accessing from Different Devices

### Desktop/Laptop:
Simply open the URL in your browser:
```
https://analytics-dot-ai-quant-trading.uc.r.appspot.com/overview
```

### Mobile:
The dashboard is responsive and works on mobile devices. Bookmark the URL for quick access.

### Tablet:
Full functionality available on tablets.

### API Access:
Use the API endpoints for programmatic access:
```bash
# Get overview data
curl https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/overview/data

# Get account data
curl https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/account/PRIMARY/data

# Get system stats
curl https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/stats
```

---

## 📊 Monitoring & Management

### View Logs:
```bash
# Real-time logs
gcloud app logs tail -s analytics

# Last 100 log entries
gcloud app logs read -s analytics --limit=100
```

### Check Service Status:
```bash
# List all services
gcloud app services list

# Describe analytics service
gcloud app services describe analytics
```

### View Metrics:
```bash
# Open in browser
gcloud app browse -s analytics
```

### Stop Service (if needed):
```bash
# Note: This will stop the analytics dashboard
gcloud app services set-traffic analytics --splits=NO_VERSION=1
```

### Restart Service:
```bash
# Deploy again to restart
gcloud app deploy analytics/app_analytics.yaml --quiet
```

---

## 💰 Cost Estimation

### Free Tier:
- **28 instance hours/day** free
- **1GB egress/day** free
- **Shared CPU** included

### Analytics Dashboard Usage:
- **Min 1 instance running** = ~720 hours/month
- **Estimated cost**: $25-40/month (after free tier)

### Cost Optimization:
- Set `min_instances: 0` to reduce costs (slower cold starts)
- Use `min_instances: 1` for always-on access (current config)

---

## 🔍 Troubleshooting

### Dashboard Not Loading:
```bash
# Check service is running
gcloud app services list

# View recent errors
gcloud app logs tail -s analytics | grep ERROR
```

### Data Not Updating:
```bash
# Check collector status
curl https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/collector/status

# Trigger manual collection
curl -X POST https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/collector/collect
```

### Permission Errors:
```bash
# Ensure you're authenticated
gcloud auth login

# Set correct project
gcloud config set project ai-quant-trading
```

---

## 🔄 Updating the Dashboard

When you make changes to the analytics code:

```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system

# Test locally first
python3 analytics/app.py

# If working, deploy to cloud
./deploy_analytics_cloud.sh
```

---

## 📱 Mobile App Integration (Future)

The API endpoints are designed to be consumed by mobile apps:

```javascript
// Example: Fetch overview data
fetch('https://analytics-dot-ai-quant-trading.uc.r.appspot.com/api/overview/data')
  .then(response => response.json())
  .then(data => console.log(data));
```

---

## ⚙️ Configuration

### Environment Variables (Already Configured):
- `OANDA_API_KEY`: Your OANDA API key (read-only access)
- `PRIMARY_ACCOUNT`: Account 101-004-30719775-009
- `GOLD_SCALP_ACCOUNT`: Account 101-004-30719775-010
- `STRATEGY_ALPHA_ACCOUNT`: Account 101-004-30719775-011
- `READ_ONLY_MODE`: true (enforced)
- `TELEGRAM_TOKEN`: For alerts (optional)

All sensitive data is encrypted in transit and at rest by Google Cloud.

---

## 🚦 Service Independence

The analytics service runs **completely independently** from your trading system:

- ✅ **Separate Service**: `analytics` vs `default` (trading)
- ✅ **Separate Scaling**: Independent auto-scaling
- ✅ **Separate Resources**: Own CPU, memory, storage
- ✅ **Separate Database**: Own database instance
- ✅ **No Trading Actions**: Read-only access only

If analytics goes down, your trading system continues unaffected.

---

## 📊 Real-Time Updates

The dashboard updates automatically:
- **Account balances**: Every 1 minute
- **Trade history**: Every 5 minutes
- **Performance metrics**: Every 15 minutes
- **Dashboard refresh**: Every 30 seconds (browser)

No manual refresh needed!

---

## ✅ Deployment Checklist

Before deploying, ensure:
- [ ] Google Cloud project is set
- [ ] gcloud CLI is authenticated
- [ ] App Engine is enabled
- [ ] All files are present in `analytics/` directory
- [ ] OANDA credentials are correct in `app_analytics.yaml`

After deploying:
- [ ] Visit the health check URL
- [ ] Verify dashboard loads
- [ ] Check data is collecting
- [ ] Test API endpoints
- [ ] Monitor logs for errors

---

## 🎯 Quick Reference

### Deploy:
```bash
./deploy_analytics_cloud.sh
```

### Access:
```
https://analytics-dot-ai-quant-trading.uc.r.appspot.com/overview
```

### Logs:
```bash
gcloud app logs tail -s analytics
```

### Status:
```bash
gcloud app services list
```

---

**Your analytics dashboard is ready to deploy to the cloud!** 🚀

Simply run the deploy script and access your trading performance from anywhere in the world.


