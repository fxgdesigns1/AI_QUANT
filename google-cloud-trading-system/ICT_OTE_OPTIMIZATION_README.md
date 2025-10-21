# ICT OTE Strategy Optimization System

A comprehensive optimization system for ICT (Inner Circle Trader) Optimal Trade Entry (OTE) strategy with backtesting and Monte Carlo simulation.

## 🚀 Features

- **Parameter Optimization**: Grid search and random search optimization
- **Comprehensive Backtesting**: Detailed historical performance analysis
- **Monte Carlo Simulation**: Robustness testing with 1000+ simulations
- **Risk Assessment**: Complete risk profile analysis
- **Performance Metrics**: Sharpe ratio, Sortino ratio, Calmar ratio, and more
- **Visualizations**: Charts and graphs for analysis
- **Comprehensive Reporting**: Detailed optimization reports

## 📋 Requirements

Install the required dependencies:

```bash
pip install -r requirements_ict_ote.txt
```

## 🔧 Quick Start

### 1. Test the System

First, run the test script to ensure everything is working:

```bash
python test_ict_ote_system.py
```

### 2. Run Optimization

Run the comprehensive optimization:

```bash
python run_ict_ote_optimization.py
```

### 3. Individual Components

You can also run individual components:

```bash
# Parameter optimization only
python ict_ote_optimizer.py

# Backtesting only
python ict_ote_backtester.py

# Monte Carlo simulation only
python ict_ote_monte_carlo.py
```

## 📊 Configuration

### Instruments
The system is configured to optimize on these instruments:
- XAU_USD (Gold)
- EUR_USD
- GBP_USD
- USD_JPY
- AUD_USD
- USD_CAD

### Time Period
- Default: Last 90 days
- Configurable in the scripts

### Risk Parameters
- Initial Balance: $10,000
- Risk per Trade: 2%
- Max Positions: 3
- Max Trades per Day: 20

## 🎯 ICT OTE Strategy Parameters

The system optimizes these key parameters:

- **OTE Retracement Range**: 50%-79% (Optimal Trade Entry zone)
- **Fair Value Gap Size**: Minimum gap size for FVG detection
- **Order Block Lookback**: Number of candles to look back for order blocks
- **Stop Loss ATR**: ATR multiplier for stop loss
- **Take Profit ATR**: ATR multiplier for take profit
- **Quality Thresholds**: Minimum strength requirements for signals

## 📈 Performance Metrics

The system calculates comprehensive performance metrics:

### Return Metrics
- Total Return
- Annualized Return
- Mean Return (Monte Carlo)

### Risk Metrics
- Maximum Drawdown
- Value at Risk (VaR)
- Conditional VaR
- Probability of Ruin

### Risk-Adjusted Returns
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Recovery Factor

### Consistency Metrics
- Win Rate
- Profit Factor
- Average Win/Loss
- Consecutive Wins/Losses

## 🎲 Monte Carlo Simulation

The Monte Carlo simulation provides:

- **1000+ Simulations**: Robust statistical analysis
- **Confidence Intervals**: 5%, 25%, 50%, 75%, 95% percentiles
- **Risk Assessment**: Probability of profit/loss/ruin
- **Drawdown Analysis**: Maximum drawdown statistics
- **Consecutive Loss Analysis**: Streak analysis

## 📊 Visualizations

The system generates several visualizations:

1. **Returns Distribution**: Histogram of simulation returns
2. **Drawdown Distribution**: Histogram of maximum drawdowns
3. **Equity Curves**: Sample equity curves and mean curve
4. **Risk-Return Scatter**: Risk vs return scatter plot

## 📋 Output Files

The system generates several output files:

- `ict_ote_comprehensive_optimization_YYYYMMDD_HHMMSS.json`: Complete results
- `ict_ote_plots/`: Directory with visualization files
- Console output with detailed reports

## 🔍 Understanding the Results

### Final Score (0-100)
- **90-100**: Excellent strategy, ready for live trading
- **80-89**: Very good strategy, minor improvements needed
- **70-79**: Good strategy, some optimization recommended
- **60-69**: Acceptable strategy, significant improvements needed
- **Below 60**: Poor strategy, major overhaul required

### Risk Levels
- **Low**: Probability of ruin <5%, drawdown <15%
- **Medium**: Probability of ruin 5-15%, drawdown 15-25%
- **High**: Probability of ruin >15%, drawdown >25%

### Recommendations
The system provides specific recommendations based on:
- Performance metrics
- Risk assessment
- Monte Carlo results
- Consistency analysis

## 🚨 Important Notes

1. **Paper Trading First**: Always test optimized parameters in paper trading
2. **Risk Management**: Implement recommended risk controls
3. **Regular Review**: Monitor performance and adjust parameters
4. **Market Conditions**: Strategy performance may vary with market conditions
5. **Position Sizing**: Use Kelly percentage for optimal position sizing

## 🔧 Customization

### Adding New Instruments
Edit the `instruments` list in the configuration:

```python
instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
```

### Adjusting Time Period
Modify the `start_date` and `end_date`:

```python
start_date=datetime.now() - timedelta(days=180),  # 6 months
end_date=datetime.now()
```

### Changing Risk Parameters
Adjust risk settings:

```python
risk_per_trade=0.01,  # 1% risk per trade
max_positions=5,      # 5 concurrent positions
max_trades_per_day=30 # 30 trades per day
```

## 📞 Support

For issues or questions:
1. Check the console output for error messages
2. Review the generated log files
3. Ensure all dependencies are installed
4. Verify API credentials are correct

## 🎯 Next Steps

After optimization:

1. **Paper Trading**: Test for 1-2 weeks
2. **Live Trading**: Start with small position sizes
3. **Monitoring**: Track performance closely
4. **Adjustment**: Fine-tune parameters as needed
5. **Scaling**: Increase position sizes gradually

## 📚 Additional Resources

- ICT (Inner Circle Trader) concepts
- Optimal Trade Entry (OTE) methodology
- Order Blocks and Fair Value Gaps
- Market Structure analysis
- Risk management principles

---

**Disclaimer**: This system is for educational and research purposes. Past performance does not guarantee future results. Always use proper risk management and never risk more than you can afford to lose.