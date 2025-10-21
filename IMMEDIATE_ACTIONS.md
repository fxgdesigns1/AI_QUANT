# 🚨 IMMEDIATE ACTIONS - Do This NOW

## ⚠️ CRITICAL: Xcode Command Line Tools Installation

**A dialog box should be on your screen right now asking to install Xcode Command Line Tools.**

### ✅ What to Do RIGHT NOW:

1. **Look for the dialog box** on your screen
2. **Click the "Install" button**
3. **Click "Agree"** to the license
4. **Wait 5-10 minutes** for installation to complete
5. **You'll see "The software was installed successfully"**

**DO NOT CLOSE THE DIALOG - Click Install!**

---

## 🚀 Once Installation Completes - Run These Commands

Copy and paste these commands into your terminal:

```bash
# Navigate to project
cd /Users/mac/quant_system_clean

# Run the complete setup (does everything automatically)
./SETUP_AI_QUANT.sh
```

This script will:
- ✅ Configure Git with fxgdesigns1@gmail.com
- ✅ Set up Google Drive credentials folder
- ✅ Create symbolic links for secure credentials
- ✅ Run security checks (no sensitive data will be committed)
- ✅ Stage all files
- ✅ Create your first commit
- ✅ Configure GitHub remote
- ✅ Guide you through pushing to GitHub

---

## 📋 After Running the Script

### Step 1: Create GitHub Repository

Go to https://github.com and:
1. Click **"+"** → **"New repository"**
2. Name: **AI_QUANT**
3. Owner: **fxgdesigns1**
4. Visibility: **Private** (recommended)
5. **DO NOT** check "Initialize with README"
6. Click **"Create repository"**

### Step 2: Get Personal Access Token

Go to https://github.com/settings/tokens and:
1. Click **"Generate new token (classic)"**
2. Name it: **"AI_QUANT"**
3. Check the **`repo`** scope
4. Click **"Generate token"**
5. **COPY THE TOKEN** (save it somewhere!)

### Step 3: Push to GitHub

```bash
git push -u origin main
```

When prompted:
- **Username:** fxgdesigns1
- **Password:** Paste the Personal Access Token

### Step 4: Edit Credentials in Google Drive

```bash
open "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml"
```

Add your OANDA credentials (Account ID, API key, etc.)

---

## 🎯 After Setup - Working from Git (Correct Workflow)

### Daily Development Workflow:

#### Morning - Start Your Day:
```bash
cd /Users/mac/quant_system_clean

# Get latest changes from GitHub
git pull origin main

# Check what branch you're on
git branch

# Check if there are any changes
git status
```

#### During Development:
```bash
# Create a new feature branch (best practice)
git checkout -b feature/your-feature-name

# Make your changes to files...
# Edit code, test, develop

# Check what changed
git status
git diff

# Test your changes
cd google-cloud-trading-system
python3 src/main.py --test
```

#### Saving Your Work:
```bash
# Stage specific files
git add filename.py

# Or stage all changes
git add .

# Review what you're about to commit
git status

# Commit with a clear message
git commit -m "Add: brief description of what you did"

# Push to your feature branch
git push origin feature/your-feature-name
```

#### Merging to Main:
```bash
# Switch to main branch
git checkout main

# Pull latest changes
git pull origin main

# Merge your feature branch
git merge feature/your-feature-name

# Push to GitHub
git push origin main

# Delete the feature branch (optional)
git branch -d feature/your-feature-name
```

---

## 📊 Git Best Practices

### Branch Strategy:

```
main (or master)  ← Production-ready code
  ↑
  └── feature/new-strategy  ← New strategy development
  └── fix/bug-fix          ← Bug fixes
  └── docs/update-readme   ← Documentation updates
```

### Commit Messages:

**Good:**
```bash
git commit -m "Add: EMA crossover strategy with backtesting"
git commit -m "Fix: Position sizing calculation error"
git commit -m "Update: Risk management parameters for gold"
git commit -m "Remove: Deprecated scanner function"
```

