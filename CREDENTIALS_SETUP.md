# 🔐 Credentials Management Guide - AI_QUANT

## Overview

This document explains how to securely manage your trading system credentials using Google Drive sync.

**Repository:** AI_QUANT  
**GitHub Account:** fxgdesigns1@gmail.com  
**Credentials Storage:** Google Drive (synced across all your devices)

---

## 🗂️ Credentials Location

All sensitive data is stored in:
```
/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/
```

This location:
- ✅ **Syncs across all your devices** via Google Drive
- ✅ **Not included in GitHub** (protected by .gitignore)
- ✅ **Backed up automatically** by Google
- ✅ **Accessible only to you** (private Google Drive)

---

## 📁 Directory Structure

```
Google Drive/My Drive/AI Trading/Gits/
├── AI_QUANT_credentials/
│   ├── accounts.yaml                 # OANDA account configurations
│   ├── oanda_config.env             # OANDA API keys
│   ├── news_api_config.env          # News API keys
│   ├── telegram_config.env          # Telegram bot credentials
│   ├── google_cloud_credentials.json # GCP credentials
│   └── README.md                    # This credentials guide
├── AI_QUANT_logs/                   # Optional: Trade logs backup
└── AI_QUANT_backups/                # Optional: Configuration backups
```

---

## 🚀 Initial Setup

### Step 1: Create Credentials Directory

Run this command to create the directory structure:
```bash
mkdir -p "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials"
```

### Step 2: Copy Template Files

```bash
# Copy the template to your credentials folder
cp google-cloud-trading-system/accounts.yaml.template \
   "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml"
```

### Step 3: Edit Credentials in Google Drive

```bash
# Open the file in your default editor
open "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml"
```

Add your actual OANDA credentials:
- Account IDs
- API keys
- Risk settings
- Instruments to trade

### Step 4: Create Symbolic Links

Link the credentials from Google Drive to your project:

```bash
# Link accounts file
ln -sf "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml" \
       google-cloud-trading-system/accounts.yaml

# Link OANDA config (if you create it)
ln -sf "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/oanda_config.env" \
       google-cloud-trading-system/oanda_config.env
```

**Now your credentials are:**
- ✅ Stored in Google Drive (synced & backed up)
- ✅ Accessible to your project (via symlink)
- ✅ Not in GitHub (protected by .gitignore)
- ✅ Available on all your computers (Google Drive sync)

---

## 🔄 Working on Multiple Computers

### On Computer #1 (Your Mac)

1. **Set up once** (as described above)
2. **Credentials sync** automatically via Google Drive
3. **Work normally** - the system uses the synced credentials

### On Computer #2 (New machine)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/fxgdesigns1/AI_QUANT.git
   cd AI_QUANT
   ```

2. **Ensure Google Drive is installed and synced**

3. **Create symbolic links:**
   ```bash
   ln -sf "/Users/YOUR_USERNAME/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml" \
          google-cloud-trading-system/accounts.yaml
   ```

4. **Done!** Your credentials are automatically available

---

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Store ALL sensitive data in the Google Drive folder
- ✅ Use strong passwords for your Google account
- ✅ Enable 2FA on your Google account
- ✅ Use symbolic links to access credentials
- ✅ Regularly backup your credentials folder
- ✅ Review .gitignore to ensure exclusions are correct

### ❌ DON'T:
- ❌ NEVER commit credentials to GitHub
- ❌ NEVER share your Google Drive credentials folder
- ❌ NEVER post credentials in chat/email/messages
- ❌ NEVER disable .gitignore protections
- ❌ NEVER store credentials in the main project directory

---

## 📝 File Descriptions

### accounts.yaml
Contains your OANDA trading accounts:
- Account IDs
- Display names
- Strategies assigned to each account
- Risk management settings
- Instruments to trade

**Format:**
```yaml
accounts:
  - id: "101-004-XXXXXXXX-XXX"
    name: "Demo Account 1"
    strategy: "adaptive_momentum"
    instruments: ["EUR_USD", "GBP_USD"]
    risk_settings:
      max_risk_per_trade: 0.02
```

### oanda_config.env
OANDA API configuration:
```env
OANDA_API_KEY=your-api-key-here
OANDA_ACCOUNT_ID=your-account-id-here
OANDA_ENVIRONMENT=practice
```

### news_api_config.env
News API credentials:
```env
NEWS_API_KEY=your-news-api-key
MARKETAUX_API_KEY=your-marketaux-key
```

### telegram_config.env
Telegram bot settings:
```env
TELEGRAM_BOT_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
```

### google_cloud_credentials.json
Google Cloud Platform credentials for deployment.

---

## 🔧 Troubleshooting

### Symlink Not Working?

Check if the symlink exists:
```bash
ls -la google-cloud-trading-system/accounts.yaml
```

If broken, recreate it:
```bash
rm google-cloud-trading-system/accounts.yaml
ln -sf "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml" \
       google-cloud-trading-system/accounts.yaml
```

### Google Drive Not Syncing?

1. Check Google Drive app is running
2. Check internet connection
3. Right-click the file → "Available offline"
4. Wait for sync to complete

### Credentials Not Found?

Verify the file exists:
```bash
ls -la "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/"
```

### Can't Access on New Computer?

1. Install Google Drive for Desktop
2. Sign in with fxgdesigns1@gmail.com
3. Wait for "AI Trading" folder to sync
4. Create symbolic links as described above

---

## 🚀 Quick Command Reference

### View Credentials Location
```bash
open "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials"
```

### Edit Accounts
```bash
nano "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml"
```

### Verify Symlink
```bash
ls -la google-cloud-trading-system/accounts.yaml
```

### Test Configuration
```bash
cd google-cloud-trading-system
python3 src/main.py --test
```

---

## 📊 Backup Strategy

### Automatic Backups:
- ✅ **Google Drive:** Automatic cloud backup
- ✅ **Google Drive Version History:** Recover old versions

### Manual Backups (Optional):
```bash
# Create timestamped backup
DATE=$(date +%Y%m%d_%H%M%S)
cp -r "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials" \
      "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_backups/backup_$DATE"
```

---

## 🤝 Team Collaboration

### Sharing with Team Members:

**Option 1: Individual Credentials** (Recommended)
- Each team member uses their own OANDA demo account
- Each person creates their own credentials file
- No sharing of sensitive data

**Option 2: Shared Google Drive Folder** (Risky)
- Share the "AI_QUANT_credentials" folder with team
- All team members can access same credentials
- ⚠️ **Use only with trusted team members!**

---

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Verify Google Drive is syncing
3. Check file permissions
4. Review the main README.md for system requirements

---

## 🎯 Summary

**Your credentials are:**
- 📂 Stored in Google Drive (synced)
- 🔗 Linked to project (symbolic links)
- 🚫 Not in GitHub (protected)
- 💾 Backed up automatically
- 🌍 Available on all your devices

**To get started:**
1. Run the setup commands above
2. Edit credentials in Google Drive
3. Symbolic links make them available to your project
4. Start trading!

---

**Repository:** https://github.com/fxgdesigns1/AI_QUANT  
**Credentials:** Google Drive (private & synced)  
**Status:** Secure ✅

