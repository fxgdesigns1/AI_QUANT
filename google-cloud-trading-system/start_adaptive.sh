#!/bin/bash
# Adaptive Trading System Startup Script
# Generated on 2025-09-18 02:26:43

echo "🚀 Starting Adaptive Trading System..."
echo "⏰ Start Time: $(date)"

# Change to project directory
cd /Users/mac/quant_system_clean/google-cloud-trading-system

# Start the adaptive system
python3 scripts/start_adaptive_system.py

echo "🛑 Adaptive Trading System Stopped"
echo "⏰ Stop Time: $(date)"
