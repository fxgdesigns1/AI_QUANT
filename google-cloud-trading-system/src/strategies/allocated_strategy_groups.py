"""
ALLOCATED STRATEGY GROUPS
Integrates the 3 optimized strategy groups with allocated demo accounts
Uses existing accounts: Strat 8, Strat 7, Strat 6
"""

import logging
from typing import Dict, Any
from datetime import datetime

try:
    from .group_1_5m_high_frequency import get_group_1_strategy
    from .group_2_15m_zero_drawdown import get_group_2_strategy  
    from .group_3_high_win_rate import get_group_3_strategy
except ImportError:
    from group_1_5m_high_frequency import get_group_1_strategy
    from group_2_15m_zero_drawdown import get_group_2_strategy  
    from group_3_high_win_rate import get_group_3_strategy

logger = logging.getLogger(__name__)

# Account allocation mapping
ACCOUNT_ALLOCATION = {
    "group_1": {
        "account_name": "Strat 8",
        "account_id": "101-004-30719775-008",
        "strategy_group": "Group 1: 5-Minute High-Frequency Portfolio",
        "priority": "HIGHEST"
    },
    "group_2": {
        "account_name": "Strat 7", 
        "account_id": "101-004-30719775-007",
        "strategy_group": "Group 2: 15-Minute Zero-Drawdown Portfolio",
        "priority": "HIGH"
    },
    "group_3": {
        "account_name": "Strat 6",
        "account_id": "101-004-30719775-006", 
        "strategy_group": "Group 3: High Win Rate Portfolio",
        "priority": "MEDIUM"
    }
}

def get_allocated_strategy_groups() -> Dict[str, Any]:
    """Get all strategy groups with their allocated accounts"""
    
    # Get the base strategy groups
    group_1_strategy = get_group_1_strategy()
    group_2_strategy = get_group_2_strategy()
    group_3_strategy = get_group_3_strategy()
    
    # Add account allocation to each group
    allocated_groups = {
        "group_1": {
            "strategy": group_1_strategy,
            "account": ACCOUNT_ALLOCATION["group_1"],
            "status": "ready_for_deployment"
        },
        "group_2": {
            "strategy": group_2_strategy,
            "account": ACCOUNT_ALLOCATION["group_2"],
            "status": "pending_group_1_success"
        },
        "group_3": {
            "strategy": group_3_strategy,
            "account": ACCOUNT_ALLOCATION["group_3"],
            "status": "pending_group_2_success"
        }
    }
    
    logger.info("✅ Allocated strategy groups initialized")
    logger.info(f"📊 Group 1 → {ACCOUNT_ALLOCATION['group_1']['account_name']} ({ACCOUNT_ALLOCATION['group_1']['account_id']})")
    logger.info(f"📊 Group 2 → {ACCOUNT_ALLOCATION['group_2']['account_name']} ({ACCOUNT_ALLOCATION['group_2']['account_id']})")
    logger.info(f"📊 Group 3 → {ACCOUNT_ALLOCATION['group_3']['account_name']} ({ACCOUNT_ALLOCATION['group_3']['account_id']})")
    
    return allocated_groups

def get_deployment_sequence() -> list:
    """Get the deployment sequence with account information"""
    
    allocated_groups = get_allocated_strategy_groups()
    
    deployment_sequence = [
        {
            "phase": 1,
            "group_name": "group_1",
            "strategy_name": "5-Minute High-Frequency Portfolio",
            "account_name": allocated_groups["group_1"]["account"]["account_name"],
            "account_id": allocated_groups["group_1"]["account"]["account_id"],
            "instruments": allocated_groups["group_1"]["strategy"].instruments,
            "timeframe": allocated_groups["group_1"]["strategy"].timeframe,
            "priority": "HIGHEST",
            "status": "ready_for_deployment"
        },
        {
            "phase": 2,
            "group_name": "group_2", 
            "strategy_name": "15-Minute Zero-Drawdown Portfolio",
            "account_name": allocated_groups["group_2"]["account"]["account_name"],
            "account_id": allocated_groups["group_2"]["account"]["account_id"],
            "instruments": allocated_groups["group_2"]["strategy"].instruments,
            "timeframe": allocated_groups["group_2"]["strategy"].timeframe,
            "priority": "HIGH",
            "status": "pending_group_1_success"
        },
        {
            "phase": 3,
            "group_name": "group_3",
            "strategy_name": "High Win Rate Portfolio", 
            "account_name": allocated_groups["group_3"]["account"]["account_name"],
            "account_id": allocated_groups["group_3"]["account"]["account_id"],
            "instruments": allocated_groups["group_3"]["strategy"].instruments,
            "timeframe": allocated_groups["group_3"]["strategy"].timeframe,
            "priority": "MEDIUM",
            "status": "pending_group_2_success"
        }
    ]
    
    return deployment_sequence

def get_account_instruments_mapping() -> Dict[str, list]:
    """Get mapping of account IDs to their instruments"""
    
    allocated_groups = get_allocated_strategy_groups()
    
    account_instruments = {}
    for group_name, group_data in allocated_groups.items():
        account_id = group_data["account"]["account_id"]
        instruments = group_data["strategy"].instruments
        account_instruments[account_id] = instruments
    
    return account_instruments

def get_next_deployment_step(current_phase: int = 0) -> Dict[str, Any]:
    """Get the next deployment step based on current phase"""
    
    deployment_sequence = get_deployment_sequence()
    
    if current_phase < len(deployment_sequence):
        next_step = deployment_sequence[current_phase]
        
        logger.info(f"🚀 Next deployment step: Phase {next_step['phase']}")
        logger.info(f"📊 Strategy: {next_step['strategy_name']}")
        logger.info(f"🏦 Account: {next_step['account_name']} ({next_step['account_id']})")
        logger.info(f"📈 Instruments: {next_step['instruments']}")
        logger.info(f"⏰ Timeframe: {next_step['timeframe']}")
        
        return next_step
    else:
        logger.info("✅ All phases completed - full portfolio deployed")
        return None

def print_deployment_plan():
    """Print the complete deployment plan with account allocation"""
    
    deployment_sequence = get_deployment_sequence()
    account_instruments = get_account_instruments_mapping()
    
    print("🚀 DEPLOYMENT PLAN WITH ACCOUNT ALLOCATION")
    print("=" * 60)
    print()
    
    for step in deployment_sequence:
        print(f"Phase {step['phase']}: {step['strategy_name']}")
        print(f"  🏦 Account: {step['account_name']} ({step['account_id']})")
        print(f"  📊 Instruments: {step['instruments']}")
        print(f"  ⏰ Timeframe: {step['timeframe']}")
        print(f"  🎯 Priority: {step['priority']}")
        print(f"  📋 Status: {step['status']}")
        print()
    
    print("📈 COMBINED PORTFOLIO SUMMARY:")
    print(f"  • Total Accounts Used: 3")
    print(f"  • Total Instruments: 5 (GBP_USD, NZD_USD, XAU_USD, EUR_JPY, USD_CAD)")
    print(f"  • API Streams: 3 (50% reduction)")
    print(f"  • Expected Weekly Wins: 264.5")
    print(f"  • Combined Win Rate: 71.9%")
    print(f"  • Risk per Trade: $200 (fixed)")
    print()
    
    print("🏦 ACCOUNT INSTRUMENT MAPPING:")
    for account_id, instruments in account_instruments.items():
        print(f"  • {account_id}: {instruments}")

if __name__ == "__main__":
    print_deployment_plan()
