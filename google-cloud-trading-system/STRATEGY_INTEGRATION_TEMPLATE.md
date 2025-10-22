# Strategy Integration Template for Learning System

This template shows how to integrate the learning system into any strategy.
Use `momentum_trading.py` as the reference implementation.

---

## Step 1: Add Imports (at top of file)

Add this block after existing imports:

```python
# Learning & Honesty System (NEW OCT 21, 2025)
try:
    from ..core.loss_learner import get_loss_learner
    from ..core.early_trend_detector import get_early_trend_detector
    from ..core.honesty_reporter import get_honesty_reporter
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("⚠️ Learning system not available")
```

---

## Step 2: Initialize in `__init__` Method

Add this block in the `__init__` method, after other initializations:

```python
# ===============================================
# LEARNING & HONESTY SYSTEM (NEW OCT 21, 2025)
# ===============================================
self.learning_enabled = False
if LEARNING_AVAILABLE:
    try:
        self.loss_learner = get_loss_learner(strategy_name=self.name)
        self.early_trend = get_early_trend_detector()
        self.honesty = get_honesty_reporter(strategy_name=self.name)
        self.learning_enabled = True
        logger.info("✅ Loss learning ENABLED - Learns from mistakes")
        logger.info("✅ Early trend detection ENABLED - Catches moves early")
        logger.info("✅ Brutal honesty reporting ENABLED - No sugar-coating")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize learning system: {e}")
        self.loss_learner = None
        self.early_trend = None
        self.honesty = None
else:
    self.loss_learner = None
    self.early_trend = None
    self.honesty = None
```

---

## Step 3: Add Trade Result Recording Method

Add these methods to the strategy class:

```python
def record_trade_result(self, trade_info: Dict, result: str, pnl: float):
    """
    Record trade result for learning system (NEW OCT 21, 2025)
    
    Args:
        trade_info: Dict with trade details (instrument, regime, adx, momentum, etc.)
        result: 'WIN' or 'LOSS'
        pnl: Profit/loss amount
    """
    if not self.learning_enabled or not self.loss_learner:
        return
    
    if result == 'LOSS':
        # Record loss for learning
        self.loss_learner.record_loss(
            instrument=trade_info.get('instrument', 'UNKNOWN'),
            regime=trade_info.get('regime', 'UNKNOWN'),
            adx=trade_info.get('adx', 0.0),
            momentum=trade_info.get('momentum', 0.0),
            volume=trade_info.get('volume', 0.0),
            pnl=pnl,
            conditions=trade_info.get('conditions', {})
        )
        logger.info(f"📉 Recorded loss for learning: {trade_info.get('instrument')} in {trade_info.get('regime')} market")
    else:
        # Record win
        self.loss_learner.record_win(
            instrument=trade_info.get('instrument', 'UNKNOWN'),
            pnl=pnl
        )
        logger.info(f"📈 Recorded win: {trade_info.get('instrument')}")

def get_learning_summary(self) -> Dict:
    """Get learning system performance summary"""
    if not self.learning_enabled or not self.loss_learner:
        return {'enabled': False}
    
    return {
        'enabled': True,
        'performance': self.loss_learner.get_performance_summary(),
        'avoidance_patterns': self.loss_learner.get_avoidance_list()
    }
```

---

## Step 4: (Optional) Use in Signal Generation

In your signal generation method, you can optionally add:

```python
# Check early trend (optional - enhances signal quality)
if self.learning_enabled and self.early_trend:
    early_signal = self.early_trend.detect_early_bullish(prices, volumes)
    if early_signal['probability'] > 0.7:
        logger.info(f"🔍 Early bullish trend detected: {early_signal['probability']:.0%}")
        # Can use early_signal['entry_price'] for better entry

# Check failure patterns (optional - avoids repeating mistakes)
if self.learning_enabled and self.loss_learner:
    conditions = {
        'instrument': instrument,
        'regime': regime,
        'adx': adx,
        'momentum': momentum,
        'volume': volume
    }
    if self.loss_learner.is_failure_pattern(conditions):
        if self.honesty:
            self.honesty.log_rejection(
                instrument=instrument,
                reasons=["Similar to past losses - avoiding"],
                scores=score_dict
            )
        continue  # Skip this signal

# Adjust risk based on recent performance (optional but recommended)
if self.learning_enabled and self.loss_learner:
    risk_multiplier = self.loss_learner.get_risk_adjustment(instrument, regime)
    lot_size = base_lot_size * risk_multiplier  # Reduce after losses

# Calculate win probability (optional - for reporting)
if self.learning_enabled and self.honesty:
    win_prob = self.honesty.calculate_win_probability(
        instrument, regime, quality_score, adx, momentum
    )
    logger.info(f"📊 Estimated win probability: {win_prob:.1%}")
```

---

## Integration Checklist

For each strategy:

- [ ] Add imports block with LEARNING_AVAILABLE flag
- [ ] Add initialization in `__init__`
- [ ] Add `record_trade_result()` method
- [ ] Add `get_learning_summary()` method
- [ ] (Optional) Use early_trend in signal generation
- [ ] (Optional) Use failure pattern checking
- [ ] (Optional) Use risk adjustment
- [ ] (Optional) Use win probability calculation
- [ ] Test strategy can still run with/without learning system
- [ ] Verify no errors in logs

---

## Strategies To Integrate

Priority order (based on usage):

1. ✅ `momentum_trading.py` - DONE
2. ⏳ `all_weather_70wr.py` - Account 002 (+$1,152 winner)
3. ⏳ `momentum_v2.py` - Account 003
4. ⏳ `ultra_strict_v2.py` - Account 004
5. ⏳ `champion_75wr.py` - Account 005
6. ⏳ `gold_scalping_optimized.py` - Account 009
7. ⏳ `ultra_strict_forex_optimized.py` - Account 010

---

## Testing After Integration

1. **Import Test:**
   ```bash
   python3 -c "from src.strategies.STRATEGY_NAME import *"
   ```

2. **Instantiation Test:**
   ```python
   from src.strategies.STRATEGY_NAME import StrategyClass
   strategy = StrategyClass()
   print(f"Learning enabled: {strategy.learning_enabled}")
   ```

3. **Record Test:**
   ```python
   strategy.record_trade_result(
       trade_info={'instrument': 'EUR_USD', 'regime': 'TRENDING', 'adx': 30, 'momentum': 0.01, 'volume': 0.5},
       result='LOSS',
       pnl=-25.0
   )
   print(strategy.get_learning_summary())
   ```

4. **Run Full Verification:**
   ```bash
   python3 verify_learning_system.py
   ```

---

## Notes

- All learning features are **optional** and **non-breaking**
- Strategies work normally even if learning system unavailable
- Each strategy learns independently (no cross-contamination)
- Learning data stored in `strategy_learning_data/`
- Honesty logs stored in `strategy_honesty_logs/`

---

**Template Version:** 1.0  
**Date:** October 21, 2025  
**Reference Implementation:** `src/strategies/momentum_trading.py`

