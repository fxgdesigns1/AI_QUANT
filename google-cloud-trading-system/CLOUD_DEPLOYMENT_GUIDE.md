# Trading Analytics System - Cloud Deployment Guide

## Overview

This guide shows you how to deploy the complete Trading Analytics System to Google Cloud, making it accessible from anywhere with both the main trading dashboard and analytics dashboard.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed locally
4. **OANDA credentials** ready

## Quick Start

### 1. Set up Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Create or select project
gcloud projects create your-trading-project-id
gcloud config set project your-trading-project-id

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Set up OANDA Credentials in Secret Manager

```bash
# Create secrets for OANDA credentials
gcloud secrets create oanda-credentials --data-file=-

# Enter your credentials when prompted:
# api-key: your-oanda-api-key
# primary-account: 101-004-30719775-002
# gold-account: 101-004-30719775-009
# alpha-account: 101-004-30719775-011

# Grant access to Cloud Run
gcloud secrets add-iam-policy-binding oanda-credentials \
    --member="serviceAccount:your-service-account@your-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Deploy to Cloud Run

```bash
# Make deployment script executable
chmod +x deploy_analytics_to_cloud.sh

# Edit the script with your project ID
nano deploy_analytics_to_cloud.sh
# Change: PROJECT_ID="your-project-id"

# Deploy!
./deploy_analytics_to_cloud.sh
```

### 4. Access Your Dashboards

After deployment, you'll get a URL like:
```
https://trading-analytics-system-xxxxx-uc.a.run.app
```

**Main Dashboard:** `https://your-url/`
**Analytics Dashboard:** `https://your-url/analytics/`

## Detailed Deployment Steps

### Option 1: Automated Deployment (Recommended)

Use the provided deployment script:

```bash
cd google-cloud-trading-system
./deploy_analytics_to_cloud.sh
```

This script will:
1. Build Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Configure environment variables
5. Set up health checks

### Option 2: Manual Deployment

#### Step 1: Build Docker Image

```bash
# Build the image
docker build -f Dockerfile.analytics -t gcr.io/your-project-id/trading-analytics .

# Push to Google Container Registry
docker push gcr.io/your-project-id/trading-analytics
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy trading-analytics-system \
    --image gcr.io/your-project-id/trading-analytics \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --set-env-vars PORT=8080 \
    --set-secrets OANDA_API_KEY=oanda-credentials:api-key \
    --set-secrets PRIMARY_ACCOUNT=oanda-credentials:primary-account \
    --set-secrets GOLD_SCALP_ACCOUNT=oanda-credentials:gold-account \
    --set-secrets STRATEGY_ALPHA_ACCOUNT=oanda-credentials:alpha-account
```

#### Step 3: Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service trading-analytics-system \
    --domain your-domain.com \
    --region us-central1
```

## Cloud Architecture

```
Internet
    ↓
Google Cloud Run
    ↓
