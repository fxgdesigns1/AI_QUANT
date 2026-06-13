#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# GITHUB SETUP - COPY & PASTE THESE COMMANDS
# ═══════════════════════════════════════════════════════════════
#
# Follow these steps IN ORDER after Xcode tools finish installing
#
# ═══════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "  GitHub Setup Commands - Follow Step by Step"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 1: Verify Git is working
# ───────────────────────────────────────────────────────────────
echo "STEP 1: Testing Git..."
if git --version 2>&1 | grep -q "xcode-select"; then
    echo "❌ ERROR: Xcode Command Line Tools not installed yet"
    echo ""
    echo "Please wait for the installation to complete, then run this script again."
    echo ""
    exit 1
else
    echo "✅ Git is working!"
    git --version
fi
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 2: Configure Git (if not already configured)
# ───────────────────────────────────────────────────────────────
echo "STEP 2: Configuring Git..."
if [ -z "$(git config user.name)" ]; then
    echo "⚠️  Git user.name not set"
    echo ""
    read -p "Enter your name: " USERNAME
    git config --global user.name "$USERNAME"
    echo "✅ Set user.name to: $USERNAME"
else
    echo "✅ Git user.name: $(git config user.name)"
fi

if [ -z "$(git config user.email)" ]; then
    echo "⚠️  Git user.email not set"
    echo ""
    read -p "Enter your email: " USEREMAIL
    git config --global user.email "$USEREMAIL"
    echo "✅ Set user.email to: $USEREMAIL"
else
    echo "✅ Git user.email: $(git config user.email)"
fi
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 3: Run security check
# ───────────────────────────────────────────────────────────────
echo "STEP 3: Running security check..."
if [ -f "check_github_ready.sh" ]; then
    ./check_github_ready.sh
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Security check failed! Please fix issues above before continuing."
        exit 1
    fi
else
    echo "⚠️  check_github_ready.sh not found, skipping..."
fi
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 4: Stage files
# ───────────────────────────────────────────────────────────────
echo "STEP 4: Staging files for commit..."
git add .
echo "✅ Files staged"
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 5: Show what will be committed
# ───────────────────────────────────────────────────────────────
echo "STEP 5: Review files to be committed..."
echo ""
git status
echo ""
echo "⚠️  SECURITY CHECK: Review the list above carefully!"
echo ""
echo "Make sure you DO NOT see:"
echo "  ❌ accounts.yaml (only accounts.yaml.template is OK)"
echo "  ❌ oanda_config.env"
echo "  ❌ Any files with credentials or API keys"
echo ""
read -p "Does everything look safe? (yes/no): " SAFE

if [ "$SAFE" != "yes" ]; then
    echo "❌ Aborting. Please review and fix before continuing."
    exit 1
fi
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 6: Commit
# ───────────────────────────────────────────────────────────────
echo "STEP 6: Creating commit..."
git commit -m "Initial commit: AI Trading System with multi-strategy framework"
echo "✅ Commit created"
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 7: Add GitHub remote
# ───────────────────────────────────────────────────────────────
echo "STEP 7: Adding GitHub remote..."
echo ""
echo "First, create a repository on GitHub:"
echo "  1. Go to https://github.com"
echo "  2. Click '+' → 'New repository'"
echo "  3. Name it (e.g., 'quant-trading-system')"
echo "  4. Choose Private or Public"
echo "  5. DO NOT initialize with README"
echo "  6. Click 'Create repository'"
echo ""
read -p "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ No URL provided. Exiting."
    exit 1
fi

git remote add origin "$REPO_URL"
echo "✅ Remote added: $REPO_URL"
echo ""

# ───────────────────────────────────────────────────────────────
# STEP 8: Push to GitHub
# ───────────────────────────────────────────────────────────────
echo "STEP 8: Pushing to GitHub..."
echo ""
echo "You may be prompted for credentials:"
echo "  Username: Your GitHub username"
echo "  Password: Use a Personal Access Token (not your GitHub password)"
echo ""
echo "Get a token at: https://github.com/settings/tokens"
echo ""
read -p "Ready to push? (yes/no): " READY

if [ "$READY" != "yes" ]; then
    echo "❌ Push cancelled."
    echo ""
    echo "When ready, run manually:"
    echo "  git push -u origin main"
    exit 0
fi

# Try main first, then master
if git show-ref --verify --quiet refs/heads/main; then
    git push -u origin main
else
    git push -u origin master
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  ✅ SUCCESS! Your code is now on GitHub!"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "View your repository at: $REPO_URL"
    echo ""
    echo "Next steps:"
    echo "  1. Go to your repository URL and verify everything looks good"
    echo "  2. Invite collaborators: Settings → Collaborators → Add people"
    echo "  3. Share the repository with your team"
    echo "  4. Team members: Follow SETUP_GUIDE.md to get started"
    echo ""
    echo "Daily workflow:"
    echo "  git pull         # Get latest changes"
    echo "  [make changes]   # Code, test, improve"
    echo "  git add .        # Stage changes"
    echo "  git commit -m \"...\"  # Commit with message"
    echo "  git push         # Share with team"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
else
    echo ""
    echo "❌ Push failed!"
    echo ""
    echo "Common issues:"
    echo "  1. Wrong credentials - Use Personal Access Token, not password"
    echo "  2. Repository doesn't exist - Create it on GitHub first"
    echo "  3. Permission denied - Check repository URL and access rights"
    echo ""
    echo "Get help at: https://docs.github.com/en/get-started"
    echo ""
    exit 1
fi

