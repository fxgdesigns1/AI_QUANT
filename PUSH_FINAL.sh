#!/bin/bash

clear

echo "═══════════════════════════════════════════════════════════════"
echo "      🚀 AI_QUANT - Final Push to GitHub"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Repository: https://github.com/fxgdesigns1/AI_QUANT"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if gh is authenticated
echo "Checking GitHub authentication..."
if gh auth status 2>&1 | grep -q "Logged in"; then
    echo "✅ GitHub authenticated!"
    echo ""
    
    # Push to GitHub
    echo "Pushing to GitHub..."
    echo ""
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "  ✅ SUCCESS! Your code is now on GitHub!"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "🔗 View your repository:"
        echo "   https://github.com/fxgdesigns1/AI_QUANT"
        echo ""
        echo "📂 Edit your credentials:"
        echo "   open \"/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gits/AI_QUANT_credentials/accounts.yaml\""
        echo ""
        echo "🔄 Daily workflow:"
        echo "   git pull                     # Morning - get latest"
        echo "   [work on code]               # Edit, test, develop"
        echo "   git add . && git commit -m \"Update: ...\" && git push"
        echo "                                # Evening - share changes"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        
        # Open repository in browser
        open "https://github.com/fxgdesigns1/AI_QUANT"
    else
        echo ""
        echo "❌ Push failed!"
        echo ""
        echo "Try authenticating again:"
        echo "  gh auth login --web"
        echo ""
    fi
else
    echo "❌ Not authenticated yet!"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Please authenticate first:"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Run this command:"
    echo "  gh auth login --web"
    echo ""
    echo "Then:"
    echo "  1. Browser opens to: https://github.com/login/device"
    echo "  2. Enter the code shown in terminal"
    echo "  3. Click 'Continue' and 'Authorize'"
    echo "  4. Come back and run this script again: ./PUSH_FINAL.sh"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
fi

