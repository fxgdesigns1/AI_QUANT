# Trading Signals Dashboard - User Guide

## Quick Start

### Access the Dashboard

**Cloud (Recommended):**
```
https://ai-quant-trading.uc.r.appspot.com/signals
```

**Local:**
```
http://localhost:8080/signals
```

## Dashboard Overview

### Top Statistics Bar
- **Total Signals** - All signals generated today
- **Pending** - Signals waiting for entry
- **Active Trades** - Currently open positions
- **Win Rate Today** - Percentage of winning trades
- **Avg Hold Time** - Average trade duration in minutes

### Filters Section
- **Strategy Filter** - View signals from specific strategies
- **Instrument Filter** - View signals for specific pairs
- **Status Filter** - Show only pending or active
- **Sort By** - Order by time, pips away, or confidence
- **Auto-Refresh Toggle** - Enable/disable 5-second auto-updates

## Pending Signals

### What You'll See
Each pending signal card shows:

1. **Instrument & Side** - e.g., EUR/USD BUY
2. **Strategy Name** - Which strategy generated it
3. **Entry Price** - Target entry price
4. **Current Price** - Live market price
5. **Stop Loss** - Where the stop is placed
6. **Take Profit** - Target exit price
7. **Pips Away from Entry** - How close we are to entry
   - 🟢 Green (< 5 pips): Very close to entry
   - 🟡 Yellow (5-15 pips): Moderate distance
   - 🔴 Red (> 15 pips): Far from entry
8. **AI Insight** - Why this signal was generated
9. **Confidence** - Strategy confidence (0-100%)
10. **R/R Ratio** - Risk:Reward ratio
11. **Generated Time** - When signal was created

### Interpreting Pending Signals

**Example Pending Signal:**
```
EUR/USD BUY
Strategy: Momentum V2
Entry: 1.08500 | Current: 1.08512
Pips Away: +1.2 pips 🟢

AI Insight: "Momentum v2 detected buy opportunity. 
Spread 0.015%. High confidence signal during 
London session. Momentum alignment detected."

Confidence: 92% | R/R: 1:2.5 | Generated: 5m ago
```

**Interpretation:**
- Current price is 1.2 pips above entry (very close!)
- High confidence (92%) means strong signal
- Good risk/reward (1:2.5)
- Generated 5 minutes ago (recent)
- Signal is likely to execute soon

## Active Trades

### What You'll See
Each active trade card shows:

1. **Instrument & Side** - Current position
2. **Strategy Name** - Strategy managing this trade
3. **Unrealized P/L** - Current profit or loss
4. **Status Badge** - PROFIT or DRAWDOWN
5. **Entry Price** - Where we entered
6. **Current Price** - Live market price
7. **Progress Bar** - Visual position between SL and TP
8. **Pips to Stop Loss** - Distance to SL (red)
9. **Pips to Take Profit** - Distance to TP (green)
10. **AI Insight** - Why we entered this trade
11. **Duration** - How long trade has been open
12. **Confidence** - Original entry confidence

### Interpreting Active Trades

**Example Active Trade (Profit):**
```
GBP/USD SELL
Strategy: Champion 75WR
Unrealized P/L: +$47.50 [PROFIT] 🟢

Entry: 1.27500 | Current: 1.27320
━━━━━━●━━━ 
SL: 12.5 pips | TP: 5.8 pips

AI Insight: "Champion 75wr detected sell opportunity. 
Spread 0.012%. High confidence signal during 
London session. High win-rate setup."

Duration: 23 min | Confidence: 88%
```

**Interpretation:**
- Trade is in profit (+$47.50)
- Closer to TP (5.8 pips) than SL (12.5 pips)
- Progress bar shows position favoring TP
- Been running for 23 minutes
- High confidence entry (88%)

**Example Active Trade (Drawdown):**
```
EUR/JPY BUY
Strategy: Ultra Strict V2
Unrealized P/L: -$12.30 [DRAWDOWN] 🔴

Entry: 163.250 | Current: 163.180
━━●━━━━━━━
SL: 3.2 pips | TP: 15.7 pips

AI Insight: "Ultra strict v2 detected buy opportunity. 
Spread 0.018%. Moderate confidence. 
Strict entry criteria met."

Duration: 8 min | Confidence: 72%
```

**Interpretation:**
- Trade is in drawdown (-$12.30)
- Close to stop loss (3.2 pips away) - risky!
- Much further from TP (15.7 pips)
- Still young (8 minutes)
- Lower confidence (72%)

## Using Filters

### Filter by Strategy
```
Select: "Momentum V2"
Result: Shows only signals from Momentum V2 strategy
```

Use this to:
- Monitor specific strategy performance
- Compare strategy signal quality
- Focus on your favorite strategies

### Filter by Instrument
```
Select: "EUR_USD"
Result: Shows only EUR/USD signals
```

Use this to:
- Focus on specific currency pairs
- Monitor high-volatility pairs
- Track your preferred instruments

