#!/usr/bin/env python3
"""
ACCOUNT ALLOCATION CONFIGURATION
Allocates the 3 optimized strategy groups to existing demo accounts
Based on your current account structure: Strat 4-8
"""

# Account allocation mapping for optimized strategy groups
ACCOUNT_ALLOCATION = {
    # Group 1: 5-Minute High-Frequency Portfolio (HIGHEST PRIORITY)
    "group_1_5m_high_frequency": {
        "account_name": "Strat 8",
        "account_id": "101-004-30719775-008",
        "strategy_group": "Group 1: 5-Minute High-Frequency Portfolio",
        "instruments": ["GBP_USD", "NZD_USD", "XAU_USD"],
        "timeframe": "5m",
        "priority": "HIGHEST - Deploy first",
        "target_sharpe": 38.5,
        "target_win_rate": 79.7,
        "target_annual_return": 148.0,
        "expected_weekly_wins": 132.4,
        "max_concurrent_positions": 3,
        "risk_per_trade": 200.0
    },
    
    # Group 2: 15-Minute Zero-Drawdown Portfolio (HIGH PRIORITY)
    "group_2_15m_zero_drawdown": {
        "account_name": "Strat 7",
        "account_id": "101-004-30719775-007",
        "strategy_group": "Group 2: 15-Minute Zero-Drawdown Portfolio",
        "instruments": ["GBP_USD", "XAU_USD"],
        "timeframe": "15m",
        "priority": "HIGH - Deploy after Group 1 success",
        "target_sharpe": 6.12,
        "target_win_rate": 53.6,
        "target_annual_return": 2244.0,
        "expected_weekly_wins": 43.9,
        "max_drawdown": 0.1,
        "max_concurrent_positions": 3,
        "risk_per_trade": 200.0
    },
    
    # Group 3: High Win Rate Portfolio (MEDIUM PRIORITY)
    "group_3_high_win_rate": {
        "account_name": "Strat 6",
        "account_id": "101-004-30719775-006",
        "strategy_group": "Group 3: High Win Rate Portfolio",
        "instruments": ["EUR_JPY", "USD_CAD"],
        "timeframe": "5m",
        "priority": "MEDIUM - Deploy after Group 2 success",
        "target_sharpe": 38.85,
        "target_win_rate": 82.4,
        "target_annual_return": 113.9,
        "expected_weekly_wins": 88.2,
        "max_drawdown": 0.7,
        "max_concurrent_positions": 3,
        "risk_per_trade": 200.0
    }
}

# Reserved accounts for future expansion or backup
RESERVED_ACCOUNTS = {
    "strat_5": {
        "account_name": "Strat 5",
        "account_id": "101-004-30719775-005",
        "status": "RESERVED - Available for future strategy groups or backup"
    },
    "strat_4": {
        "account_name": "Strat 4", 
        "account_id": "101-004-30719775-004",
        "status": "RESERVED - Available for future strategy groups or backup"
    }
}

# Deployment order (priority sequence)
DEPLOYMENT_ORDER = [
    "group_1_5m_high_frequency",  # Start with highest performing group
    "group_2_15m_zero_drawdown",  # Add zero-drawdown group
    "group_3_high_win_rate"       # Complete with high win rate group
]

def get_account_allocation():
    """Get the complete account allocation configuration"""
    return ACCOUNT_ALLOCATION

def get_deployment_order():
    """Get the deployment order for strategy groups"""
    return DEPLOYMENT_ORDER

def get_reserved_accounts():
    """Get information about reserved accounts"""
    return RESERVED_ACCOUNTS

def get_account_by_id(account_id):
    """Get account configuration by account ID"""
    for group_name, config in ACCOUNT_ALLOCATION.items():
        if config["account_id"] == account_id:
            return config
    
    for account_name, config in RESERVED_ACCOUNTS.items():
        if config["account_id"] == account_id:
            return config
    
    return None

def get_next_deployment_group(current_group=None):
    """Get the next group to deploy based on current deployment status"""
    if current_group is None:
        return DEPLOYMENT_ORDER[0]  # Start with Group 1
    
    try:
        current_index = DEPLOYMENT_ORDER.index(current_group)
        if current_index < len(DEPLOYMENT_ORDER) - 1:
            return DEPLOYMENT_ORDER[current_index + 1]
        else:
            return None  # All groups deployed
    except ValueError:
        return DEPLOYMENT_ORDER[0]  # Start from beginning if invalid group

def print_allocation_summary():
    """Print a summary of the account allocation"""
    print("🏦 ACCOUNT ALLOCATION SUMMARY")
    print("=" * 50)
    print()
    
    print("📊 STRATEGY GROUP ALLOCATIONS:")
    for group_name, config in ACCOUNT_ALLOCATION.items():
        print(f"{config['strategy_group']}:")
        print(f"  • Account: {config['account_name']} ({config['account_id']})")
        print(f"  • Instruments: {config['instruments']}")
        print(f"  • Timeframe: {config['timeframe']}")
        print(f"  • Priority: {config['priority']}")
        print(f"  • Target Sharpe: {config['target_sharpe']}")
        print(f"  • Target Win Rate: {config['target_win_rate']}%")
        print(f"  • Expected Weekly Wins: {config['expected_weekly_wins']}")
        print()
    
    print("📋 RESERVED ACCOUNTS:")
    for account_name, config in RESERVED_ACCOUNTS.items():
        print(f"  • {config['account_name']} ({config['account_id']}): {config['status']}")
    print()
    
    print("🚀 DEPLOYMENT SEQUENCE:")
    for i, group_name in enumerate(DEPLOYMENT_ORDER, 1):
        config = ACCOUNT_ALLOCATION[group_name]
        print(f"  {i}. {config['strategy_group']} → {config['account_name']}")
    print()
    
    print("📈 EXPECTED COMBINED PERFORMANCE:")
    total_weekly_wins = sum(config['expected_weekly_wins'] for config in ACCOUNT_ALLOCATION.values())
    avg_sharpe = sum(config['target_sharpe'] for config in ACCOUNT_ALLOCATION.values()) / len(ACCOUNT_ALLOCATION)
    avg_win_rate = sum(config['target_win_rate'] for config in ACCOUNT_ALLOCATION.values()) / len(ACCOUNT_ALLOCATION)
    
    print(f"  • Total Weekly Wins: {total_weekly_wins}")
    print(f"  • Average Sharpe: {avg_sharpe:.1f}")
    print(f"  • Average Win Rate: {avg_win_rate:.1f}%")
    print(f"  • API Reduction: 50% (3 streams vs 6 individual)")
    print(f"  • Total Risk per Trade: $200 (fixed across all groups)")

if __name__ == "__main__":
    print_allocation_summary()




