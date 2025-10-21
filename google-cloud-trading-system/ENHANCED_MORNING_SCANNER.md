# Enhanced Morning Scanner with Contextual Analysis

## Overview

The Enhanced Morning Scanner is a significant upgrade to the original scanner, integrating all the contextual modules developed for the trading system. This scanner runs at 8:00 AM London time (or on demand) and identifies high-quality trading opportunities using a comprehensive market context analysis.

## Key Features

### 1. Multi-Timeframe Analysis

- **Data Collection**: Fetches data for 5 timeframes (M5, M15, H1, H4, D1)
- **Trend Analysis**: Analyzes trend direction and strength across all timeframes
- **Alignment Detection**: Identifies setups where multiple timeframes are aligned

### 2. Session Awareness

- **Session Quality**: Scores the current trading session (0-100)
- **Session Description**: Provides human-readable session information
- **Prime Time Detection**: Identifies if current time is optimal for trading
- **Next Session Info**: Shows when the next prime trading session begins

### 3. News Integration

- **Recent News Impact**: Analyzes recent economic news events
- **Upcoming News Warning**: Warns about high-impact news events coming up
- **News Sentiment**: Provides sentiment analysis of recent news

### 4. Price Context Analysis

- **Key Level Detection**: Identifies important support and resistance levels
- **Pattern Recognition**: Detects chart patterns and candlestick formations
- **Smart Stop Loss/Take Profit**: Places SL/TP at key levels when available

### 5. Comprehensive Quality Scoring

- **Multiple Factors**: Scores trades based on 10+ quality factors
- **Detailed Breakdown**: Shows contribution of each factor to the final score
- **Adaptive Thresholds**: Adjusts quality requirements based on market conditions
- **Explanations**: Provides human-readable explanations of quality assessment

### 6. Enhanced Position Sizing

- **Risk-Based Sizing**: Calculates position size based on account balance and risk
- **Instrument-Specific Adjustments**: Handles Gold and forex pairs differently
- **Clear Risk/Reward**: Shows exact dollar amounts for risk and potential reward

## Workflow

1. **Initialization**:
   - Loads credentials and initializes all contextual modules
   - Connects to OANDA API and gets account information

2. **Data Collection**:
   - Fetches multi-timeframe data for all instruments
   - Retrieves current session information
   - Gets news context for each instrument

3. **Analysis Process** (for each instrument):
   - Analyzes price context across all timeframes
   - Checks for high-impact news (skips if found)
   - Calculates momentum and ADX indicators
   - Determines trade direction based on multi-timeframe context
   - Places stop loss and take profit at key levels when available
   - Scores trade quality using the comprehensive scoring system
   - Calculates position size based on risk parameters

4. **Filtering and Ranking**:
   - Filters out low-quality setups (below 60/100)
   - Ranks remaining opportunities by quality score

5. **Notification**:
   - Sends detailed Telegram notification with top opportunities
   - Includes contextual information for each setup
   - Provides clear execution instructions
   - Shows quality analysis explanation

6. **Persistence**:
   - Saves all opportunities to JSON file for reference

## Benefits Over Previous Scanner

1. **Higher Quality Signals**: More comprehensive filtering reduces false positives
2. **Contextual Awareness**: Trading decisions based on complete market context
3. **Smart Level Detection**: Places SL/TP at key market levels for better R:R
4. **Detailed Quality Analysis**: Explains why a setup is considered good or bad
5. **News Avoidance**: Prevents trading during high-risk news events
6. **Session Optimization**: Provides session quality information for better timing
7. **Error Handling**: Robust error handling with Telegram notifications
8. **Enhanced Documentation**: Saves detailed trade context for later analysis

## Usage

Run the scanner at the beginning of the trading day or on demand:

```bash
python morning_scanner.py
```

The scanner will:
1. Analyze all instruments
2. Find high-quality opportunities
3. Send a detailed Telegram notification
4. Save results to `latest_opportunities.json`

## Integration with Other Components

The Enhanced Morning Scanner integrates with:

- **Session Manager**: For trading session awareness
- **Price Context Analyzer**: For multi-timeframe and key level analysis
- **Quality Scoring**: For comprehensive trade quality assessment
- **Historical News Fetcher**: For news-aware trading decisions
- **Telegram Notifier**: For detailed mobile notifications
- **OANDA Client**: For market data and account information

This integration creates a powerful, context-aware scanner that significantly improves the quality of trading signals and provides detailed information to support trading decisions.



