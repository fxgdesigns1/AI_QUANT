#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# AI_QUANT - ONE COMMAND SETUP
# ═══════════════════════════════════════════════════════════════
# Run this after Xcode Command Line Tools are installed
# ═══════════════════════════════════════════════════════════════

clear

echo "═══════════════════════════════════════════════════════════════"
echo "              🚀 AI_QUANT - Complete Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Repository: AI_QUANT"
echo "GitHub: fxgdesigns1@gmail.com"
echo "URL: https://github.com/fxgdesigns1/AI_QUANT"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if Xcode tools are installed
if git --version 2>&1 | grep -q "xcode-select"; then
    echo "❌ ERROR: Xcode Command Line Tools not installed!"
    echo ""
    echo "Please:"
    echo "  1. Click 'Install' on the Xcode dialog"
    echo "  2. Wait for installation to complete"
    echo "  3. Run this script again: ./GO.sh"
    echo ""
    exit 1
fi

echo "✅ Xcode tools installed!"
echo ""
echo "Running complete setup..."
echo ""

# Run the main setup script
./SETUP_AI_QUANT.sh

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📖 Read IMMEDIATE_ACTIONS.md for Git workflow best practices"
echo ""
echo "Your code is ready to push to GitHub!"
echo ""

