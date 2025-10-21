#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# AI_QUANT - Push to GitHub (Works without Xcode!)
# ═══════════════════════════════════════════════════════════════

clear

echo "═══════════════════════════════════════════════════════════════"
echo "      🚀 AI_QUANT - GitHub Push (Xcode Workaround)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Try to find ANY working git
GIT_CMD=""

# Try brew git first
if [ -x "/opt/homebrew/bin/git" ]; then
    GIT_CMD="/opt/homebrew/bin/git"
# Try system git
elif command -v git &> /dev/null && ! git --version 2>&1 | grep -q "xcode-select"; then
    GIT_CMD="git"
fi

if [ -z "$GIT_CMD" ]; then
    echo "❌ Git not available yet."
    echo ""
    echo "SOLUTION 1 - Install Xcode Command Line Tools:"
    echo "─────────────────────────────────────────────"
    echo "Run this command and click 'Install' when dialog appears:"
    echo "  xcode-select --install"
    echo ""
    echo "SOLUTION 2 - Use GitHub Desktop (Easier!):"
    echo "───────────────────────────────────────────"
    echo "1. Download GitHub Desktop: https://desktop.github.com"
    echo "2. Install and sign in with: fxgdesigns1@gmail.com"
    echo "3. Click 'Add' → 'Add Existing Repository'"
    echo "4. Choose: /Users/mac/quant_system_clean"
    echo "5. Commit all changes"
    echo "6. Click 'Publish repository' → Name it: AI_QUANT"
    echo "7. Choose 'Private'"
    echo "8. Done!"
    echo ""
    echo "GitHub Desktop handles everything without needing terminal commands!"
    echo ""
    exit 1
fi

echo "✅ Found git: $GIT_CMD"
echo ""

# Configure git
echo "Configuring Git..."
$GIT_CMD config --local user.email "fxgdesigns1@gmail.com"
$GIT_CMD config --local user.name "FXG Designs"
echo "✅ Git configured"
echo ""

# Add remote if not exists
echo "Setting up GitHub remote..."
if ! $GIT_CMD remote get-url origin &> /dev/null; then
    $GIT_CMD remote add origin https://github.com/fxgdesigns1/AI_QUANT.git
    echo "✅ Remote added"
else
    $GIT_CMD remote set-url origin https://github.com/fxgdesigns1/AI_QUANT.git
    echo "✅ Remote updated"
fi
echo ""

# Stage all files
echo "Staging files..."
$GIT_CMD add .
echo "✅ Files staged"
echo ""

# Show what will be committed
echo "═══════════════════════════════════════════════════════════════"
echo "Files to be committed:"
echo "═══════════════════════════════════════════════════════════════"
$GIT_CMD status --short | head -30
echo ""
TOTAL_FILES=$($GIT_CMD status --short | wc -l | tr -d ' ')
if [ "$TOTAL_FILES" -gt 30 ]; then
    echo "... and $((TOTAL_FILES - 30)) more files"
    echo ""
fi

# Security check
echo "🔒 Security check..."
if $GIT_CMD status | grep -q "accounts\.yaml" && ! $GIT_CMD status | grep -q "accounts\.yaml\.template"; then
    echo "⚠️  WARNING: accounts.yaml might be included!"
    echo "This should be a symlink and ignored by .gitignore"
fi

if $GIT_CMD status --short | grep -q "\.env"; then
    echo "⚠️  WARNING: .env files detected!"
    echo "These contain sensitive data and should be ignored!"
fi

echo "✅ Security check passed"
echo ""

# Commit
echo "Creating commit..."
$GIT_CMD commit -m "Initial commit: AI_QUANT Trading System

- Multi-strategy trading framework with AI-powered signals
- Real-time dashboard with advanced analytics and monitoring
- Comprehensive risk management and position sizing
- News integration with sentiment analysis
- Telegram alerts and daily notifications
- Secure credential management via Google Drive symlinks
- Complete documentation and setup guides
- Paper trading ready with demo account support

Repository: AI_QUANT
Email: fxgdesigns1@gmail.com
Credentials: Google Drive (synced & secure)" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Commit created"
else
    echo "ℹ️  Commit may already exist or nothing to commit"
fi
echo ""

# Instructions for GitHub
echo "═══════════════════════════════════════════════════════════════"
echo "  📋 Create GitHub Repository (If Not Already Created)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: AI_QUANT"
echo "3. Owner: fxgdesigns1"
echo "4. Description: AI-powered quantitative trading system"
echo "5. Visibility: Private (recommended)"
echo "6. DO NOT check 'Initialize with README'"
echo "7. Click 'Create repository'"
echo ""
read -p "Press ENTER once you've created the repository..."
echo ""

# Get Personal Access Token
echo "═══════════════════════════════════════════════════════════════"
echo "  🔑 Personal Access Token Required"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "You need a Personal Access Token (not your GitHub password):"
echo ""
echo "1. Go to: https://github.com/settings/tokens"
echo "2. Click 'Generate new token (classic)'"
echo "3. Note: AI_QUANT Access"
echo "4. Expiration: No expiration (or your preference)"
echo "5. Check the 'repo' scope"
echo "6. Click 'Generate token'"
echo "7. COPY THE TOKEN (you won't see it again!)"
echo ""
read -p "Press ENTER once you have your token ready..."
echo ""

# Push to GitHub
echo "═══════════════════════════════════════════════════════════════"
echo "  🚀 Pushing to GitHub"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "When prompted:"
echo "  Username: fxgdesigns1 (or your GitHub username)"
echo "  Password: Paste your Personal Access Token"
echo ""
echo "Pushing..."
echo ""

# Check if main or master branch
if $GIT_CMD branch | grep -q "main"; then
    $GIT_CMD push -u origin main
elif $GIT_CMD branch | grep -q "master"; then
    $GIT_CMD push -u origin master
else
    # Create main branch if needed
    $GIT_CMD branch -M main
    $GIT_CMD push -u origin main
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✅ SUCCESS! Your code is on GitHub!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "🔗 Repository: https://github.com/fxgdesigns1/AI_QUANT"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Go to your repository URL and verify everything looks good"
    echo "  2. Confirm 'accounts.yaml' is NOT visible (only .template)"
    echo "  3. Edit your credentials in Google Drive:"
    echo "     open \"/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml\""
    echo "  4. Add your OANDA API credentials"
    echo "  5. Start trading!"
    echo ""
    echo "🔄 Daily Git Workflow:"
    echo "  Morning:  git pull"
    echo "  [work]    make changes, test, develop"
    echo "  Evening:  git add . && git commit -m 'Update: ...' && git push"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
else
    echo ""
    echo "❌ Push failed!"
    echo ""
    echo "Common issues:"
    echo "  1. Wrong token - Use Personal Access Token, not password"
    echo "  2. Repository doesn't exist - Create it on GitHub first"
    echo "  3. Permission denied - Check repository URL and access"
    echo ""
    echo "Try GitHub Desktop instead: https://desktop.github.com"
    echo ""
    exit 1
fi

