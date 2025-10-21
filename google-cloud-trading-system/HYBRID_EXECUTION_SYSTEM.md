# Hybrid Execution System

## Overview

The Hybrid Execution System combines automated trade execution with manual approval workflows, providing flexibility to execute trades based on quality thresholds and user preferences. This system bridges the gap between fully automated trading and manual execution, allowing for automated execution of high-quality setups while requiring human approval for less certain opportunities.

## Key Features

### 1. Multiple Execution Modes

- **Fully Automated**: Execute all trades automatically without human intervention
- **Quality-Based**: Auto-execute high-quality trades, require approval for medium-quality trades
- **Fully Manual**: All trades require manual approval regardless of quality

### 2. Quality-Based Decision Making

- **Configurable Quality Threshold**: Set the minimum quality score for automatic execution
- **Comprehensive Quality Scoring**: Uses the quality scoring system to evaluate trade opportunities
- **Context-Aware Decisions**: Incorporates session quality, news events, and market structure

### 3. Robust Trade Management

- **Position Sizing**: Calculates position size based on account balance and risk per trade
- **Stop Loss and Take Profit**: Sets appropriate SL/TP levels based on market structure
- **Trade Tracking**: Maintains records of open trades and pending approvals

### 4. Telegram Integration

- **Approval Workflow**: Allows trade approval/rejection via Telegram commands
- **Real-Time Notifications**: Sends execution summaries and trade updates
- **Command Processing**: Processes approval commands and executes trades accordingly

### 5. Risk Management

- **Configurable Risk Per Trade**: Set risk as a percentage of account balance
- **Position Tracking**: Monitors open positions and unrealized P&L
- **Trade Updates**: Provides regular updates on open and closed positions

## Implementation Details

### Core Components

1. **HybridExecutionSystem Class**: Main class that handles execution decisions and trade management
2. **ExecutionMode Enum**: Defines the available execution modes
3. **Trade Approver Integration**: Uses the trade approver module for manual approval workflow
4. **OANDA Client Integration**: Executes trades and manages positions
5. **Telegram Notifier Integration**: Sends notifications and processes commands

### Key Methods

- **scan_and_execute()**: Scans for opportunities and executes based on mode
- **_execute_trade()**: Executes trades automatically
- **_request_approval()**: Requests manual approval for trades
- **process_approval_commands()**: Processes approval commands from Telegram
- **update_open_trades()**: Updates and manages open trades

### Data Persistence

- **Open Trades**: Saves open trades to `open_trades.json`
- **Pending Approvals**: Tracks pending approval requests in memory
- **Execution Results**: Logs detailed execution results

## Execution Workflow

### 1. Scan and Execute

1. **Scan for Opportunities**: Uses the morning scanner to find trading opportunities
2. **Evaluate Each Opportunity**: Determines execution path based on mode and quality
3. **Execute or Request Approval**: Either executes trades automatically or requests approval
4. **Send Execution Summary**: Notifies user of execution results

### 2. Process Approval Commands

1. **Check for Commands**: Retrieves pending commands from Telegram
2. **Process Each Command**: Approves or rejects trades based on commands
3. **Execute Approved Trades**: Executes trades that have been approved
4. **Send Command Summary**: Notifies user of command processing results

### 3. Update Open Trades

1. **Load Open Trades**: Loads open trades from file
2. **Get Current Positions**: Retrieves current positions from OANDA
3. **Update Trade Information**: Updates unrealized P&L and current prices
4. **Identify Closed Trades**: Removes trades that have been closed
5. **Send Trade Update**: Notifies user of trade updates

## Usage

### Command Line Interface

```bash
python hybrid_execution_system.py --mode quality_based --threshold 80 --risk 0.01
```

### Options

- `--mode`: Execution mode (fully_automated, quality_based, fully_manual)
- `--threshold`: Quality threshold for automatic execution (0-100)
- `--risk`: Risk per trade as percentage of account balance (0.01 = 1%)

### Python API

```python
from hybrid_execution_system import run_hybrid_system

results = run_hybrid_system(
    mode_str="quality_based",
    auto_threshold=80,
    risk_per_trade=0.01
)
```

## Benefits

1. **Flexibility**: Choose between automated, hybrid, or manual execution
2. **Quality Control**: Only auto-execute trades that meet quality standards
3. **Risk Management**: Consistent position sizing based on risk parameters
4. **Transparency**: Detailed notifications and trade tracking
5. **User Control**: Ability to approve or reject trades via Telegram
6. **Efficiency**: Automate routine tasks while maintaining oversight

## Integration with Other Components

The Hybrid Execution System integrates with:

- **Morning Scanner**: For finding trading opportunities
- **Quality Scoring**: For evaluating trade quality
- **Trade Approver**: For manual approval workflow
- **Session Manager**: For session awareness
- **Historical News Fetcher**: For news event awareness
- **OANDA Client**: For trade execution and position management
- **Telegram Notifier**: For notifications and command processing

This integration creates a comprehensive trading system that combines the best aspects of automated and manual trading.



