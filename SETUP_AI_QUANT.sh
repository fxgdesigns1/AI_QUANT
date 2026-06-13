#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# AI_QUANT Repository Setup Script
# Repository: AI_QUANT on fxgdesigns1@gmail.com
# Credentials: Google Drive (synced & secure)
# ═══════════════════════════════════════════════════════════════

CREDS_DIR="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials"
GITHUB_REPO="https://github.com/fxgdesigns1/AI_QUANT.git"
GIT_EMAIL="fxgdesigns1@gmail.com"
GIT_NAME="FXG Designs"

echo "═══════════════════════════════════════════════════════════════"
echo "  AI_QUANT Repository Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 1: Verify Git is working
# ───────────────────────────────────────────────────────────────
echo "Step 1: Verifying Git installation..."
if git --version 2>&1 | grep -q "xcode-select"; then
    echo "❌ ERROR: Xcode Command Line Tools not installed yet"
    echo ""
    echo "Please run: xcode-select --install"
    echo "Then click 'Install' and wait for it to complete."
    echo ""
    exit 1
else
    echo "✅ Git is working: $(git --version)"
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 2: Configure Git
# ───────────────────────────────────────────────────────────────
echo "Step 2: Configuring Git for AI_QUANT..."
git config user.email "$GIT_EMAIL"
git config user.name "$GIT_NAME"
echo "✅ Git configured:"
echo "   Email: $GIT_EMAIL"
echo "   Name: $GIT_NAME"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 3: Create Google Drive Credentials Directory
# ───────────────────────────────────────────────────────────────
echo "Step 3: Setting up credentials directory..."
if [ ! -d "$CREDS_DIR" ]; then
    echo "Creating: $CREDS_DIR"
    mkdir -p "$CREDS_DIR"
    echo "✅ Credentials directory created"
else
    echo "✅ Credentials directory already exists"
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 4: Copy Template to Google Drive
# ───────────────────────────────────────────────────────────────
echo "Step 4: Setting up credentials template..."
if [ ! -f "$CREDS_DIR/accounts.yaml" ]; then
    if [ -f "google-cloud-trading-system/accounts.yaml.template" ]; then
        cp google-cloud-trading-system/accounts.yaml.template "$CREDS_DIR/accounts.yaml"
        echo "✅ Template copied to Google Drive"
        echo ""
        echo "⚠️  IMPORTANT: Edit this file with your OANDA credentials:"
        echo "   $CREDS_DIR/accounts.yaml"
        echo ""
    else
        echo "⚠️  Template not found, creating placeholder..."
        touch "$CREDS_DIR/accounts.yaml"
    fi
else
    echo "✅ Credentials file already exists in Google Drive"
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 5: Create Symbolic Link
# ───────────────────────────────────────────────────────────────
echo "Step 5: Creating symbolic link to credentials..."
if [ -f "google-cloud-trading-system/accounts.yaml" ] || [ -L "google-cloud-trading-system/accounts.yaml" ]; then
    echo "Removing existing accounts.yaml..."
    rm google-cloud-trading-system/accounts.yaml
fi

ln -s "$CREDS_DIR/accounts.yaml" google-cloud-trading-system/accounts.yaml
echo "✅ Symbolic link created"
echo "   google-cloud-trading-system/accounts.yaml → Google Drive"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 6: Create README in Credentials Directory
# ───────────────────────────────────────────────────────────────
echo "Step 6: Creating credentials README..."
cat > "$CREDS_DIR/README.md" << 'EOF'
# AI_QUANT Credentials

This folder contains sensitive credentials for the AI_QUANT trading system.

## ⚠️ SECURITY WARNING
**NEVER share these files or commit them to GitHub!**

## Files in This Directory

- `accounts.yaml` - OANDA account configurations and API keys
- `oanda_config.env` - OANDA API environment variables (optional)
- `news_api_config.env` - News API keys (optional)
- `telegram_config.env` - Telegram bot credentials (optional)
- `google_cloud_credentials.json` - GCP credentials (optional)

## How It Works

These files are:
1. Stored in Google Drive (synced across your devices)
2. Linked to your project via symbolic links
3. NOT included in GitHub (protected by .gitignore)
4. Backed up automatically by Google Drive

## Editing Credentials

Edit these files directly in this location. Changes will automatically sync to your project via the symbolic link.

## On Other Computers

When you clone the repository on another computer:
1. Ensure Google Drive is installed and synced
2. Run the setup script: `./SETUP_AI_QUANT.sh`
3. The script will create the necessary symbolic links

