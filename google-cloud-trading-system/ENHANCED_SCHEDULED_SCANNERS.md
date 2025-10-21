# Enhanced Scheduled Scanners with Contextual Reports

## Overview

The Enhanced Scheduled Scanners system provides comprehensive market context reports at key times throughout the trading day. This system leverages all the contextual modules to deliver rich, informative reports via Telegram, helping traders make better-informed decisions based on session quality, market conditions, news events, and technical analysis.

## Key Features

### 1. Comprehensive Session-Based Schedule

- **Pre-Market Briefing (6:00 AM London)**: Morning preparation with key levels and economic events
- **Morning Scan (8:00 AM London)**: London open scanner with detailed trade opportunities
- **Peak Scan (1:00 PM London)**: London/NY overlap scanner during maximum liquidity
- **EOD Summary (5:00 PM London)**: End-of-day review with account performance
- **Asian Preview (9:00 PM London)**: Overnight session preview with key levels
- **Continuous Monitor (Every 15 min)**: Real-time alerts for significant price movements

### 2. Rich Contextual Information

Each report includes relevant contextual information:

- **Session Context**: Current trading session, quality score, and liquidity expectations
- **Market Structure**: Key support/resistance levels and overall trend direction
- **Economic Calendar**: Upcoming high-impact news events that may affect trading
- **Account Status**: Current balance, open positions, and unrealized P&L
- **Performance Metrics**: Daily performance and position status

### 3. Intelligent Market Analysis

- **Key Level Detection**: Automatically identifies important support/resistance levels
- **Trend Analysis**: Determines overall market bias across instruments
- **Significant Move Detection**: Alerts for unusual price movements (>0.3% in 15 minutes)
- **Multi-Instrument Coverage**: Tracks major forex pairs and gold simultaneously

### 4. Persistent Data Storage

- **Historical Record**: Saves scan results to JSON files with timestamps
- **Price Tracking**: Maintains record of previous prices for move comparison
- **Performance Logging**: Comprehensive logging of all operations

## Detailed Function Descriptions

### 1. Pre-Market Briefing

**Purpose**: Prepare traders for the day ahead before London open

**Content**:
- Current session status and quality
- Economic calendar events for the day
- Key support/resistance levels for all instruments
- Overall market bias (bullish/bearish/mixed)
- Expected volatility based on session quality
- Schedule for the day's upcoming reports

### 2. Morning Scan

**Purpose**: Identify trading opportunities at London open

**Content**:
- Detailed trade setups with entry, stop loss, and take profit levels
- Multi-timeframe trend analysis for each opportunity
- Quality scoring with factor breakdown
- Risk/reward analysis and position sizing
- News context and session quality considerations

### 3. Peak Scan

**Purpose**: Identify prime opportunities during maximum liquidity period

**Content**:
- Current session status with prime time indicator
- Account summary with open positions
- Unrealized profit/loss for all positions
- New trading opportunities with detailed context
- Next scheduled report information

### 4. EOD Summary

**Purpose**: Review the day's performance and prepare for tomorrow

**Content**:
- Account balance and performance metrics
- Open position status and unrealized P&L
- Daily price performance for all instruments
- Tomorrow's key economic events
- Trading session status and position management recommendations

### 5. Asian Preview

**Purpose**: Prepare for overnight trading and next day

**Content**:
- Asian session status and quality expectations
- Key levels for Asian-relevant pairs (JPY, AUD, NZD)
- Account status and open position management
- Liquidity expectations and trading recommendations
- Next scheduled report information

### 6. Continuous Monitor

**Purpose**: Alert traders to significant market movements in real-time

**Content**:
- Significant price movements (>0.3% in 15 minutes)
- Direction and magnitude of price changes
- Current session context
- Potential trading opportunity notifications

## Implementation Details

### Core Components

1. **Session Manager Integration**: Provides timezone-aware session information
2. **Price Context Analyzer**: Identifies key levels and market structure
3. **Historical News Fetcher**: Retrieves economic calendar events
4. **OANDA Client**: Fetches market data and account information
5. **Telegram Notifier**: Delivers formatted reports to mobile devices

### Helper Functions

- `get_key_levels_for_instruments()`: Analyzes price data to find support/resistance
- `get_economic_calendar()`: Retrieves and formats economic events
- `get_account_summary()`: Fetches and formats account and position information

### Data Persistence

- Morning and peak scan results saved as JSON files with timestamps
- Previous prices saved between continuous monitor runs
- Comprehensive logging of all operations

## Benefits Over Previous System

1. **Richer Context**: Includes session quality, news events, and market structure
2. **More Frequent Updates**: Six different report types throughout the day
3. **Intelligent Alerts**: Notifies only on significant market movements
4. **Account Integration**: Shows real-time position status and performance
5. **Enhanced Formatting**: Better organized reports with emojis and clear sections
6. **Data Persistence**: Maintains historical record of scans and price movements

## Usage

The scheduled scanners are designed to be called by Google Cloud cron jobs as defined in `cron.yaml`. Each function can also be called manually for on-demand reports:

```python
from scheduled_scanners import pre_market_briefing, morning_scan, peak_scan, eod_summary, asian_preview, continuous_monitor

# Run a specific scanner
pre_market_briefing()
```

For testing all scanners at once:

```bash
python scheduled_scanners.py
```

## Integration with Other Components

The Enhanced Scheduled Scanners integrate with:

- **Morning Scanner**: Uses the enhanced morning scanner for trade opportunities
- **Session Manager**: For trading session awareness
- **Price Context Analyzer**: For key level detection and trend analysis
- **Historical News Fetcher**: For economic calendar events
- **OANDA Client**: For market data and account information
- **Telegram Notifier**: For mobile notifications

This integration creates a comprehensive trading assistant that provides valuable context and insights throughout the trading day.



