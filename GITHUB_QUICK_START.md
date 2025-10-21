# GitHub Quick Start - Get Your Code Online NOW

## ⚠️ IMPORTANT: Xcode Command Line Tools

A dialog should have appeared asking to install Xcode Command Line Tools.
**Click "Install" and wait for it to complete** (5-10 minutes).

While it's installing, read through the steps below.

## Steps to Push Your Code to GitHub

### Step 1: Wait for Xcode Tools Installation

The installation dialog will show progress. Once it says "The software was installed", continue to Step 2.

### Step 2: Verify Git is Working

Open Terminal and run:
```bash
cd /Users/mac/quant_system_clean
git --version
```

You should see something like: `git version 2.x.x`

### Step 3: Check Repository Status

```bash
git status
```

This shows what files will be committed. **IMPORTANT:** Review the list carefully!

### Step 4: Review What Will Be Committed

```bash
# See all files that will be added
git status

# Make sure NO sensitive data will be committed:
# ❌ accounts.yaml should NOT appear (only accounts.yaml.template)
# ❌ No API keys or credentials
# ❌ No .env files with secrets
```

### Step 5: Add Files to Git

```bash
# Add all files (respecting .gitignore)
git add .

# Check what's staged
git status
```

### Step 6: Create Your First Commit

```bash
git commit -m "Initial commit: AI Trading System with multi-strategy framework"
```

### Step 7: Create GitHub Repository

1. Go to [github.com](https://github.com)
2. Click the **"+"** icon (top right) → **"New repository"**
3. Fill in:
   - **Repository name:** `quant-trading-system` (or your preferred name)
   - **Description:** "AI-powered quantitative trading system for forex and gold"
   - **Visibility:** 
     - **Private** (recommended) - Only you and invited collaborators can see it
     - **Public** - Anyone can see it (be extra careful with secrets!)
   - **DO NOT** initialize with README (you already have one)
4. Click **"Create repository"**

### Step 8: Connect Local Repository to GitHub

GitHub will show you commands. Copy and paste them, or use these:

```bash
# Replace YOUR-USERNAME and REPO-NAME with your actual values
git remote add origin https://github.com/YOUR-USERNAME/REPO-NAME.git

# Verify remote was added
git remote -v
```

### Step 9: Push Your Code

```bash
# Push to GitHub
git push -u origin main

# OR if your branch is called 'master':
git push -u origin master
```

You may be prompted for GitHub credentials. Enter:
- **Username:** Your GitHub username
- **Password:** A [Personal Access Token](https://github.com/settings/tokens) (NOT your GitHub password)

### Step 10: Verify on GitHub

1. Go to your repository URL: `https://github.com/YOUR-USERNAME/REPO-NAME`
2. You should see all your files!
3. Check that `accounts.yaml` is **NOT** there (only `accounts.yaml.template`)

## 🎉 Success! Your Code is Now on GitHub

### Access from Anywhere

```bash
# On any computer:
git clone https://github.com/YOUR-USERNAME/REPO-NAME.git
cd REPO-NAME

# Set up and run (see SETUP_GUIDE.md)
```

### Invite Collaborators

1. Go to your repository on GitHub
2. Click **"Settings"** → **"Collaborators"**
3. Click **"Add people"**
4. Enter their GitHub username or email
5. They'll receive an invitation

### Daily Workflow

```bash
# Morning: Get latest changes
git pull

# Make changes to your files...

# Afternoon: Commit your changes
git add .
git commit -m "Update: description of what you changed"
git push

# Your collaborators will see your changes!
```

## Common Commands

```bash
# See what changed
git status
git diff

# Commit changes
git add .
git commit -m "Your message"
git push

# Get latest changes
git pull

# View history
git log --oneline

# Create a new branch for experiments
git checkout -b experiment/new-strategy
```

## Security Checklist ✅

Before every commit, verify:

- [ ] No `accounts.yaml` (only `accounts.yaml.template`)
- [ ] No API keys or tokens in files
- [ ] No `.env` files with secrets
- [ ] No log files with sensitive data
- [ ] No account IDs or real trading data

```bash
# Quick security check:
git status | grep -E "(accounts\.yaml|\.env|api_key|password)"

# If you see anything suspicious, remove it:
git reset HEAD filename
```

## Troubleshooting

### "xcode-select: command not found"
You're not on macOS. Skip to Step 2, Git should work.

### "Permission denied (publickey)"
Use HTTPS instead of SSH:
```bash
git remote set-url origin https://github.com/YOUR-USERNAME/REPO-NAME.git
```

### "Support for password authentication was removed"
You need a [Personal Access Token](https://github.com/settings/tokens):
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Select scopes: `repo` (full control)
4. Copy the token
5. Use it as your password when pushing

### "Failed to push some refs"
Someone else pushed changes. Pull first:
```bash
git pull --rebase
git push
```

### I Accidentally Committed Sensitive Data!

1. **Remove from staging** (before push):
   ```bash
   git reset HEAD accounts.yaml
   git commit --amend
   ```

2. **Already pushed?** Contact a maintainer immediately and:
   - Revoke any compromised credentials
   - Remove from history (advanced - see CONTRIBUTING.md)

## Next Steps

1. ✅ Read `SETUP_GUIDE.md` for detailed setup instructions
2. ✅ Read `CONTRIBUTING.md` for collaboration guidelines
3. ✅ Invite your collaborators
4. ✅ Set up issue tracking on GitHub
5. ✅ Enable GitHub Actions for automated testing (optional)

## Support

- **Documentation:** `README.md`, `SETUP_GUIDE.md`, `CONTRIBUTING.md`
- **GitHub Guide:** [GitHub Docs](https://docs.github.com/)
- **Git Cheat Sheet:** [Git Quick Reference](https://training.github.com/downloads/github-git-cheat-sheet/)

---

**You're all set!** Your trading system is now version controlled and ready for collaboration! 🚀

Any questions? Check the docs or create an issue on GitHub.