## Documentation

See `CREDENTIALS_SETUP.md` in the main repository for complete documentation.
EOF
echo "✅ README created in credentials directory"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 7: Run Security Check
# ───────────────────────────────────────────────────────────────
echo "Step 7: Running security check..."
if [ -f "./check_github_ready.sh" ]; then
    ./check_github_ready.sh
    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Security check had warnings. Review above before continuing."
        echo ""
        read -p "Continue anyway? (yes/no): " CONTINUE
        if [ "$CONTINUE" != "yes" ]; then
            exit 1
        fi
    fi
else
    echo "⚠️  check_github_ready.sh not found, skipping..."
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 8: Stage Files
# ───────────────────────────────────────────────────────────────
echo "Step 8: Staging files for commit..."
git add .
echo "✅ Files staged"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 9: Show What Will Be Committed
# ───────────────────────────────────────────────────────────────
echo "Step 9: Files ready to commit:"
echo "────────────────────────────────────────"
git status --short
echo "────────────────────────────────────────"
echo ""
echo "⚠️  SECURITY CHECK:"
echo "   Make sure 'accounts.yaml' is NOT in the list above!"
echo "   (Only 'accounts.yaml.template' should be there)"
echo ""
read -p "Does everything look safe? (yes/no): " SAFE

if [ "$SAFE" != "yes" ]; then
    echo "❌ Aborting. Please review and fix."
    exit 1
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 10: Commit
# ───────────────────────────────────────────────────────────────
echo "Step 10: Creating commit..."
git commit -m "Initial commit: AI_QUANT Trading System

- Multi-strategy trading framework
- Real-time dashboard with advanced analytics
- Risk management and position sizing
- News integration and sentiment analysis
- Telegram alerts and notifications
- Secure credentials via Google Drive
- Complete documentation for setup and collaboration"

if [ $? -eq 0 ]; then
    echo "✅ Commit created successfully"
else
    echo "⚠️  Commit failed or nothing to commit"
fi
echo ""

# ───────────────────────────────────────────────────────────────
# Step 11: Set Up GitHub Remote
# ───────────────────────────────────────────────────────────────
echo "Step 11: Setting up GitHub remote..."
if git remote get-url origin &> /dev/null; then
    echo "Remote 'origin' already exists. Updating URL..."
    git remote set-url origin "$GITHUB_REPO"
else
    echo "Adding remote 'origin'..."
    git remote add origin "$GITHUB_REPO"
fi
echo "✅ Remote configured: $GITHUB_REPO"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 12: Instructions for GitHub
# ───────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════════════════════"
echo "  ✅ SETUP COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next Steps:"
echo ""
echo "1. CREATE GITHUB REPOSITORY (if not already created):"
echo "   • Go to https://github.com"
echo "   • Click '+' → 'New repository'"
echo "   • Repository name: AI_QUANT"
echo "   • Owner: fxgdesigns1"
echo "   • Visibility: Private (recommended)"
echo "   • DO NOT initialize with README"
echo "   • Click 'Create repository'"
echo ""
echo "2. EDIT YOUR CREDENTIALS:"
echo "   open \"$CREDS_DIR/accounts.yaml\""
echo ""
echo "   Replace placeholders with your actual OANDA credentials."
echo ""
echo "3. PUSH TO GITHUB:"
echo "   git push -u origin main"
echo ""
echo "   (Or 'master' if your branch is called master)"
echo ""
echo "   You'll need a Personal Access Token as password:"
echo "   → Get it at: https://github.com/settings/tokens"
echo "   → Select 'repo' scope"
echo "   → Use the token as your password when prompted"
echo ""
echo "4. VERIFY ON GITHUB:"
echo "   • Go to: https://github.com/fxgdesigns1/AI_QUANT"
echo "   • Verify all files are there"
echo "   • Confirm 'accounts.yaml' is NOT visible"
echo "   • Only 'accounts.yaml.template' should be there"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📂 Your credentials are stored securely in:"
echo "   $CREDS_DIR"
echo ""
echo "🔗 Linked to project via symbolic link (not in GitHub)"
echo "☁️  Synced across all your devices via Google Drive"
echo "🔒 Protected by .gitignore"
echo ""
echo "📖 For more information, see:"
echo "   • CREDENTIALS_SETUP.md - Complete credentials guide"
echo "   • START_HERE.md - Getting started guide"
echo "   • README.md - Project overview"
echo ""
echo "════════════════════════════════════════════════════════════"

