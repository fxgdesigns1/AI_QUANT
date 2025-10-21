#!/bin/bash

clear
echo "═══════════════════════════════════════════════════════════════"
echo "          🚀 Finishing GitHub Push"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if already authenticated
if gh auth status 2>&1 | grep -q "Logged in"; then
    echo "✅ Already authenticated!"
    echo ""
    echo "Pushing to GitHub..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ SUCCESS! Code pushed to GitHub!"
        echo ""
        echo "View at: https://github.com/fxgdesigns1/AI_QUANT"
        open "https://github.com/fxgdesigns1/AI_QUANT"
    else
        echo "❌ Push failed. Try: git push -u origin main"
    fi
else
    echo "Need to authenticate first..."
    echo ""
    echo "Run this command in your terminal:"
    echo ""
    echo "    gh auth login --web"
    echo ""
    echo "Then enter the code shown and click Authorize."
    echo "After that, run: ./FINISH_PUSH.sh again"
fi
