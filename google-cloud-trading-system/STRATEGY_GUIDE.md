# 🎯 Modular Strategy Management Guide

## ✅ Your System is Fully Modular!

Each strategy operates **independently**. You can tweak, test, and perfect each one without affecting the others.

---

## 📂 Strategy Files

```
/src/strategies/
├── ultra_strict_forex.py    → Account 010 (Forex Trading)
├── gold_scalping.py          → Account 009 (Gold Scalping)
└── momentum_trading.py       → Account 011 (Alpha/Momentum)
```

---

## 🔧 Quick Strategy Tweaking

### **Method 1: Edit Configuration File (Easiest)**

Edit `strategy_config.yaml` to change any parameter:

```yaml
gold_scalping:
  locked: false  # Change to true when perfected
  
  parameters:
    lot_size: 10000        # Change lot size
    max_trades_per_day: 100  # Change trade limits
    
  entry:
    confidence_threshold: 0.25  # Adjust entry criteria
    
  risk:
    stop_loss_pct: 0.003   # Adjust stop loss
    take_profit_pct: 0.005  # Adjust take profit
```

**Deploy changes:**
```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system
gcloud app deploy --quiet
```

---

### **Method 2: Use Command-Line Tool**

```bash
# Show all strategy statuses
python strategy_manager.py

# Update a parameter
python strategy_manager.py update gold_scalping parameters lot_size 20000
python strategy_manager.py update ultra_strict_forex entry confidence_threshold 0.40

# Lock a perfected strategy
python strategy_manager.py lock gold_scalping

# Disable a strategy temporarily
python strategy_manager.py disable momentum_trading
```

---

## 🔒 Locking Strategies (Closing the System)

When you've **perfected a strategy**, lock it to prevent accidental changes:

```bash
# Lock a strategy
python strategy_manager.py lock gold_scalping
```

Or edit `strategy_config.yaml`:
```yaml
gold_scalping:
  locked: true  # ← Set this to true
```

**Locked strategies cannot be modified** until explicitly unlocked.

---

## 🎛️ Common Tweaks

### **Increase Aggressiveness:**
```bash
# More trades
python strategy_manager.py update gold_scalping parameters max_trades_per_day 200

# Lower entry threshold (more opportunities)
python strategy_manager.py update gold_scalping entry confidence_threshold 0.15

# Bigger lot sizes
python strategy_manager.py update gold_scalping parameters lot_size 30000
```

### **Reduce Risk:**
```bash
# Tighter stop loss
python strategy_manager.py update gold_scalping risk stop_loss_pct 0.002

# Smaller lot sizes
python strategy_manager.py update gold_scalping parameters lot_size 5000

# Fewer trades
python strategy_manager.py update gold_scalping parameters max_trades_per_day 50
```

### **Perfect Entry Timing:**
```bash
# Higher quality trades only
python strategy_manager.py update ultra_strict_forex entry confidence_threshold 0.50

# More aggressive ADX requirement
python strategy_manager.py update momentum_trading entry min_adx 25
```

---

## 🔄 Workflow: Perfecting a Strategy

1. **Initial Setup** - Start with default parameters
2. **Test** - Run for a day, observe results
3. **Tweak** - Adjust parameters in `strategy_config.yaml`
4. **Deploy** - `gcloud app deploy --quiet`
5. **Repeat** - Continue testing and tweaking
6. **Perfect** - When satisfied, lock the strategy
7. **Move On** - Start perfecting the next strategy

---

## 📊 Example: Perfecting Gold Strategy

```bash
# Week 1: Test default settings
python strategy_manager.py  # Check status

# Week 2: Increase lot size after good results
python strategy_manager.py update gold_scalping parameters lot_size 20000
gcloud app deploy --quiet

# Week 3: Tighten entry criteria
python strategy_manager.py update gold_scalping entry confidence_threshold 0.30
gcloud app deploy --quiet

# Week 4: Perfect! Lock it down
python strategy_manager.py lock gold_scalping

# Now move on to perfecting ultra_strict_forex...
```

---

## 🚨 Change Logging

All changes are automatically logged to `strategy_changes.log`:

```
[2025-09-30 14:30:22] gold_scalping.parameters.lot_size: 10000 → 20000
[2025-09-30 14:35:10] gold_scalping.entry.confidence_threshold: 0.25 → 0.30
[2025-09-30 14:40:05] gold_scalping.locked: False → True
```

---

## 🎯 Independent Strategy Control

**KEY POINT:** Each strategy has its own:
- ✅ Trading logic
- ✅ Risk parameters
- ✅ Instruments
- ✅ Entry/exit criteria
- ✅ Lock status

**Changing one strategy NEVER affects the others!**

---

## 💡 Pro Tips

1. **Test one change at a time** - Easier to identify what works
2. **Lock strategies as you perfect them** - Prevents accidental changes
3. **Use the log file** - Review `strategy_changes.log` to track what you changed
4. **Start conservative** - Easier to increase aggressiveness than recover from losses
5. **Perfect in order** - Focus on one strategy at a time

---

## 🔐 Final Lockdown

When **ALL strategies are perfected**, lock the entire system:

```bash
python strategy_manager.py lock gold_scalping
python strategy_manager.py lock ultra_strict_forex
python strategy_manager.py lock momentum_trading
```

Now the system is **closed off** and production-ready! 🎉