**Bad:**
```bash
git commit -m "stuff"
git commit -m "fixes"
git commit -m "wip"
```

### Before Every Commit:

```bash
# 1. Check what you're committing
git status

# 2. Review the actual changes
git diff

# 3. Make sure NO sensitive data
git status | grep -E "(accounts\.yaml|\.env|credentials)"

# 4. If you see sensitive files, remove them:
git reset HEAD accounts.yaml
```

---

## 🔄 Common Git Workflows

### Scenario 1: Working Alone

```bash
# Morning
git pull

# Work on code...

# Evening
git add .
git commit -m "Update: description"
git push
```

### Scenario 2: Working with Team

```bash
# Create feature branch
git checkout -b feature/my-feature

# Work on code...

# Commit to feature branch
git add .
git commit -m "Add: my feature"
git push origin feature/my-feature

# On GitHub: Create Pull Request
# Team reviews → Merge → Delete branch
```

### Scenario 3: Hotfix (Urgent Bug)

```bash
# Create hotfix branch from main
git checkout main
git pull
git checkout -b hotfix/urgent-fix

# Fix the bug...

# Commit and push
git add .
git commit -m "Fix: urgent bug description"
git push origin hotfix/urgent-fix

# Merge immediately
git checkout main
git merge hotfix/urgent-fix
git push origin main
```

---

## 🛠️ Useful Git Commands

### Status & Info:
```bash
git status              # What's changed?
git diff                # Show exact changes
git log --oneline       # Commit history
git branch              # List branches
git remote -v           # Show remote URLs
```

### Undoing Changes:
```bash
git checkout -- file.py     # Discard changes to file
git reset HEAD file.py      # Unstage file
git commit --amend          # Modify last commit
git revert HEAD             # Undo last commit (safe)
```

### Branch Management:
```bash
git branch feature-name         # Create branch
git checkout feature-name       # Switch to branch
git checkout -b feature-name    # Create and switch
git branch -d feature-name      # Delete branch
git push origin --delete branch # Delete remote branch
```

### Syncing:
```bash
git fetch origin        # Download changes (don't merge)
git pull origin main    # Download and merge
git push origin main    # Upload your changes
```

---

## 🔒 Security Checklist (Every Time You Commit)

Run this before EVERY commit:
```bash
# Check status
git status

# Look for these files (BAD if you see them):
# ❌ accounts.yaml (only .template is OK)
# ❌ oanda_config.env
# ❌ news_api_config.env
# ❌ Any .env files
# ❌ Files with "credentials" in the name

# Quick security check:
./check_github_ready.sh

# If all good, commit:
git commit -m "Your message"
```

---

## 📂 Your Credentials Setup

Your credentials are in:
```
Google Drive: /Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/

Project: google-cloud-trading-system/accounts.yaml ➜ (symlink to Google Drive)
```

**This means:**
- ✅ Edit credentials in Google Drive (they sync everywhere)
- ✅ Project uses them via symlink
- ✅ GitHub never sees them (protected by .gitignore)
- ✅ Available on all your computers

---

## 🎯 Your Current Status

✅ Git repository initialized
✅ Google Drive credentials folder created
✅ Complete documentation ready
✅ Setup script ready
✅ .gitignore protecting sensitive data
⏳ Waiting for Xcode installation
⏳ Then run ./SETUP_AI_QUANT.sh

---

## 📞 Next Steps Summary

1. **RIGHT NOW:** Click "Install" on Xcode dialog
2. **Wait:** 5-10 minutes for installation
3. **Run:** `./SETUP_AI_QUANT.sh`
4. **Follow:** Script prompts to push to GitHub
5. **Edit:** Your credentials in Google Drive
6. **Start:** Working with proper Git workflow

---

## 🚀 You're Ready!

Once Xcode installation completes:
```bash
cd /Users/mac/quant_system_clean
./SETUP_AI_QUANT.sh
```

Then follow the Git workflow above for all future development!

**Repository:** https://github.com/fxgdesigns1/AI_QUANT
**Email:** fxgdesigns1@gmail.com
**Credentials:** Google Drive (synced & secure)

