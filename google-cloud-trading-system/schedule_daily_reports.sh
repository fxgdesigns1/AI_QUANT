#!/bin/bash
# Schedule daily Telegram reports at 9:30 PM London time

echo "📅 Scheduling daily Telegram results reports..."

# Add to crontab for 9:30 PM daily (21:30)
(crontab -l 2>/dev/null; echo "30 21 * * * cd /Users/mac/quant_system_clean/google-cloud-trading-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_results_reporter.py") | crontab -

echo "✅ Daily reports scheduled for 9:30 PM London every night"
echo ""
echo "You'll receive:"
echo "  • Full account P&L breakdown"
echo "  • Weekly target progress"
echo "  • Actions taken today"
echo "  • Tomorrow's plan"
echo ""
echo "First report: Tonight at 9:30 PM!"
