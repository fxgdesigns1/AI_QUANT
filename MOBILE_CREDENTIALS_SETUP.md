# 📱 Mobile Credentials Setup Guide

## Problem Solved ✅
You can now access your trading system from **Cursor mobile** without needing `.env` files. Your credentials are securely stored in **Google Cloud Secret Manager** and accessible from anywhere.

---

## 🎯 Benefits

✅ **Mobile Access** - Use your system from any device  
✅ **Secure** - Industry-standard encryption by Google Cloud  
✅ **No Git Commits** - Credentials never touch your repository  
✅ **Automatic Fallback** - Still works with .env files if needed  
✅ **Easy Management** - Update credentials without redeploying code  

---

## 📋 Prerequisites

1. **Google Cloud Project** (you already have one)
2. **Google Cloud SDK** installed (`gcloud` command)
3. **Python 3.8+** (you have this)

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Required Package
```bash
pip install google-cloud-secret-manager
```

### Step 2: Enable Secret Manager API
```bash
# Login to Google Cloud
gcloud auth application-default login

# Set your project (replace with your actual project ID)
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com
```

### Step 3: Migrate Your Credentials
```bash
# Test first (dry run - no changes made)
python migrate_credentials_to_secret_manager.py \
    --project-id your-project-id \
    --dry-run

# Actually migrate
python migrate_credentials_to_secret_manager.py \
    --project-id your-project-id
```

### Step 4: Test Everything Works
```bash
python test_secret_manager.py
```

You should see: **🎉 ALL TESTS PASSED!**

---

## 💻 Using in Your Code

### Before (Old Way - .env files)
```python
import os
from dotenv import load_dotenv

load_dotenv('oanda_config.env')
api_key = os.getenv('OANDA_API_KEY')
```

### After (New Way - Secret Manager)
```python
from src.core.secret_manager import get_credentials_manager

# Initialize once
credentials = get_credentials_manager()

# Get any credential
api_key = credentials.get('OANDA_API_KEY')
telegram_token = credentials.get('TELEGRAM_TOKEN')

# Get all at once
all_creds = credentials.get_all_trading_credentials()
```

### Automatic Fallback
If Secret Manager is unavailable, the system **automatically** falls back to `.env` files. No code changes needed!

---

## 📱 Mobile Access Instructions

### From Cursor Mobile:

1. **Set Environment Variable**
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

2. **Authenticate** (one-time setup)
   ```bash
   gcloud auth application-default login
   ```

3. **Run Your Trading System**
   ```bash
   python google-cloud-trading-system/main.py
   ```

Your credentials will automatically load from Google Cloud! 🚀

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` files as local backup
- Add `.env` to `.gitignore`
- Use Secret Manager for production
- Rotate credentials regularly
- Use separate credentials for dev/prod

### ❌ DON'T:
- Commit `.env` files to git
- Share credentials in chat/email
- Use production keys in development
- Hard-code credentials in code
- Share your Google Cloud project access

---

## 🛠️ Managing Credentials

### View All Secrets
```bash
gcloud secrets list --project=your-project-id
```

### View a Specific Secret
```bash
gcloud secrets versions access latest --secret="oanda-api-key"
```

### Update a Secret
```python
from src.core.secret_manager import SecretManager

sm = SecretManager(project_id='your-project-id')
sm.update_secret('oanda-api-key', 'new-api-key-value')
```

### Add a New Secret
```python
sm.create_secret('new-credential-name', 'credential-value')
```

### Delete a Secret
```python
sm.delete_secret('credential-to-remove')
```

---

## 🌐 Google Cloud Console Access

You can also manage secrets via web browser:

1. Go to: https://console.cloud.google.com/security/secret-manager
2. Select your project
3. View/Edit/Create secrets with a nice UI

Perfect for mobile! 📱

---

## 🔧 Troubleshooting

### Error: "No Google Cloud project ID found"
**Solution:**
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
# Add to ~/.zshrc to make permanent:
echo 'export GOOGLE_CLOUD_PROJECT="your-project-id"' >> ~/.zshrc
```

### Error: "Secret 'xyz' not found"
**Solution:** Run the migration script again:
```bash
python migrate_credentials_to_secret_manager.py --project-id your-project-id
```

### Error: "Permission denied"
**Solution:** Make sure you're authenticated:
```bash
gcloud auth application-default login
```

### Fallback Mode Activating
**This is normal!** The system will automatically use `.env` files if:
- Secret Manager is unavailable
- You're not authenticated
- Project ID is not set

No action needed - your system still works!

---

## 📊 What Gets Migrated

The migration script automatically handles these credentials:

**Trading:**
- `OANDA_API_KEY` → `oanda-api-key`

**Communication:**
- `TELEGRAM_TOKEN` → `telegram-token`
- `TELEGRAM_CHAT_ID` → `telegram-chat-id`

**News APIs:**
- `ALPHA_VANTAGE_API_KEY` → `alpha-vantage-api-key`
- `MARKETAUX_API_KEY` → `marketaux-api-key`
- `NEWSDATA_API_KEY` → `newsdata-api-key`
- `FMP_API_KEY` → `fmp-api-key`
- `POLYGON_API_KEY` → `polygon-api-key`
- `TWELVE_DATA_API_KEY` → `twelve-data-api-key`
- `NEWSAPI_KEY` → `newsapi-key`
- `GEMINI_API_KEY` → `gemini-api-key`

**Application:**
- `FLASK_SECRET_KEY` → `flask-secret-key`

---

## 💰 Cost

**Google Cloud Secret Manager Pricing:**
- First 10,000 accesses per month: **FREE** ✨
- Storage: $0.06 per secret per month
- Additional accesses: $0.03 per 10,000 accesses

**Your Expected Cost:** ~$0.50/month (well within free tier)

---

## 🎓 Advanced Usage

### Use Different Projects for Dev/Prod
```python
# Development
dev_creds = get_credentials_manager(project_id='my-dev-project')

# Production
prod_creds = get_credentials_manager(project_id='my-prod-project')
```

### Caching
Credentials are automatically cached in memory to reduce API calls and improve performance.

### JSON Secrets
For complex configurations:
```python
from src.core.secret_manager import SecretManager

sm = SecretManager()

# Store JSON
config = {"key1": "value1", "key2": "value2"}
sm.create_secret('my-config', json.dumps(config))

# Retrieve JSON
config = sm.get_secret_json('my-config')
```

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run the test script: `python test_secret_manager.py`
3. Verify Google Cloud authentication: `gcloud auth list`
4. Check Secret Manager API is enabled: `gcloud services list --enabled | grep secretmanager`

---

## 🎉 You're Done!

Your trading system is now:
- ✅ Mobile-ready
- ✅ Secure
- ✅ Professional
- ✅ Production-ready

**No more .env files needed for mobile access!** 🚀

---

## Quick Reference Card

```bash
# Setup (one-time)
pip install google-cloud-secret-manager
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Migrate credentials
python migrate_credentials_to_secret_manager.py --project-id your-project-id

# Test
python test_secret_manager.py

# Use in code
from src.core.secret_manager import get_credentials_manager
credentials = get_credentials_manager()
api_key = credentials.get('OANDA_API_KEY')
```

That's it! 🎯

