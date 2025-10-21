# Enhanced Monte Carlo Optimizer with Contextual Awareness

## Overview

The Enhanced Monte Carlo Optimizer is a significant upgrade to the original optimizer, incorporating session quality and news awareness to find truly optimal parameter combinations for trading strategies. By considering the full market context during optimization, this tool can discover parameter sets that perform well in specific market conditions, leading to more robust and profitable strategies.

## Key Features

### 1. Contextual Awareness

- **Session Quality Filtering**: Optimizes parameters based on trading session quality
- **News Event Avoidance**: Incorporates news filtering to avoid high-impact events
- **Time-of-Day Optimization**: Finds optimal parameters for specific trading hours

### 2. Advanced Optimization

- **Multi-Objective Fitness Function**: Balances trade frequency, quality, and consistency
- **Realistic Parameter Ranges**: Uses carefully calibrated parameter ranges based on real market behavior
- **Comprehensive Testing**: Tests 1000+ parameter combinations against historical data

### 3. Enhanced Configuration Options

- **Session Parameters**:
  - `min_session_quality`: Minimum required session quality (0-100)
  - `only_trade_london_ny`: Whether to trade only during London/NY sessions

- **News Parameters**:
  - `avoid_high_impact_news`: Whether to avoid trading around high-impact news events

### 4. Improved Results Analysis

- **Detailed Reporting**: Comprehensive output of top configurations with all parameters
- **Performance Metrics**: Signals per day, average quality, and fitness scores
- **Result Persistence**: Saves optimization results to JSON files for further analysis

## Implementation Details

### Core Components

1. **ContextualMonteCarloOptimizer Class**: Main class that handles the optimization process
2. **Session Manager Integration**: Provides session quality data for historical timestamps
3. **Historical News Fetcher**: Provides news event data for historical timestamps
4. **Strategy Validator**: Tests parameter combinations against historical data

### Key Methods

- **process_contextual_data()**: Processes timestamps to get session quality and news context
- **optimize()**: Runs the Monte Carlo optimization with contextual awareness
- **_add_contextual_filters()**: Adds contextual filters to strategy for backtest
- **_calculate_fitness()**: Calculates multi-objective fitness score
- **save_results()**: Saves optimization results to file

### Optimization Process

1. **Data Preparation**:
   - Load historical price data
   - Process timestamps for session quality
   - Process timestamps for news events

2. **Parameter Generation**:
   - Generate random parameter combinations
   - Include session and news parameters if enabled

3. **Strategy Testing**:
   - Apply parameters to strategy
   - Add contextual filters to strategy
   - Run backtest with historical data

4. **Fitness Evaluation**:
   - Calculate signals per day
   - Calculate average quality
   - Compute multi-objective fitness score

5. **Result Ranking**:
   - Sort configurations by fitness
   - Return top 10 configurations

## Benefits Over Previous Optimizer

1. **Context-Aware Parameters**: Finds parameters that work well in specific market contexts
2. **Reduced False Positives**: Avoids trading during low-quality sessions or news events
3. **More Realistic Optimization**: Better reflects real-world trading conditions
4. **Flexible Configuration**: Can enable/disable contextual filters as needed
5. **Better Documentation**: Detailed reporting of optimization results
6. **Improved Code Structure**: Object-oriented design for better maintainability

## Usage

### Command Line Interface

```bash
python monte_carlo_optimizer.py --strategy momentum_trading --days 7 --iterations 1000 --session --news --target 5.0
```

### Options

- `--strategy`: Strategy name (default: momentum_trading)
- `--module`: Strategy module (default: src.strategies.momentum_trading)
- `--function`: Strategy function (default: get_momentum_trading_strategy)
- `--days`: Days to look back (default: 7)
- `--iterations`: Number of iterations (default: 1000)
- `--session`: Enable session filtering
- `--news`: Enable news filtering
- `--target`: Target trades per day (default: 5.0)

### Python API

```python
from monte_carlo_optimizer import ContextualMonteCarloOptimizer

# Create optimizer
optimizer = ContextualMonteCarloOptimizer(
    strategy_name="momentum_trading",
    strategy_module="src.strategies.momentum_trading",
    strategy_function="get_momentum_trading_strategy",
    instruments=instruments,
    historical_data=historical_data,
    lookback_days=7
)

# Run optimization
top_configs = optimizer.optimize(
    iterations=1000,
    session_filter=True,
    news_filter=True,
    target_trades_per_day=5.0
)

# Save results
optimizer.save_results(top_configs)
```

## Integration with Other Components

The Enhanced Monte Carlo Optimizer integrates with:

- **Session Manager**: For trading session awareness
- **Historical News Fetcher**: For news event awareness
- **Strategy Validator**: For backtesting parameter combinations
- **Historical Fetcher**: For retrieving historical price data

This integration creates a powerful optimization tool that considers the full market context when finding optimal parameters for trading strategies.