Trading Analytics System
    ├── Main Dashboard (Port 8080)
    ├── Analytics Dashboard (/analytics/*)
    ├── SQLite Database (Persistent Disk)
    ├── Trade Logger (OANDA Integration)
    └── Data Archiver (Cloud Storage)
```

## Environment Variables

The system uses these environment variables in cloud:

| Variable | Description | Source |
|----------|-------------|---------|
| `PORT` | Application port | Environment (8080) |
| `OANDA_API_KEY` | OANDA API key | Secret Manager |
| `OANDA_ENVIRONMENT` | OANDA environment | Environment (practice) |
| `PRIMARY_ACCOUNT` | Primary account ID | Secret Manager |
| `GOLD_SCALP_ACCOUNT` | Gold account ID | Secret Manager |
| `STRATEGY_ALPHA_ACCOUNT` | Alpha account ID | Secret Manager |
| `FLASK_SECRET_KEY` | Flask secret | Environment |

## Data Persistence

### SQLite Database
- Stored in `/app/data/trading.db`
- Persists across deployments
- Automatic backups recommended

### Archived Data
- Compressed JSON files in `/app/data/archives/`
- Can be moved to Cloud Storage for long-term storage

### Cloud Storage Integration (Optional)

```bash
# Create bucket for archives
gsutil mb gs://your-trading-archives

# Sync archives to Cloud Storage
gsutil rsync -r /app/data/archives/ gs://your-trading-archives/
```

## Monitoring and Logging

### View Logs

```bash
# View recent logs
gcloud run services logs tail trading-analytics-system --region us-central1

# View logs from specific time
gcloud run services logs read trading-analytics-system \
    --region us-central1 \
    --since 2025-10-21T10:00:00Z
```

### Set up Monitoring

```bash
# Enable monitoring
gcloud services enable monitoring.googleapis.com

# Create alerting policy
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

### Health Checks

The system provides health check endpoints:

- **Main health:** `GET /api/analytics/health`
- **Analytics health:** `GET /analytics/api/health`
- **Database stats:** `GET /analytics/api/database/stats`

## Scaling Configuration

### Automatic Scaling

Cloud Run automatically scales based on:
- Request volume
- CPU usage
- Memory usage

### Manual Scaling

```bash
# Set minimum instances
gcloud run services update trading-analytics-system \
    --min-instances 1 \
    --region us-central1

# Set maximum instances
gcloud run services update trading-analytics-system \
    --max-instances 10 \
    --region us-central1
```

## Security Configuration

### Authentication (Optional)

```bash
# Require authentication
gcloud run services update trading-analytics-system \
    --no-allow-unauthenticated \
    --region us-central1

# Add IAM binding
gcloud run services add-iam-policy-binding trading-analytics-system \
    --member="user:your-email@domain.com" \
    --role="roles/run.invoker" \
    --region us-central1
```

### Network Security

```bash
# Restrict to specific IPs
gcloud run services update trading-analytics-system \
    --ingress internal-and-cloud-load-balancing \
    --region us-central1
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
gcloud run jobs create backup-db \
    --image gcr.io/your-project-id/trading-analytics \
    --command python3 \
    --args -c "import shutil; shutil.copy('/app/data/trading.db', '/tmp/backup.db')" \
    --region us-central1

# Download backup
gcloud run jobs executions list --job backup-db --region us-central1
```

### Restore from Backup

```bash
# Upload backup to Cloud Storage
gsutil cp backup.db gs://your-trading-backups/

# Restore in new deployment
gcloud run services update trading-analytics-system \
    --set-env-vars RESTORE_FROM_BACKUP=gs://your-trading-backups/backup.db \
    --region us-central1
```

## Cost Optimization

### Resource Limits

```bash
# Optimize for cost
gcloud run services update trading-analytics-system \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 100 \
    --region us-central1
```

### Scheduled Scaling

```bash
# Scale down during off-hours
gcloud scheduler jobs create http scale-down \
    --schedule "0 22 * * *" \
    --uri "https://trading-analytics-system-xxxxx-uc.a.run.app/api/scale-down" \
    --http-method POST
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   gcloud run services logs tail trading-analytics-system --region us-central1
   
   # Check secrets
   gcloud secrets versions access latest --secret oanda-credentials
   ```

2. **Analytics dashboard not accessible**
   ```bash
   # Check if analytics routes are registered
   curl https://your-url/analytics/api/health
   ```

3. **Database connection issues**
   ```bash
   # Check database file permissions
   gcloud run services logs tail trading-analytics-system --region us-central1 | grep -i database
   ```

### Debug Mode

```bash
# Enable debug logging
gcloud run services update trading-analytics-system \
    --set-env-vars DEBUG=true \
    --region us-central1
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Response Time**
   - Main dashboard: < 200ms
   - Analytics queries: < 1s

2. **Database Performance**
   - Query time: < 100ms
   - Connection pool usage

3. **Memory Usage**
   - Peak: < 1.5GB
   - Average: < 1GB

4. **Error Rate**
   - Target: < 1%
   - Alert threshold: > 5%

### Monitoring Dashboard

Create a monitoring dashboard in Google Cloud Console:

```bash
# Create monitoring dashboard
gcloud monitoring dashboards create --config-from-file=dashboard-config.yaml
```

## Updates and Maintenance

### Rolling Updates

```bash
# Update to new version
gcloud run services update trading-analytics-system \
    --image gcr.io/your-project-id/trading-analytics:latest \
    --region us-central1
```

### Database Maintenance

```bash
# Vacuum database
gcloud run jobs create db-maintenance \
    --image gcr.io/your-project-id/trading-analytics \
    --command python3 \
    --args -c "from src.analytics.trade_database import get_trade_database; get_trade_database().vacuum_database()" \
    --region us-central1
```

## Support and Documentation

### Useful Commands

```bash
# Get service info
gcloud run services describe trading-analytics-system --region us-central1

# Get service URL
gcloud run services describe trading-analytics-system --region us-central1 --format="value(status.url)"

# Check service health
curl https://your-url/api/analytics/health

# View analytics
curl https://your-url/analytics/api/strategies
```

### Documentation

- **Analytics System:** `ANALYTICS_SYSTEM_README.md`
- **Implementation:** `ANALYTICS_IMPLEMENTATION_COMPLETE.md`
- **API Reference:** Available at `/analytics/api/health`

## Next Steps

1. **Deploy the system** using the deployment script
2. **Configure monitoring** and alerts
3. **Set up backups** for the database
4. **Test all functionality** with demo trades
5. **Monitor performance** and optimize as needed

## Cost Estimation

For a typical trading system with 10 strategies:

- **Cloud Run:** $20-50/month (depending on usage)
- **Container Registry:** $5-10/month
- **Secret Manager:** $0.06 per secret per month
- **Cloud Storage:** $5-15/month (for archives)
- **Total:** ~$30-80/month

## Conclusion

Your Trading Analytics System is now deployed to Google Cloud and accessible from anywhere. The system provides:

✅ **Main Dashboard** - Real-time trading interface  
✅ **Analytics Dashboard** - Comprehensive performance analysis  
✅ **Automatic Trade Logging** - Every trade captured  
✅ **Strategy Versioning** - Track configuration changes  
✅ **Data Retention** - 90-day detailed + archival  
✅ **Cloud Scalability** - Auto-scales with demand  
✅ **Security** - Secrets managed securely  
✅ **Monitoring** - Full observability  

Access your dashboards and start tracking your trading performance with enterprise-grade analytics!


