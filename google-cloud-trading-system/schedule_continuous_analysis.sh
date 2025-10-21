#!/bin/bash
# Schedule continuous strategy analysis - Daily morning at 6 AM

echo "📅 Scheduling daily strategy analysis..."

# Daily morning analysis at 6:00 AM London
(crontab -l 2>/dev/null | grep -v continuous_strategy_analyzer; echo "0 6 * * * cd /Users/mac/quant_system_clean/google-cloud-trading-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 continuous_strategy_analyzer.py") | crontab -

# Daily evening results at 9:30 PM London  
(crontab -l 2>/dev/null | grep -v daily_results_reporter; echo "30 21 * * * cd /Users/mac/quant_system_clean/google-cloud-trading-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_results_reporter.py") | crontab -

echo "✅ Continuous analysis scheduled!"
echo ""
echo "Daily Updates:"
echo "  • 6:00 AM: Strategy analysis (market conditions, predictions, goals)"
echo "  • 9:30 PM: Results report (performance, progress, tomorrow plan)"
echo ""
echo "Each strategy analyzed individually:"
echo "  • Gold (XAU_USD) - Economic factors, targets, predictions"
echo "  • Ultra Strict (EUR_USD, GBP_USD) - Each pair analyzed"
echo "  • Momentum (USD_JPY) - If re-enabled"
echo ""
echo "Check your Telegram!"
