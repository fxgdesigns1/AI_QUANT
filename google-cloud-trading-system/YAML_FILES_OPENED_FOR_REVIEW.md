# 📋 YOUR YAML STRATEGY FILES - FULL DETAILS

## YAML FILE 1: RANK_01_AUD_USD_5m_140pct_Return.yaml

**Designed For:** AUD_USD (Australian Dollar vs US Dollar)
- **Pair:** AUD_USD
- **Annual Return:** 140.1%
- **Win Rate:** 80.3%
- **Sharpe:** 35.0
- **Max DD:** 1.4%
- **Trades Tested:** 3,173

**Indicators:**
- EMA Fast: 3
- EMA Slow: 12
- RSI: 14 period (20/80 levels)
- ATR: 14 period, 1.5x multiplier

---

## YAML FILE 2: RANK_01_EUR_USD_5m_Lowest_DD.yaml

**Designed For:** EUR_USD (Euro vs US Dollar)
- **Pair:** EUR_USD
- **Annual Return:** 106.1%
- **Win Rate:** 80.8% (HIGHEST)
- **Sharpe:** 34.29
- **Max DD:** 0.5% (LOWEST)
- **Trades Tested:** 3,263

**Indicators:**
- EMA Fast: 3
- EMA Slow: 12
- RSI: 14 period (20/80 levels)
- ATR: 14 period, 1.5x multiplier

---

## YAML FILE 3: RANK_01_XAU_USD_5m_GOLD_199pct_Return.yaml

**Designed For:** XAU_USD (Gold vs US Dollar)
- **Pair:** XAU_USD
- **Annual Return:** 199.7% (HIGHEST)
- **Win Rate:** 80.2%
- **Sharpe:** 33.04
- **Max DD:** 0.7%
- **Trades Tested:** 3,142

**Indicators:**
- EMA Fast: 3
- EMA Slow: 12
- RSI: 14 period (20/80 levels)
- ATR: 14 period, 1.5x multiplier

---

## YAML FILE 4: MULTI_STRATEGY_PORTFOLIO.yaml

**Designed For:** Multi-pair portfolio (4 pairs in one account)

**The 4 Pairs:**
1. **GBP_USD** (30% allocation, $6,000)
2. **EUR_USD** (30% allocation, $6,000)
3. **XAU_USD** (20% allocation, $4,000)
4. **AUD_USD** (20% allocation, $4,000)

**Combined Performance:**
- Portfolio Win Rate: 80.4%
- Portfolio Sharpe: 34.5
- Expected Annual Return: 140%

---

## ❌ **THE MISMATCH I CREATED:**

### What YOUR Original Config Says (streaming_data_feed.py):
```python
'101-004-30719775-006': ['EUR_JPY', 'USD_CAD'],  # Group 3 High Win Rate
'101-004-30719775-007': ['GBP_USD', 'XAU_USD'],  # Group 2 Zero Drawdown
'101-004-30719775-008': ['GBP_USD', 'NZD_USD', 'XAU_USD']  # Group 1 High Frequency
```

### What the YAML Files Say:
```yaml
AUD_USD YAML: pair: AUD_USD  (not EUR_JPY, USD_CAD!)
EUR_USD YAML: pair: EUR_USD  (not GBP_USD, XAU_USD!)
XAU_USD YAML: pair: XAU_USD  (correct for 007/008)
MULTI_PORTFOLIO YAML: GBP_USD, EUR_USD, XAU_USD, AUD_USD  (not GBP_USD, NZD_USD, XAU_USD!)
```

---

## 🎯 **THE TRUTH:**

**You have a MISMATCH:**

1. **Your YAML files** were designed/backtested for specific pairs (AUD_USD, EUR_USD, XAU_USD)
2. **Your system config** assigns different pairs (EUR_JPY, USD_CAD, GBP_USD, NZD_USD, XAU_USD)

**The strategy LOGIC is the same** (EMA/RSI/ATR indicators), but:
- It was backtested on AUD_USD
- You're applying it to EUR_JPY, USD_CAD

---

## ❓ **QUESTION FOR YOU:**

**Did you mean to:**

**A)** Use the same strategy logic (EMA 3/12, RSI, ATR) on DIFFERENT pairs than backtested?
- Account 006: EUR_JPY, USD_CAD (not AUD_USD as backtested)
- Account 007: GBP_USD, XAU_USD (partially matches - has XAU_USD)
- Account 008: GBP_USD, NZD_USD, XAU_USD (has GBP and XAU from portfolio)

**B)** Actually trade the EXACT pairs from the YAML files?
- Account 006: AUD_USD (as in YAML)
- Account 007: EUR_USD (as in YAML)
- Account 008: GBP_USD, EUR_USD, XAU_USD, AUD_USD (as in MULTI_PORTFOLIO YAML)

**Which is your intention?**