### Filter by Status
```
Select: "Active"
Result: Shows only currently open trades
```

Use this to:
- Monitor open positions only
- Check all pending opportunities
- Quick status overview

### Sort Options
- **Time (Newest)** - Most recent signals first
- **Pips Away** - Pending signals closest to entry first
- **Confidence** - Highest confidence signals first

## Understanding AI Insights

### Insight Components

1. **Strategy Identification**
   - "Momentum v2 detected buy opportunity"
   - "Ultra strict v2 detected sell opportunity"

2. **Market Conditions**
   - "Spread 0.015%" - Current spread cost
   - "During London session" - Trading session
   - "Prime time trading hours"

3. **Confidence Level**
   - "High confidence signal" - 90%+
   - "Moderate confidence" - 70-90%
   - "Lower confidence, tight stops" - <70%

4. **Strategy-Specific Context**
   - "Momentum alignment detected" - Momentum strategy
   - "Strict entry criteria met" - Ultra Strict strategy
   - "Short-term scalping setup" - Scalping strategy
   - "High win-rate setup" - Champion 75WR strategy

### Example Insights Decoded

**"Momentum v2 detected buy opportunity. Spread 0.015%. High confidence signal during London session. Momentum alignment detected."**

Translation:
- Momentum V2 strategy found a buying opportunity
- The spread is very tight (0.015% - good for entry)
- High confidence (90%+ probability)
- It's during London session (optimal trading time)
- Momentum indicators are aligned (strong signal)

## Best Practices

### Monitoring Pending Signals
1. Check pips away - closer is better
2. High confidence (>85%) signals are more reliable
3. Good R/R ratio (1:2 or better) preferred
4. Recent signals (< 15 min) are more relevant

### Monitoring Active Trades
1. Watch pips to SL - if < 5 pips, risk is high
2. Progress bar should favor TP side
3. Longer duration may mean ranging market
4. Drawdown trades near SL need attention

### Using Auto-Refresh
- **Keep ON** for active monitoring
- **Turn OFF** if dashboard is distracting
- Updates every 5 seconds automatically
- WebSocket provides instant updates

## Dashboard Behavior

### Signal Lifecycle

```
1. PENDING (⏳)
   - Signal generated by strategy
   - Waiting for entry price
   - Shows pips away from entry
   - May expire after 1 hour

2. ACTIVE (🔥)
   - Trade executed
   - Position is open
   - Shows real-time P/L
   - Shows pips to SL/TP

3. CLOSED
   - FILLED (✅) - Take profit hit (WIN)
   - STOPPED (❌) - Stop loss hit (LOSS)
   - Archived after closing
```

### Empty States

**No Pending Signals:**
```
⏳ No Pending Signals
Waiting for new trading opportunities...
```
This is normal during:
- Quiet market periods
- Weekend mode
- Outside trading sessions

**No Active Trades:**
```
📊 No Active Trades
All clear - no open positions
```
This is normal when:
- No signals have executed yet
- All trades have closed
- System is in observation mode

## Time Display

All times are in **London Time (GMT/BST)**:
- "Just now" - < 1 minute ago
- "5m ago" - 5 minutes ago
- "2h ago" - 2 hours ago
- Full timestamp for older signals

## Mobile Usage

Dashboard is fully responsive:
- Cards stack vertically on mobile
- All features available
- Touch-friendly controls
- Same real-time updates

## Troubleshooting

### Dashboard Not Loading
1. Check internet connection
2. Verify URL is correct
3. Try refreshing page (Cmd/Ctrl + R)

### No Signals Showing
1. Check if it's weekend (markets closed)
2. Verify system is running
3. Check filters - may be hiding signals
4. Wait for next scanner run (every 5 minutes)

### Auto-Refresh Not Working
1. Check browser console for errors
2. Verify WebSocket connection
3. Try manual refresh button
4. Reload page to reconnect

### Prices Not Updating
1. Check WebSocket status (green pulse)
2. Verify auto-refresh is ON
3. Check network connection
4. Reload page

## Tips & Tricks

1. **Bookmark the Dashboard**
   - Quick access to signals

2. **Use Multiple Filters**
   - Strategy + Instrument for focused view

3. **Monitor Win Rate**
   - Track daily performance
   - High win rate = good day

4. **Watch Average Hold Time**
   - Long hold time may indicate ranging market
   - Short hold time suggests trending market

5. **Check Statistics Bar First**
   - Quick overview of system activity
   - Spot unusual patterns quickly

## Support

For issues or questions:
1. Check this guide first
2. Review `SIGNALS_DASHBOARD_IMPLEMENTATION.md` for technical details
3. Check system logs for errors
4. Verify all services are running

## What's Next

Future enhancements could include:
- Trade execution buttons
- Detailed signal history
- Performance charts per strategy
- Export signals to CSV
- Alert notifications
- Mobile app

---

**Dashboard URL:** https://ai-quant-trading.uc.r.appspot.com/signals

**Last Updated:** October 16, 2025



