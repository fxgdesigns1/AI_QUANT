<!-- 34338c6a-b17f-4bdd-82ae-c786438fb6bf d0722757-7af0-4a7a-9b0a-5116aa832c1a -->
# Build Complete Contextual Trading System

## Current System Analysis

The current system has several components that need to be integrated more effectively:

1. **Market Regime Detection** (`market_regime.py`) - Detects trending/ranging/choppy markets
2. **News Integration** (`news_integration.py`) - Fetches financial news and calculates sentiment
3. **Morning Scanner** (`morning_scanner.py`) - Scans for opportunities at specific times
4. **Scheduled Scanners** (`scheduled_scanners.py`) - Cron-based scanning at optimal times

However, these components are not fully leveraging each other, and the backtesting system doesn't accurately reflect live market conditions.

## Implementation Plan

### 1. Create Session-Aware Backtesting

We need a backtesting system that respects market sessions and doesn't generate signals during off-hours:

- Create a `session_manager.py` to track active trading sessions (London/NY/Asia)
- Implement proper datetime handling in backtests (using historical timestamps, not `datetime.now()`)
- Add session filters to all strategy backtests

### 2. Integrate News Events into Backtesting

Currently, news is only available in live trading but not in backtests:

- Create a `historical_news_fetcher.py` to download and cache past news events
- Implement a news calendar system for major economic releases
- Add news impact scoring to backtests (simulating how news would have affected signals)

### 3. Build Multi-Timeframe Context

The system needs to understand price action context across timeframes:

- Create a `price_context_analyzer.py` to detect key levels, patterns, and structures
- Implement support/resistance detection that works in both live and backtest
- Add multi-timeframe momentum alignment checks

### 4. Create Realistic Quality Scoring

Develop a comprehensive quality scoring system that considers all contextual factors:

- Create a `quality_scoring.py` module that assigns 0-100 scores based on multiple factors
- Include session quality, news alignment, trend strength, and pattern quality
- Add probability estimates based on historical pattern performance

### 5. Develop Hybrid Execution System

Build a system that can operate in both fully automated and human-approval modes:

- Create a `trade_approver.py` module for manual trade approval via Telegram
- Implement a scoring threshold system that auto-executes only the highest quality trades
- Add detailed trade context information to Telegram alerts

## Key Files to Create/Modify

1. **New File: `src/core/session_manager.py`**

- Track active trading sessions (London/NY/Asia)
- Provide session quality scores
- Handle timezone conversions properly

2. **New File: `src/core/historical_news_fetcher.py`**

- Download and cache historical news
- Provide news context for backtests
- Track economic calendar events

3. **New File: `src/core/price_context_analyzer.py`**

- Detect key price levels and patterns
- Analyze multi-timeframe context
- Identify high-probability reversal and continuation zones

4. **New File: `src/core/quality_scoring.py`**

- Comprehensive trade quality scoring (0-100)
- Multiple factor analysis
- Historical win rate tracking per pattern

5. **New File: `src/core/trade_approver.py`**

- Telegram-based trade approval system
- Detailed context information for decision making
- Hybrid auto/manual execution

6. **Modify: `monte_carlo_optimizer.py`**

- Update to include session awareness
- Add news impact simulation
- Incorporate quality scoring in optimization

7. **Modify: `morning_scanner.py`**

- Enhance with multi-timeframe analysis
- Add detailed quality scoring
- Include price action pattern detection

8. **Modify: `scheduled_scanners.py`**

- Add comprehensive market context to reports
- Include key level information
- Add news impact analysis

## Implementation Steps

1. First, build the core infrastructure modules:

- Session manager
- Historical news fetcher
- Price context analyzer
- Quality scoring system

2. Then integrate these modules into the existing system:

- Update strategy classes to use the new context modules
- Modify backtesting to include all contextual factors
- Enhance Telegram notifications with detailed context

3. Finally, create the hybrid execution system:

- Implement trade approval workflow
- Create detailed context reports for manual decisions
- Build auto-execution for highest quality setups

## Expected Outcomes

1. **More Realistic Backtests**: Backtests will accurately reflect live market conditions
2. **Higher Win Rate**: Quality filtering will improve win rate to 60-70%
3. **Better Context**: Traders will have complete market context for decisions
4. **Flexible Execution**: System can run fully automated or with manual approval
5. **Continuous Improvement**: System will learn from historical pattern performance

### To-dos

- [ ] Create universal Monte Carlo optimizer framework that works with any strategy class and parameter ranges
- [ ] Optimize momentum_trading (Trump DNA) for ALL pairs (not just Gold), verify against past week, document results
- [ ] Optimize champion_75wr strategy, verify against past week, document results with trade-by-trade breakdown
- [ ] Optimize gold_scalping strategy, verify against past week, document results
- [ ] Optimize all three gbp_usd_5m strategies (rank 1, 2, 3), ensure each has unique parameters, verify and document
- [ ] Optimize ultra_strict_forex and ultra_strict_v2, verify against past week, document results
- [ ] Optimize momentum_v2 and all_weather_70wr, verify against past week, document results
- [ ] Implement all optimized parameters into respective strategy files with documentation
- [ ] Test all dashboards (strategy switcher, performance metrics) work with optimized strategies
- [ ] Deploy to Google Cloud, migrate traffic, monitor for 30 mins, verify signals and Telegram alerts
- [ ] Create comprehensive summary showing all 10 strategies' optimized parameters, past week performance, and current signals