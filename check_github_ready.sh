#!/bin/bash

# GitHub Readiness Checker
# This script verifies your system is ready to push code to GitHub

echo "🔍 Checking GitHub Readiness..."
echo "================================"
echo ""

# Check 1: Git installation
echo "1️⃣  Checking Git installation..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    if [[ $GIT_VERSION == *"xcode-select"* ]]; then
        echo "   ❌ Xcode Command Line Tools not installed"
        echo "   → Run: xcode-select --install"
        echo "   → Click 'Install' in the dialog that appears"
        exit 1
    else
        echo "   ✅ Git is installed: $GIT_VERSION"
    fi
else
    echo "   ❌ Git is not installed"
    exit 1
fi
echo ""

# Check 2: Git repository
echo "2️⃣  Checking Git repository..."
if [ -d ".git" ]; then
    echo "   ✅ Git repository initialized"
else
    echo "   ❌ Not a Git repository"
    echo "   → Run: git init"
    exit 1
fi
echo ""

# Check 3: Security check - sensitive files
echo "3️⃣  Security check - sensitive files..."
SENSITIVE_FILES=()

if [ -f "google-cloud-trading-system/accounts.yaml" ]; then
    # Check if accounts.yaml will be committed
    if git check-ignore google-cloud-trading-system/accounts.yaml &> /dev/null; then
        echo "   ✅ accounts.yaml is properly ignored"
    else
        echo "   ⚠️  WARNING: accounts.yaml might be committed!"
        SENSITIVE_FILES+=("google-cloud-trading-system/accounts.yaml")
    fi
fi

if [ -f "google-cloud-trading-system/oanda_config.env" ]; then
    if git check-ignore google-cloud-trading-system/oanda_config.env &> /dev/null; then
        echo "   ✅ oanda_config.env is properly ignored"
    else
        echo "   ⚠️  WARNING: oanda_config.env might be committed!"
        SENSITIVE_FILES+=("google-cloud-trading-system/oanda_config.env")
    fi
fi

# Check for any .env files
if ls .env* &> /dev/null; then
    for env_file in .env*; do
        if git check-ignore "$env_file" &> /dev/null; then
            echo "   ✅ $env_file is properly ignored"
        else
            echo "   ⚠️  WARNING: $env_file might be committed!"
            SENSITIVE_FILES+=("$env_file")
        fi
    done
fi

if [ ${#SENSITIVE_FILES[@]} -gt 0 ]; then
    echo ""
    echo "   ⚠️  SECURITY ISSUE: The following sensitive files might be committed:"
    for file in "${SENSITIVE_FILES[@]}"; do
        echo "      - $file"
    done
    echo ""
    echo "   → Fix .gitignore or remove these files from git staging"
    exit 1
fi
echo ""

# Check 4: Git configuration
echo "4️⃣  Checking Git configuration..."
GIT_USER=$(git config user.name 2>&1)
GIT_EMAIL=$(git config user.email 2>&1)

if [ -z "$GIT_USER" ]; then
    echo "   ⚠️  Git user name not set"
    echo "   → Run: git config --global user.name \"Your Name\""
    HAS_WARNING=1
else
    echo "   ✅ Git user name: $GIT_USER"
fi

if [ -z "$GIT_EMAIL" ]; then
    echo "   ⚠️  Git email not set"
    echo "   → Run: git config --global user.email \"your.email@example.com\""
    HAS_WARNING=1
else
    echo "   ✅ Git email: $GIT_EMAIL"
fi
echo ""

# Check 5: Remote repository
echo "5️⃣  Checking remote repository..."
REMOTE=$(git remote get-url origin 2>&1)
if [[ $REMOTE == *"No such remote"* ]] || [ -z "$REMOTE" ]; then
    echo "   ⚠️  No GitHub remote configured yet"
    echo "   → Create a repository on GitHub first"
    echo "   → Then run: git remote add origin https://github.com/USERNAME/REPO.git"
    HAS_WARNING=1
else
    echo "   ✅ Remote configured: $REMOTE"
fi
echo ""

# Check 6: Files ready to commit
echo "6️⃣  Checking files ready to commit..."
STAGED_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
UNSTAGED_COUNT=$(git ls-files --modified | wc -l | tr -d ' ')
UNTRACKED_COUNT=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')

echo "   📝 Staged files: $STAGED_COUNT"
echo "   📝 Unstaged changes: $UNSTAGED_COUNT"
echo "   📝 Untracked files: $UNTRACKED_COUNT"

if [ "$STAGED_COUNT" -eq 0 ] && [ "$UNSTAGED_COUNT" -eq 0 ] && [ "$UNTRACKED_COUNT" -eq 0 ]; then
    echo "   ℹ️  No changes to commit"
elif [ "$STAGED_COUNT" -gt 0 ]; then
    echo "   ✅ Ready to commit!"
else
    echo "   ℹ️  Run 'git add .' to stage changes"
fi
echo ""

# Summary
echo "================================"
if [ ${#SENSITIVE_FILES[@]} -eq 0 ] && [ -z "$HAS_WARNING" ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. git add .                    (stage changes)"
    echo "   2. git status                   (review what will be committed)"
    echo "   3. git commit -m \"message\"      (commit changes)"
    echo "   4. git push -u origin main      (push to GitHub)"
    echo ""
    echo "👉 See GITHUB_QUICK_START.md for detailed instructions"
else
    echo "⚠️  SOME ISSUES FOUND"
    echo ""
    echo "Please fix the issues above before pushing to GitHub."
    echo "See GITHUB_QUICK_START.md for help."
fi
echo ""

