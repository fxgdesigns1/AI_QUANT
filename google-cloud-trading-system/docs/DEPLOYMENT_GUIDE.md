# Google Cloud Trading System - Deployment Guide

## 🎯 Overview

This guide will walk you through deploying your clean, production-ready trading system to Google Cloud Platform.

## 📋 Prerequisites

### 1. Google Cloud Account
- [Sign up for Google Cloud](https://cloud.google.com/)
- Create a new project or use existing one
- Enable billing (required for App Engine)

### 2. OANDA Demo Account
- [Sign up for OANDA demo account](https://www.oanda.com/)
- Get your API key and Account ID
- Verify account is active

### 3. Google Cloud SDK
- [Install Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Authenticate with your account

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Environment

```bash
# Navigate to the project directory
cd google-cloud-trading-system

# Set your Google Cloud project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login
```

### Step 2: Initialize Google Cloud Project

```bash
# Set the project
gcloud config set project $GOOGLE_CLOUD_PROJECT

# Enable required APIs
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

### Step 3: Deploy the Application

```bash
# Run the automated deployment script
./scripts/deploy.sh
```

**OR** deploy manually:

```bash
# Copy configuration to root
cp config/app.yaml .

# Deploy to App Engine
gcloud app deploy app.yaml

# Clean up
rm app.yaml
```

### Step 4: Configure OANDA Credentials

1. **Go to Google Cloud Console**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project

2. **Navigate to App Engine**:
   - Go to App Engine > Settings
   - Click on "Environment Variables"

3. **Add OANDA Credentials**:
   ```
   OANDA_API_KEY = your_actual_api_key_here
   OANDA_ACCOUNT_ID = your_actual_account_id_here
   ```

4. **Save Configuration**:
   - Click "Save"
   - Wait for deployment to update

### Step 5: Verify Deployment

```bash
# Get the deployed URL
gcloud app browse

# Check application logs
gcloud app logs tail -s trading-system
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OANDA_API_KEY` | OANDA API key | Yes | - |
| `OANDA_ACCOUNT_ID` | OANDA account ID | Yes | - |
| `OANDA_ENVIRONMENT` | OANDA environment | No | `practice` |
| `MAX_RISK_PER_TRADE` | Risk per trade | No | `0.02` |
| `MAX_PORTFOLIO_RISK` | Portfolio risk limit | No | `0.10` |
| `MAX_POSITIONS` | Maximum positions | No | `5` |
| `DAILY_TRADE_LIMIT` | Daily trade limit | No | `50` |

### Custom Configuration

Edit `config/app.yaml` to customize:

```yaml
env_variables:
  # Risk Management
  MAX_RISK_PER_TRADE: "0.02"      # 2% per trade
  MAX_PORTFOLIO_RISK: "0.10"      # 10% total portfolio
  MAX_POSITIONS: "5"              # Maximum positions
  DAILY_TRADE_LIMIT: "50"         # Daily trade limit
  
  # Data Settings
  MAX_DATA_AGE_SECONDS: "300"     # 5 minutes max data age
  MIN_CONFIDENCE_THRESHOLD: "0.8" # 80% confidence minimum
  REQUIRE_LIVE_DATA: "True"       # Live data only
```

## 📊 Monitoring Your Deployment

### 1. Google Cloud Console

- **App Engine**: Monitor application performance
- **Logs**: View application and error logs
- **Metrics**: Monitor CPU, memory, and request metrics

### 2. Application Dashboard

- **URL**: Your deployed application URL
- **Features**: Real-time trading dashboard
- **Monitoring**: Live account and position data

### 3. Log Monitoring

```bash
# View real-time logs
gcloud app logs tail -s trading-system

# View specific log levels
gcloud app logs read --severity=ERROR

# Export logs
gcloud app logs read --format=json > logs.json
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Make your changes to the code
# Then redeploy
./scripts/deploy.sh
```

### Updating Configuration

1. Edit `config/app.yaml`
2. Redeploy: `gcloud app deploy config/app.yaml`

### Scaling

The system automatically scales based on traffic. You can adjust scaling in `config/app.yaml`:

```yaml
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6
```

## 🛡️ Security Best Practices

### 1. Credential Management

- Store OANDA credentials in environment variables only
- Never commit credentials to version control
- Rotate API keys regularly

### 2. Access Control

- Use IAM roles for Google Cloud access
- Limit dashboard access in production
- Enable audit logging

### 3. Network Security

- All traffic is HTTPS encrypted
- Use VPC for additional network isolation
- Configure firewall rules as needed

## 🚨 Troubleshooting

### Common Issues

#### 1. Deployment Fails

```bash
# Check project permissions
gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT

# Verify APIs are enabled
gcloud services list --enabled
```

#### 2. OANDA Connection Issues

- Verify API credentials in Google Cloud Console
- Check OANDA account status
- Review application logs for errors

#### 3. High Resource Usage

- Monitor CPU and memory usage
- Adjust instance class if needed
- Check for memory leaks in logs

#### 4. No Trades Executing

- Check risk management limits
- Verify market data is flowing
- Review strategy signals in logs

### Debug Commands

```bash
# Check application status
gcloud app versions list

# View detailed logs
gcloud app logs read --severity=DEBUG

# Check instance health
gcloud app instances list
```

## 📈 Performance Optimization

### 1. Instance Configuration

Adjust instance class in `config/app.yaml`:

```yaml
instance_class: F2  # F1 (smallest) to F4 (largest)
```

### 2. Scaling Configuration

```yaml
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6
```

### 3. Resource Limits

```yaml
resources:
  cpu: 1
  memory_gb: 2
  disk_size_gb: 10
```

## 🔄 Backup and Recovery

### 1. Configuration Backup

```bash
# Backup configuration
cp config/app.yaml config/app.yaml.backup

# Backup environment variables
gcloud app describe > app-description.json
```

### 2. Code Backup

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial deployment"

# Push to remote repository
git remote add origin your-repo-url
git push -u origin main
```

## 📞 Support

### Getting Help

1. **Check Logs**: Review application logs first
2. **Google Cloud Documentation**: [App Engine Docs](https://cloud.google.com/appengine/docs)
3. **OANDA Documentation**: [OANDA API Docs](https://developer.oanda.com/)
4. **System Logs**: Check for error patterns

### Useful Commands

```bash
# View application info
gcloud app describe

# Check quotas
gcloud compute project-info describe

# View service status
gcloud app services list
```

---

**🎉 Your trading system is now deployed and ready for production use!**

Visit your deployed URL to start live OANDA paper trading with your clean, production-ready system.
