# 🚀 AI_QUANT - Quick Start Guide

## Your Repository Setup

**Repository:** `AI_QUANT`  
**GitHub Account:** `fxgdesigns1@gmail.com`  
**GitHub URL:** https://github.com/fxgdesigns1/AI_QUANT  
**Credentials Location:** Google Drive (synced & secure)

---

## ⚡ ONE-COMMAND SETUP

Once Xcode Command Line Tools finish installing, run:

```bash
cd /Users/mac/quant_system_clean
./SETUP_AI_QUANT.sh
```

This script will:
1. ✅ Configure Git with your email (fxgdesigns1@gmail.com)
2. ✅ Create credentials folder in Google Drive
3. ✅ Set up symbolic links to keep credentials secure
4. ✅ Run security checks
5. ✅ Create your first commit
6. ✅ Configure GitHub remote for AI_QUANT
7. ✅ Guide you through pushing to GitHub

---

## 🔐 How Credentials Work

Your sensitive data (API keys, account IDs) is stored in:
```
/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/
```

**Benefits:**
- ✅ **Synced** across all your devices via Google Drive
- ✅ **Secure** - not included in GitHub repository
- ✅ **Backed up** automatically by Google
- ✅ **Accessible** to your project via symbolic links

**How it works:**
```
Project File                                Google Drive (Synced)
────────────────────────────────────────    ─────────────────────────────────
accounts.yaml (symlink) ──────────────>     accounts.yaml (actual file)
                                             ├── OANDA account IDs
                                             ├── API keys
                                             └── Trading configurations
```

The project uses a symbolic link, so:
- Your code can read the credentials
- GitHub never sees the actual credentials
- Google Drive syncs them across all your computers

---

## 📋 Step-by-Step After Running Script

### Step 1: Wait for Xcode Installation
A dialog should have appeared asking to install Xcode Command Line Tools.
👉 **Click "Install"** and wait 5-10 minutes.

### Step 2: Run Setup Script
```bash
./SETUP_AI_QUANT.sh
```

### Step 3: Create GitHub Repository
1. Go to https://github.com
2. Click **"+"** → **"New repository"**
3. Repository name: **AI_QUANT**
4. Owner: **fxgdesigns1** (or your username)
5. Visibility: **Private** (recommended)
6. **DO NOT** initialize with README
7. Click **"Create repository"**

### Step 4: Edit Your Credentials
```bash
open "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml"
```

Replace the placeholders with your actual OANDA credentials:
- Account IDs
- API keys
- Risk settings

### Step 5: Push to GitHub
```bash
git push -u origin main
```

You'll need a **Personal Access Token** (not your GitHub password):
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "AI_QUANT"
4. Check the **`repo`** scope
5. Click "Generate token"
6. Copy the token
7. Use it as your password when pushing

### Step 6: Verify on GitHub
1. Go to https://github.com/fxgdesigns1/AI_QUANT
2. Verify all files are there
3. Confirm **`accounts.yaml` is NOT visible**
4. Only `accounts.yaml.template` should be there

---

## 🌍 Using on Multiple Computers

### On a New Computer:

1. **Install Google Drive** and sign in with fxgdesigns1@gmail.com
2. **Wait for sync** to complete
3. **Clone the repository:**
   ```bash
   git clone https://github.com/fxgdesigns1/AI_QUANT.git
   cd AI_QUANT
   ```
4. **Run setup script:**
   ```bash
   ./SETUP_AI_QUANT.sh
   ```
5. **Done!** Your credentials are automatically available via Google Drive

---

## 🔄 Daily Workflow

### Morning:
```bash
cd /Users/mac/quant_system_clean
git pull  # Get latest changes
```

### During the Day:
- Make code changes
- Test strategies
- Monitor trades

### Evening:
```bash
git add .
git commit -m "Update: describe what you changed"
git push
```

Your team can see your changes when they run `git pull`!

---

## 👥 Collaborating with Others

### Inviting Team Members:
1. Go to https://github.com/fxgdesigns1/AI_QUANT
2. **Settings** → **Collaborators** → **Add people**
3. Enter their GitHub username
4. They'll receive an invitation

### For Team Members:
Each person should:
1. Clone the repository
2. Create their **own** OANDA demo account
3. Create their **own** credentials file
4. **Never share credentials**

---

## 🔒 Security Checklist

Before every commit:
```bash
git status  # Review what will be committed
```

Make sure you **DO NOT** see:
- ❌ `accounts.yaml` (only .template is OK)
- ❌ Any `.env` files
- ❌ Files with "credentials" or "api_key" in the name

If you accidentally stage a sensitive file:
```bash
git reset HEAD filename
```

---

## 📁 Project Structure

```
AI_QUANT/
├── google-cloud-trading-system/     # Main trading system
│   ├── src/
│   │   ├── main.py                  # Entry point
│   │   ├── strategies/              # Trading strategies
│   │   └── templates/               # Web dashboard
│   ├── accounts.yaml ➜ (symlink to Google Drive)
│   └── ...
├── README.md                        # Project overview
├── CREDENTIALS_SETUP.md             # Credentials guide
├── AI_QUANT_README.md              # This file
├── SETUP_AI_QUANT.sh               # Setup script
└── .gitignore                       # Security protection
```

---

## 🛠️ Running the Trading System

```bash
cd google-cloud-trading-system
python3 src/main.py
```

Open browser to: http://localhost:8080

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **`AI_QUANT_README.md`** | This quick start guide |
| **`CREDENTIALS_SETUP.md`** | Complete credentials documentation |
| **`README.md`** | Project overview and features |
| **`SETUP_GUIDE.md`** | Detailed technical setup |
| **`CONTRIBUTING.md`** | Collaboration guidelines |
| **`START_HERE.md`** | General getting started |

---

## 🆘 Troubleshooting

### "Xcode tools not installed"
Wait longer (can take 10-15 minutes). Check:
```bash
xcode-select -p
```
If it shows a path, it's installed!

### "Credentials not found"
Verify Google Drive is syncing:
```bash
ls -la "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/"
```

### "Symlink broken"
Recreate it:
```bash
./SETUP_AI_QUANT.sh
```

### "Permission denied to GitHub"
You need a Personal Access Token (see Step 5 above).

---

## ✨ What's Protected

The `.gitignore` file automatically excludes:
- ❌ `accounts.yaml` (your credentials)
- ❌ `oanda_config.env` (API keys)
- ❌ `news_api_config.env` (API keys)
- ❌ All `.env` files
- ❌ `google-cloud-credentials/` directory
- ❌ `logs/` directory
- ❌ `backups/` directory

**Your sensitive data is safe!**

---

## 🎯 Summary

**Repository:** AI_QUANT  
**Credentials:** Google Drive (synced)  
**Security:** Automatic via .gitignore  
**Setup Time:** 5 minutes  
**Team Ready:** Yes  

**To get started:**
```bash
./SETUP_AI_QUANT.sh
```

That's it! The script handles everything else.

---

## 📞 Need Help?

1. Check `CREDENTIALS_SETUP.md` for credentials questions
2. Check `SETUP_GUIDE.md` for technical setup
3. Check `CONTRIBUTING.md` for collaboration workflow
4. Open an issue on GitHub

---

**You're all set! Let's get your trading system on GitHub!** 🚀📈

**Repository:** https://github.com/fxgdesigns1/AI_QUANT

