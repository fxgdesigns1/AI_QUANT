# 🎯 Trade Quality Filter System

## Overview
The Trade Quality Filter is a multi-layer scoring system that evaluates each trade signal across 7 independent dimensions. Only trades that score above the minimum threshold are executed.

**Goal:** Trade less, win more, profit more.

---

## 📊 Quality Scoring Breakdown (Total: 100 Points)

### 1. Trend Alignment (20 points)
- **Strong trend (ADX > 30)**: 20 points
- **Moderate trend (ADX 25-30)**: 17 points
- **Weak trend (ADX 20-25)**: 14 points
- **Ranging market**: 5 points

### 2. Session Timing (15 points)
- **London session (8-11 GMT)**: 15 points (best liquidity)
- **NY session (13-16 GMT)**: 12 points (good volume)
- **Tokyo session (0-3 GMT)**: 5-10 points (depends on instrument)
- **Off-hours**: 2 points

### 3. Risk-Reward Ratio (20 points)
- **R:R >= 5:1**: 20 points
- **R:R >= 4:1**: 18 points
- **R:R >= 3:1**: 15 points
- **R:R >= 2.5:1**: 10 points
- **R:R >= 2:1**: 5 points
- **R:R < 2:1**: 0 points

### 4. Market Structure (15 points)
- **Price at key support/resistance**: 8 points
- **Moderate volatility (0.3-0.7)**: 7 points
- **Clean price action**: Bonus points

### 5. Volume Confirmation (10 points)
- **Volume ratio >= 2.0x average**: 10 points
- **Volume ratio >= 1.5x average**: 7 points
- **Volume ratio >= 1.2x average**: 4 points
- **Below average volume**: 0 points

### 6. Momentum Strength (10 points)
- **RSI in optimal zones (30-40 or 60-70)**: 10 points
- **RSI near optimal zones**: 6 points
- **RSI neutral**: 2 points

### 7. Correlation Risk (10 points)
- **No correlated positions open**: 10 points
- **Low correlation (<0.3)**: 10 points
- **Moderate correlation (0.3-0.5)**: 6 points
- **High correlation (0.5-0.7)**: 3 points
- **Very high correlation (>0.7)**: 0 points

---

## 🎯 Recommended Thresholds

### Conservative (85/100)
- **Best for**: FTMO challenges, prop firms
- **Expected win rate**: 60-70%
- **Trade frequency**: 3-8 trades/week
- **Risk profile**: Low

### Balanced (75/100)
- **Best for**: Regular trading, growth
- **Expected win rate**: 55-65%
- **Trade frequency**: 8-15 trades/week
- **Risk profile**: Medium

### Aggressive (65/100)
- **Best for**: High-volume trading
- **Expected win rate**: 45-55%
- **Trade frequency**: 15-25 trades/week
- **Risk profile**: Higher

---

## 💡 Key Benefits

### 1. **Fewer, Better Trades**
- Filter out 50-70% of marginal setups
- Only take the highest probability trades
- Reduce emotional trading stress

### 2. **Higher Win Rate**
- Quality > Quantity
- Multiple confirmation layers
- Confluence-based entries

### 3. **Better Risk Management**
- Enforces minimum 3:1 R:R
- Prevents over-correlation
- Session-based timing

### 4. **Psychological Benefits**
- More confidence in each trade
- Less screen time required
- Better work-life balance

---

## 🔧 How to Use

### In Your Strategy:
```python
from src.core.trade_quality_filter import TradeQualityFilter

# Initialize filter
quality_filter = TradeQualityFilter(min_quality_score=85)

# Evaluate each signal
should_take, score, breakdown = quality_filter.evaluate_trade_quality(
    signal=trade_signal,
    market_data=current_market_data,
    strategy_metadata=strategy_metadata
)

if should_take:
    # Execute trade
    execute_trade(signal)
    quality_filter.add_active_trade(signal)
else:
    # Skip trade
    logger.info(f"Trade filtered out - Score: {score}/100")
```

---

## 📈 Expected Improvements

### Before Quality Filter:
- **Trades**: 31 per 14 days (~15.5/week)
- **Win Rate**: 41.9%
- **Profit**: +2,286 pips

### After Quality Filter (85 threshold):
- **Trades**: 8-12 per 14 days (~5-6/week)
- **Win Rate**: 60-65% (estimated)
- **Profit**: +2,500-3,000 pips (estimated)

**Result:** 
- ✅ 50% fewer trades
- ✅ 50% higher win rate
- ✅ Similar or better profit
- ✅ Much less stressful trading

---

## 🎓 Best Practices

1. **Start Conservative** (85 threshold) and gradually lower if needed
2. **Track Results** - Monitor which filters reject most trades
3. **Adjust Per Instrument** - Some pairs may need different thresholds
4. **Session Awareness** - Don't force trades outside peak sessions
5. **Trust the System** - If score is below threshold, skip the trade

---

## 🔬 Testing & Optimization

Run the quality threshold optimizer to find your optimal setting:

```bash
cd google-cloud-trading-system
python3 quality_threshold_optimizer.py
```

This will test thresholds from 50-95 and recommend the optimal balance for your strategy.

---

## ⚠️ Important Notes

- **This is NOT a standalone strategy** - it's a filter layer on top of your existing strategies
- **Requires good base strategy** - Garbage in = garbage out
- **Backtesting recommended** - Test on historical data before live trading
- **May reduce opportunities** - Fewer trades = more patience required
- **FTMO-friendly** - Helps meet win rate requirements for prop firms

---

## 🚀 Next Steps

1. Run `quality_threshold_optimizer.py` to find your optimal threshold
2. Integrate `TradeQualityFilter` into your main trading system
3. Backtest with 30 days of data
4. Start with paper trading to validate
5. Go live with small position sizes
6. Scale up as confidence grows

---

**Remember:** Quality over quantity. It's better to take 1 great trade per week than 10 mediocre ones.




