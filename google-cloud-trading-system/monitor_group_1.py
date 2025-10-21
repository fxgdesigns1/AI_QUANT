#!/usr/bin/env python3
"""
MONITOR GROUP 1: 5-MINUTE HIGH-FREQUENCY PORTFOLIO
Monitors the performance of Group 1 deployment on Strat 8
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_deployment_record():
    """Load the deployment record for Group 1"""
    try:
        # Find the most recent deployment record
        deployment_dir = "deployment_records"
        if not os.path.exists(deployment_dir):
            logger.error("❌ No deployment records found")
            return None
        
        records = [f for f in os.listdir(deployment_dir) if f.startswith("group_1_deployment_")]
        if not records:
            logger.error("❌ No Group 1 deployment records found")
            return None
        
        # Get the most recent record
        latest_record = sorted(records)[-1]
        record_path = os.path.join(deployment_dir, latest_record)
        
        with open(record_path, 'r') as f:
            record = json.load(f)
        
        logger.info(f"✅ Loaded deployment record: {latest_record}")
        return record
        
    except Exception as e:
        logger.error(f"❌ Failed to load deployment record: {e}")
        return None

def get_current_performance():
    """Get current performance metrics"""
    logger.info("📊 Getting current performance metrics...")
    
    try:
        from src.core.oanda_client import get_oanda_client
        from dotenv import load_dotenv
        
        load_dotenv('oanda_config.env')
        oanda_client = get_oanda_client()
        
        # Get account info
        account_info = oanda_client.get_account_info()
        
        # Get current prices
        instruments = ["GBP_USD", "NZD_USD", "XAU_USD"]
        prices = oanda_client.get_current_prices(instruments)
        
        # Get open positions
        positions = oanda_client.get_positions()
        
        # Get open trades
        trades = oanda_client.get_open_trades()
        
        performance = {
            "timestamp": datetime.now().isoformat(),
            "account": {
                "account_id": account_info.account_id,
                "balance": account_info.balance,
                "unrealized_pl": account_info.unrealized_pl,
                "realized_pl": account_info.realized_pl,
                "open_trade_count": account_info.open_trade_count,
                "open_position_count": account_info.open_position_count
            },
            "prices": {},
            "positions": positions,
            "trades": trades
        }
        
        # Format prices
        for instrument, price in prices.items():
            performance["prices"][instrument] = {
                "bid": price.bid,
                "ask": price.ask,
                "spread": price.ask - price.bid
            }
        
        logger.info("✅ Performance metrics retrieved")
        return performance
        
    except Exception as e:
        logger.error(f"❌ Failed to get performance metrics: {e}")
        return None

def calculate_performance_metrics(deployment_record, current_performance):
    """Calculate performance metrics vs targets"""
    
    if not deployment_record or not current_performance:
        return None
    
    targets = deployment_record["config"]["performance_targets"]
    account = current_performance["account"]
    
    # Calculate time elapsed
    deployed_at = datetime.fromisoformat(deployment_record["config"]["deployment_info"]["deployed_at"])
    current_time = datetime.now()
    time_elapsed = current_time - deployed_at
    hours_elapsed = time_elapsed.total_seconds() / 3600
    
    # Calculate metrics
    metrics = {
        "time_elapsed_hours": round(hours_elapsed, 2),
        "time_elapsed_days": round(hours_elapsed / 24, 2),
        "balance_change": round(account["balance"] - 79146.17, 2),  # Starting balance
        "balance_change_pct": round((account["balance"] - 79146.17) / 79146.17 * 100, 2),
        "unrealized_pl": account["unrealized_pl"],
        "realized_pl": account["realized_pl"],
        "total_pl": account["unrealized_pl"] + account["realized_pl"],
        "open_trades": account["open_trade_count"],
        "open_positions": account["open_position_count"],
        "targets": targets
    }
    
    # Calculate expected vs actual (simplified)
    expected_daily_wins = targets["expected_weekly_wins"] / 7
    expected_hourly_wins = expected_daily_wins / 24
    expected_wins_so_far = expected_hourly_wins * hours_elapsed
    
    metrics["expected_wins_so_far"] = round(expected_wins_so_far, 2)
    metrics["actual_trades"] = account["open_trade_count"]  # Simplified - would need historical data
    
    return metrics

def print_monitoring_report(metrics, current_performance):
    """Print comprehensive monitoring report"""
    
    print("\n" + "="*80)
    print("📊 GROUP 1 MONITORING REPORT - 5-MINUTE HIGH-FREQUENCY PORTFOLIO")
    print("="*80)
    print(f"📅 Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Time Elapsed: {metrics['time_elapsed_hours']} hours ({metrics['time_elapsed_days']} days)")
    print()
    
    print("💰 ACCOUNT PERFORMANCE:")
    print("-" * 40)
    account = current_performance["account"]
    print(f"Account ID: {account['account_id']}")
    print(f"Current Balance: ${account['balance']:,.2f}")
    print(f"Balance Change: ${metrics['balance_change']:,.2f} ({metrics['balance_change_pct']:+.2f}%)")
    print(f"Unrealized P&L: ${account['unrealized_pl']:,.2f}")
    print(f"Realized P&L: ${account['realized_pl']:,.2f}")
    print(f"Total P&L: ${metrics['total_pl']:,.2f}")
    print()
    
    print("📈 TRADING ACTIVITY:")
    print("-" * 40)
    print(f"Open Trades: {account['open_trade_count']}")
    print(f"Open Positions: {account['open_position_count']}")
    print(f"Expected Wins So Far: {metrics['expected_wins_so_far']}")
    print()
    
    print("💱 CURRENT MARKET PRICES:")
    print("-" * 40)
    for instrument, price_data in current_performance["prices"].items():
        print(f"{instrument}: {price_data['bid']:.5f} / {price_data['ask']:.5f} (Spread: {price_data['spread']:.5f})")
    print()
    
    print("🎯 PERFORMANCE TARGETS:")
    print("-" * 40)
    targets = metrics["targets"]
    print(f"Target Sharpe Ratio: {targets['target_sharpe']}")
    print(f"Target Win Rate: {targets['target_win_rate']}%")
    print(f"Target Annual Return: {targets['target_annual_return']}%")
    print(f"Expected Weekly Wins: {targets['expected_weekly_wins']}")
    print()
    
    print("📋 MONITORING STATUS:")
    print("-" * 40)
    if metrics["time_elapsed_hours"] < 48:
        remaining_hours = 48 - metrics["time_elapsed_hours"]
        print(f"🟡 Monitoring Phase: {remaining_hours:.1f} hours remaining")
        print("📊 Status: Active monitoring - collecting performance data")
    else:
        print("🟢 Monitoring Phase: Complete")
        print("📊 Status: Ready for performance evaluation")
    print()
    
    print("📊 NEXT ACTIONS:")
    print("-" * 40)
    if metrics["time_elapsed_hours"] < 24:
        print("1. Continue monitoring for full 48-hour period")
        print("2. Track trade execution quality")
        print("3. Monitor for any system issues")
        print("4. Document any adjustments needed")
    elif metrics["time_elapsed_hours"] < 48:
        print("1. Complete remaining monitoring hours")
        print("2. Prepare performance summary")
        print("3. Evaluate readiness for Group 2 deployment")
        print("4. Update deployment log with results")
    else:
        print("1. Generate final performance report")
        print("2. Evaluate Group 1 success criteria")
        print("3. Prepare for Group 2 deployment")
        print("4. Update strategy deployment log")

def save_monitoring_data(metrics, current_performance):
    """Save monitoring data to file"""
    try:
        monitoring_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "performance": current_performance
        }
        
        # Create monitoring directory if it doesn't exist
        os.makedirs("monitoring_records", exist_ok=True)
        
        # Save with timestamp
        filename = f"monitoring_records/group_1_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(monitoring_data, f, indent=2)
        
        logger.info(f"✅ Monitoring data saved: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"❌ Failed to save monitoring data: {e}")
        return None

def main():
    """Main monitoring function"""
    logger.info("🔍 MONITORING GROUP 1: 5-MINUTE HIGH-FREQUENCY PORTFOLIO")
    logger.info("=" * 70)
    
    # Load deployment record
    deployment_record = load_deployment_record()
    if not deployment_record:
        logger.error("❌ Cannot monitor without deployment record")
        return False
    
    # Get current performance
    current_performance = get_current_performance()
    if not current_performance:
        logger.error("❌ Cannot monitor without current performance data")
        return False
    
    # Calculate metrics
    metrics = calculate_performance_metrics(deployment_record, current_performance)
    if not metrics:
        logger.error("❌ Cannot calculate performance metrics")
        return False
    
    # Print report
    print_monitoring_report(metrics, current_performance)
    
    # Save monitoring data
    save_monitoring_data(metrics, current_performance)
    
    logger.info("✅ Monitoring report completed")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Group 1 monitoring successful!")
    else:
        print("\n❌ Group 1 monitoring failed!")
        print("Please check the logs and fix issues.")




