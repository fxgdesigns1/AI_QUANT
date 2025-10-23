#!/usr/bin/env python3
"""
DEPLOY OPTIMIZED MULTI-STRATEGY PORTFOLIO
Deployment script for the 3-group optimized portfolio with 50% API reduction
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from strategies.optimized_multi_strategy_portfolio import (
    get_optimized_multi_strategy_portfolio,
    get_portfolio_performance_targets,
    get_portfolio_status
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_system_requirements():
    """Check if system is ready for deployment"""
    logger.info("🔍 Checking system requirements...")
    
    # Check if we're in the right directory
    if not os.path.exists('src/strategies/optimized_multi_strategy_portfolio.py'):
        logger.error("❌ Not in correct directory - run from google-cloud-trading-system root")
        return False
    
    # Check if strategy files exist
    strategy_files = [
        'src/strategies/group_1_5m_high_frequency.py',
        'src/strategies/group_2_15m_zero_drawdown.py',
        'src/strategies/group_3_high_win_rate.py',
        'src/strategies/optimized_multi_strategy_portfolio.py'
    ]
    
    for file_path in strategy_files:
        if not os.path.exists(file_path):
            logger.error(f"❌ Missing strategy file: {file_path}")
            return False
    
    logger.info("✅ All strategy files present")
    return True

def validate_portfolio_configuration():
    """Validate the portfolio configuration"""
    logger.info("🔍 Validating portfolio configuration...")
    
    try:
        portfolio = get_optimized_multi_strategy_portfolio()
        targets = get_portfolio_performance_targets()
        status = get_portfolio_status()
        
        logger.info("✅ Portfolio configuration validated")
        logger.info(f"📊 Total Strategies: {portfolio.total_strategies}")
        logger.info(f"📊 Unique Instruments: {len(portfolio.unique_instruments)}")
        logger.info(f"📊 API Streams: {portfolio.api_streams}")
        logger.info(f"📊 API Reduction: {portfolio.api_reduction_pct}%")
        
        return True, portfolio, targets, status
        
    except Exception as e:
        logger.error(f"❌ Portfolio validation failed: {e}")
        return False, None, None, None

def display_portfolio_summary(portfolio, targets, status):
    """Display comprehensive portfolio summary"""
    logger.info("📊 OPTIMIZED MULTI-STRATEGY PORTFOLIO SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"Portfolio Name: {portfolio.portfolio_name}")
    logger.info(f"Description: {portfolio.portfolio_description}")
    logger.info(f"Total Strategies: {portfolio.total_strategies}")
    logger.info(f"Unique Instruments: {portfolio.unique_instruments}")
    logger.info(f"API Streams: {portfolio.api_streams} (vs {portfolio.total_strategies} individual)")
    logger.info(f"API Reduction: {portfolio.api_reduction_pct}%")
    
    logger.info("\n📈 PERFORMANCE TARGETS:")
    logger.info(f"Combined Sharpe Ratio: {targets['combined_targets']['sharpe_ratio']}")
    logger.info(f"Combined Win Rate: {targets['combined_targets']['win_rate_pct']}%")
    logger.info(f"Combined Annual Return: {targets['combined_targets']['annual_return_pct']}%")
    logger.info(f"Expected Weekly Wins: {targets['combined_targets']['weekly_wins']}")
    logger.info(f"Max Drawdown: {targets['combined_targets']['max_drawdown_pct']}%")
    
    logger.info("\n🎯 STRATEGY GROUPS:")
    for group_name, group in portfolio.groups.items():
        logger.info(f"{group_name.upper()}:")
        logger.info(f"  - Instruments: {group.instruments}")
        logger.info(f"  - Timeframe: {group.timeframe}")
        logger.info(f"  - Target Sharpe: {group.target_sharpe}")
        logger.info(f"  - Target Win Rate: {group.target_win_rate}%")
        logger.info(f"  - Target Annual Return: {group.target_annual_return}%")
    
    logger.info("\n💰 RISK MANAGEMENT:")
    logger.info(f"Risk per Trade: ${targets['risk_management']['risk_per_trade']}")
    logger.info(f"Max Concurrent Positions: {targets['risk_management']['max_concurrent_positions']}")
    logger.info(f"Max Daily Trades: {targets['risk_management']['max_daily_trades']}")
    logger.info(f"Position Allocation: {targets['risk_management']['position_allocation']}")

def suggest_account_allocation():
    """Suggest demo account allocation for the 3 groups"""
    logger.info("\n🏦 SUGGESTED DEMO ACCOUNT ALLOCATION:")
    logger.info("=" * 50)
    
    # Based on the existing account structure from the codebase
    suggested_accounts = {
        "Group 1 (5m High-Frequency)": {
            "account_id": "101-004-30719775-015",  # New account for Group 1
            "instruments": ["GBP_USD", "NZD_USD", "XAU_USD"],
            "timeframe": "5m",
            "priority": "HIGHEST - Start here"
        },
        "Group 2 (15m Zero-Drawdown)": {
            "account_id": "101-004-30719775-016",  # New account for Group 2
            "instruments": ["GBP_USD", "XAU_USD"],
            "timeframe": "15m",
            "priority": "HIGH - Add after Group 1 success"
        },
        "Group 3 (High Win Rate)": {
            "account_id": "101-004-30719775-017",  # New account for Group 3
            "instruments": ["EUR_JPY", "USD_CAD"],
            "timeframe": "5m",
            "priority": "MEDIUM - Add after Group 2 success"
        }
    }
    
    for group_name, config in suggested_accounts.items():
        logger.info(f"{group_name}:")
        logger.info(f"  - Account ID: {config['account_id']}")
        logger.info(f"  - Instruments: {config['instruments']}")
        logger.info(f"  - Timeframe: {config['timeframe']}")
        logger.info(f"  - Priority: {config['priority']}")
        logger.info("")

def deployment_plan():
    """Display the deployment plan"""
    logger.info("\n🚀 DEPLOYMENT PLAN:")
    logger.info("=" * 30)
    
    phases = [
        {
            "phase": "Phase 1: Group 1 Deployment",
            "duration": "Week 1-2",
            "tasks": [
                "Configure Group 1 (5m High-Frequency)",
                "Allocate demo account 101-004-30719775-015",
                "Deploy and test",
                "Monitor for 48 hours",
                "Document performance",
                "Make adjustments if needed"
            ]
        },
        {
            "phase": "Phase 2: Group 2 Addition",
            "duration": "Week 3-4",
            "tasks": [
                "Configure Group 2 (15m Zero-Drawdown)",
                "Allocate demo account 101-004-30719775-016",
                "Deploy alongside Group 1",
                "Monitor combined performance",
                "Optimize allocation between groups",
                "Document results"
            ]
        },
        {
            "phase": "Phase 3: Complete Portfolio",
            "duration": "Week 5-6",
            "tasks": [
                "Configure Group 3 (High Win Rate)",
                "Allocate demo account 101-004-30719775-017",
                "Deploy full portfolio",
                "Monitor all 3 groups",
                "Final optimization",
                "Prepare for live trading"
            ]
        }
    ]
    
    for phase_info in phases:
        logger.info(f"{phase_info['phase']} ({phase_info['duration']}):")
        for task in phase_info['tasks']:
            logger.info(f"  - {task}")
        logger.info("")

def main():
    """Main deployment function"""
    logger.info("🚀 OPTIMIZED MULTI-STRATEGY PORTFOLIO DEPLOYMENT")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("")
    
    # Check system requirements
    if not check_system_requirements():
        logger.error("❌ System requirements not met")
        return False
    
    # Validate portfolio configuration
    success, portfolio, targets, status = validate_portfolio_configuration()
    if not success:
        logger.error("❌ Portfolio validation failed")
        return False
    
    # Display portfolio summary
    display_portfolio_summary(portfolio, targets, status)
    
    # Suggest account allocation
    suggest_account_allocation()
    
    # Display deployment plan
    deployment_plan()
    
    logger.info("✅ DEPLOYMENT PREPARATION COMPLETE")
    logger.info("=" * 40)
    logger.info("Next steps:")
    logger.info("1. Configure demo accounts as suggested")
    logger.info("2. Update data feed configurations")
    logger.info("3. Test API connections")
    logger.info("4. Deploy Group 1 first")
    logger.info("5. Monitor and document results")
    logger.info("")
    logger.info("📊 Expected Results:")
    logger.info(f"- 50% API reduction vs individual strategies")
    logger.info(f"- {targets['combined_targets']['weekly_wins']} weekly wins")
    logger.info(f"- {targets['combined_targets']['win_rate_pct']}% combined win rate")
    logger.info(f"- {targets['combined_targets']['annual_return_pct']}% annual return")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Deployment preparation successful!")
        print("Ready to proceed with account allocation and testing.")
    else:
        print("\n❌ Deployment preparation failed!")
        print("Please fix the issues above before proceeding.")




