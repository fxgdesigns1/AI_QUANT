# 🔧 Integration Guide: Update Existing Code

## Quick Integration Checklist

Follow these steps to integrate Secret Manager into your existing trading system:

---

## ✅ Step 1: Update Dependencies

Add to `requirements.txt`:
```txt
google-cloud-secret-manager>=2.16.0
```

Install:
```bash
pip install google-cloud-secret-manager
```

---

## ✅ Step 2: Migrate Credentials

```bash
# Test migration (no changes)
python migrate_credentials_to_secret_manager.py \
    --project-id YOUR_PROJECT_ID \
    --dry-run

# Actually migrate
python migrate_credentials_to_secret_manager.py \
    --project-id YOUR_PROJECT_ID

# Test it works
python test_secret_manager.py
```

---

## ✅ Step 3: Update Core Files

### File: `google-cloud-trading-system/src/core/oanda_client.py`

**Find this code:**
```python
import os
from dotenv import load_dotenv

load_dotenv('oanda_config.env')
api_key = os.getenv('OANDA_API_KEY')
```

**Replace with:**
```python
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()
api_key = credentials.get('OANDA_API_KEY')
```

---

### File: `google-cloud-trading-system/src/core/telegram_notifier.py`

**Find this code:**
```python
import os
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
```

**Replace with:**
```python
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()
token = credentials.get('TELEGRAM_TOKEN')
chat_id = credentials.get('TELEGRAM_CHAT_ID')
```

---

### File: `google-cloud-trading-system/src/core/news_integration.py`

**Find this code:**
```python
import os
alpha_key = os.getenv('ALPHA_VANTAGE_API_KEY')
marketaux_key = os.getenv('MARKETAUX_API_KEY')
```

**Replace with:**
```python
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()
alpha_key = credentials.get('ALPHA_VANTAGE_API_KEY')
marketaux_key = credentials.get('MARKETAUX_API_KEY')
```

---

## ✅ Step 4: Update Main Entry Point

### File: `google-cloud-trading-system/main.py`

**Add at the top (after imports):**
```python
# Initialize credentials system
from src.core.secret_manager import get_credentials_manager
credentials = get_credentials_manager()

# Update Flask secret key to use Secret Manager
app.config['SECRET_KEY'] = credentials.get('FLASK_SECRET_KEY', 'fallback-key')
```

---

## ✅ Step 5: Environment Variables

### Local Development:
```bash
# Add to ~/.zshrc or ~/.bashrc
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Reload shell
source ~/.zshrc
```

### Google Cloud Deployment:
Update `app.yaml`:
```yaml
env_variables:
  GOOGLE_CLOUD_PROJECT: "your-project-id"
```

---

## 🎯 Pattern for All Files

Use this pattern anywhere you need credentials:

```python
from src.core.secret_manager import get_credentials_manager

# Get credentials manager (cached after first call)
credentials = get_credentials_manager()

# Get any credential
api_key = credentials.get('CREDENTIAL_NAME', 'optional_default')
```

---

## 📝 Files to Update

Here's a complete list of files that likely need updating:

### Core Files:
- ✅ `src/core/oanda_client.py` - OANDA API key
- ✅ `src/core/telegram_notifier.py` - Telegram credentials
- ✅ `src/core/news_integration.py` - News API keys
- ✅ `src/core/data_feed.py` - OANDA credentials
- ✅ `src/core/order_manager.py` - OANDA credentials
- ✅ `main.py` - Flask secret key

### Dashboard Files:
- ✅ `src/dashboard/advanced_dashboard.py` - All credentials

---

## 🔍 Finding All Uses

Search for files that need updating:
```bash
# Find all files using os.getenv with API keys
grep -r "os.getenv.*API" google-cloud-trading-system/

# Find all files loading .env
grep -r "load_dotenv" google-cloud-trading-system/

# Find all files with OANDA_API_KEY
grep -r "OANDA_API_KEY" google-cloud-trading-system/
```

---

## 🧪 Testing After Integration

### 1. Test Secret Manager:
```bash
python test_secret_manager.py
```

### 2. Test OANDA Connection:
```python
from src.core.oanda_client import OandaClient
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()
client = OandaClient(credentials.get('OANDA_API_KEY'))
print("✓ OANDA client working!")
```

### 3. Test Telegram:
```bash
python google-cloud-trading-system/send_telegram_update.py
```

### 4. Test Full System:
```bash
cd google-cloud-trading-system
python main.py
```

---

## 🚨 Troubleshooting

### Issue: "No module named 'google.cloud'"
```bash
pip install google-cloud-secret-manager
```

### Issue: "Secret 'xyz' not found"
```bash
# Re-run migration
python migrate_credentials_to_secret_manager.py --project-id YOUR_PROJECT_ID
```

### Issue: "Could not connect to Secret Manager"
```bash
# Check authentication
gcloud auth application-default login

# Check project is set
echo $GOOGLE_CLOUD_PROJECT
```

### Issue: System still works but using .env
**This is normal!** The system automatically falls back to `.env` files if Secret Manager is unavailable. Check the logs to see which mode it's using.

---

## 📦 Backward Compatibility

**Good news:** You don't have to update all files at once!

- Files using Secret Manager will use cloud credentials
- Files still using `.env` will continue to work
- Both can coexist during migration
- No downtime required

---

## 🎓 Advanced: Gradual Migration

Migrate one subsystem at a time:

### Phase 1: Core Trading (Week 1)
- `oanda_client.py`
- `order_manager.py`
- `data_feed.py`

### Phase 2: Communication (Week 2)
- `telegram_notifier.py`

### Phase 3: Analytics (Week 3)
- `news_integration.py`
- All news API integrations

### Phase 4: Dashboard (Week 4)
- `advanced_dashboard.py`
- `main.py`

---

## ✨ Benefits After Integration

✅ **Mobile Access** - Use Cursor mobile anywhere  
✅ **No .env Syncing** - Credentials stay in cloud  
✅ **Secure** - Enterprise-grade security  
✅ **Easy Updates** - Change credentials without redeploying  
✅ **Audit Trail** - See who accessed what credential when  
✅ **Automatic Rotation** - Rotate credentials on schedule  
✅ **Team Friendly** - Easy to share access (not files)  

---

## 🎯 Final Checklist

- [ ] Install google-cloud-secret-manager
- [ ] Run migration script
- [ ] Test with test_secret_manager.py
- [ ] Update oanda_client.py
- [ ] Update telegram_notifier.py
- [ ] Update news_integration.py
- [ ] Update main.py
- [ ] Set GOOGLE_CLOUD_PROJECT env var
- [ ] Test full system
- [ ] Deploy to Google Cloud
- [ ] Test from mobile
- [ ] 🎉 Celebrate!

---

## 📞 Need Help?

Check these resources:
1. [MOBILE_CREDENTIALS_SETUP.md](MOBILE_CREDENTIALS_SETUP.md) - Full setup guide
2. [example_secret_manager_usage.py](google-cloud-trading-system/example_secret_manager_usage.py) - Code examples
3. Run: `python test_secret_manager.py` - Diagnostic tool

---

**You're almost done! 🚀**

The system is designed to be easy to integrate, with automatic fallback if anything goes wrong.


