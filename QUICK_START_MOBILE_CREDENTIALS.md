# 📱 Quick Start: Mobile Credentials

## The Problem
You want to access your trading system from **Cursor mobile**, but:
- ❌ Can't use `.env` files on mobile
- ❌ Can't commit credentials to git (security risk)
- ❌ Need credentials available everywhere

## The Solution ✅
**Google Cloud Secret Manager** - Industry-standard, secure credential storage accessible from anywhere (including mobile!)

---

## 🚀 Super Quick Setup (5 Minutes)

### Option 1: Automated Script (Easiest)
```bash
./setup_mobile_credentials.sh
```

That's it! The script will:
1. Install dependencies
2. Authenticate with Google Cloud
3. Enable Secret Manager API
4. Migrate all your credentials
5. Test everything works

### Option 2: Manual Steps

```bash
# 1. Install dependencies
pip install google-cloud-secret-manager

# 2. Authenticate
gcloud auth application-default login

# 3. Set your project
export GOOGLE_CLOUD_PROJECT="your-project-id"

# 4. Enable API
gcloud services enable secretmanager.googleapis.com

# 5. Migrate credentials
python migrate_credentials_to_secret_manager.py --project-id your-project-id

# 6. Test
python test_secret_manager.py
```

---

## 📝 What Gets Stored

All these credentials are automatically migrated to Google Cloud:

**Trading:**
- OANDA_API_KEY

**Communication:**
- TELEGRAM_TOKEN
- TELEGRAM_CHAT_ID

**News APIs:**
- ALPHA_VANTAGE_API_KEY
- MARKETAUX_API_KEY
- NEWSDATA_API_KEY
- FMP_API_KEY
- POLYGON_API_KEY
- TWELVE_DATA_API_KEY
- NEWSAPI_KEY
- GEMINI_API_KEY

**Application:**
- FLASK_SECRET_KEY

---

## 💻 Using in Your Code

### Before:
```python
import os
api_key = os.getenv('OANDA_API_KEY')
```

### After:
```python
from src.core.secret_manager import get_credentials_manager
credentials = get_credentials_manager()
api_key = credentials.get('OANDA_API_KEY')
```

See `example_secret_manager_usage.py` for more examples!

---

## 📱 Mobile Access

Once set up, access from mobile is simple:

```bash
# One-time authentication on mobile
gcloud auth application-default login

# Set project
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Run your system - credentials load automatically!
python google-cloud-trading-system/main.py
```

Your credentials are securely loaded from Google Cloud! 🎉

---

## 🔒 Security Features

✅ **Encrypted at rest** - Google Cloud encryption  
✅ **Encrypted in transit** - TLS/SSL  
✅ **Access control** - IAM permissions  
✅ **Audit logging** - See who accessed what  
✅ **Automatic versioning** - Rollback if needed  
✅ **No git commits** - Credentials never in code  

---

## 💰 Cost

**Free Tier:**
- First 10,000 accesses/month: FREE
- Storage: ~$0.50/month total

**Your usage:** Well within free tier! 🎯

---

## 🔧 Troubleshooting

### "No module named 'google.cloud'"
```bash
pip install google-cloud-secret-manager
```

### "Could not connect to Secret Manager"
```bash
gcloud auth application-default login
```

### "Secret not found"
```bash
python migrate_credentials_to_secret_manager.py --project-id YOUR_PROJECT_ID
```

### System uses .env instead of Secret Manager
**This is normal!** It's the automatic fallback. Everything still works.

---

## 📚 Full Documentation

- **MOBILE_CREDENTIALS_SETUP.md** - Complete setup guide with troubleshooting
- **INTEGRATION_GUIDE.md** - How to update your existing code
- **example_secret_manager_usage.py** - Code examples and patterns

---

## ✅ Verification Checklist

After setup, verify everything works:

```bash
# Test Secret Manager
python test_secret_manager.py
# Should see: "🎉 ALL TESTS PASSED!"

# Test trading system
python google-cloud-trading-system/main.py
# Should start normally and load credentials

# Test from different directory (simulates mobile)
cd /tmp
python /Users/mac/quant_system_clean/test_secret_manager.py
# Should still work!
```

---

## 🎉 Benefits

After setup, you have:

✅ **Mobile-ready trading system**  
✅ **Secure credential management**  
✅ **Access from anywhere**  
✅ **No .env files to sync**  
✅ **Professional security**  
✅ **Easy team collaboration**  
✅ **Automatic fallback (if Secret Manager unavailable)**  

---

## 🤔 FAQ

**Q: Do I need to delete my .env files?**  
A: No! Keep them as backup. The system uses Secret Manager first, falls back to .env if needed.

**Q: What if Secret Manager is down?**  
A: Automatic fallback to .env files. No downtime!

**Q: Can I still use .env files?**  
A: Yes! You can disable Secret Manager per-file or per-credential.

**Q: Is this secure enough for live trading?**  
A: Yes! Google Cloud Secret Manager is used by major banks and financial institutions.

**Q: What about my existing code?**  
A: It still works! No changes required. Update gradually when convenient.

**Q: Cost?**  
A: ~$0.50/month, mostly free tier. Negligible for trading profits! 💰

---

## 🚀 Ready to Start?

**Quickest way:**
```bash
./setup_mobile_credentials.sh
```

**Or read full guide:**
```bash
cat MOBILE_CREDENTIALS_SETUP.md
```

**Need help?**
```bash
python test_secret_manager.py  # Diagnostic tool
```

---

## 📞 Support

If you get stuck:
1. Run `python test_secret_manager.py` for diagnostics
2. Check `MOBILE_CREDENTIALS_SETUP.md` for detailed troubleshooting
3. See `example_secret_manager_usage.py` for code examples

---

**Let's secure those credentials! 🔐🚀**

*Your trading system, now accessible from anywhere, securely.*


