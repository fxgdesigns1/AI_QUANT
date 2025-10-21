# 🚀 Strategy Switcher - User Guide

## Overview

The Strategy Switcher provides a **web-based interface** for managing trading strategies with **live, instant switching** - no more manual YAML editing or cloud redeployments!

## ✨ Key Features

- **10-30 second strategy switches** (vs 2-3 minute cloud deployments)
- **Visual interface** with drag-and-drop ease
- **Live preview** of changes before applying
- **Graceful restarts** that wait for positions to close
- **Automatic rollback** on failures
- **Position safety monitoring** 
- **Real-time progress updates** via WebSocket
- **One-click enable/disable** for accounts
- **Full audit trail** with automatic backups

## 🎯 Quick Start

### Access the Strategy Manager

1. Navigate to your main dashboard
2. Click the **"⚙️ Strategy Manager"** button in the header
3. Or go directly to: `https://your-app.appspot.com/strategy-manager`

### Switch a Strategy

1. Find the account card you want to modify
2. Click the **strategy dropdown**
3. Select a new strategy from the list
4. The card will highlight in **yellow** showing a pending change
5. Review changes in the **"Pending Changes"** preview panel
6. Click **"Apply All Changes"** when ready
7. Confirm in the dialog
8. Watch real-time progress as system restarts safely

### Enable/Disable an Account

1. Find the account card
2. Toggle the **switch** on the top-right
3. The change is staged immediately
4. Apply when ready

## 📋 Available Strategies

The system shows all strategies from your `accounts.yaml`:

- **gold_scalping** - High-frequency gold scalping (5M timeframe)
- **ultra_strict_forex** - Strict forex with multi-timeframe (15M)
- **momentum_trading** - Momentum-based multi-currency (15M-1H)
- **gbp_usd_5m_strategy_rank_1** - Best Sharpe ratio strategy (35.90)
- **gbp_usd_5m_strategy_rank_2** - Second best strategy (35.55)
- **gbp_usd_5m_strategy_rank_3** - Most conservative strategy (35.18)
- **champion_75wr** - Ultra-selective 75% win rate (1H)
- **ultra_strict_v2** - Regime-aware adaptive (1H)
- **momentum_v2** - Execution-robust momentum (1H)
- **all_weather_70wr** - All-weather 70% win rate (1H)

## 🔄 How the Graceful Restart Works

When you click **"Apply Changes"**, the system:

1. **Checks for open positions** across all accounts
2. **Waits up to 30 seconds** for positions to close
   - Shows real-time countdown
   - Displays how many positions remain open
3. **Backs up** your current configuration
4. **Applies** the new configuration to `accounts.yaml`
5. **Restarts** the trading scanner with new strategies
6. **Verifies** everything is working
7. **Sends Telegram notification** on completion

## 🛡️ Safety Features

### Position Safety
- System will **not restart** while positions are open (unless forced)
- Automatically waits for positions to close
- Configurable timeout (default: 30 seconds)
- Real-time position count display

### Configuration Validation
- Validates all changes before applying
- Checks that strategies exist
- Ensures account IDs are valid
- Verifies YAML structure

### Automatic Backups
- Every change creates a timestamped backup
- Keeps last 10 backups automatically
- Backups stored in `config_backups/` directory
- One-click rollback (coming soon)

### Error Handling
- Automatic rollback on configuration errors
- Scanner reinitializes if restart fails
- Telegram alerts on failures
- Detailed error messages in UI

## 🎨 UI Elements Explained

### Account Cards
- **Green border** = Account active
- **Gray/faded** = Account disabled
- **Yellow border** = Pending changes
- **Strategy dropdown** = Select new strategy
- **Toggle switch** = Enable/disable account
- **Instrument tags** = Shows what pairs are traded
- **Risk settings** = Daily trade limits displayed

### Status Indicators
- **Green dot** = Safe to restart (no open positions)
- **Yellow dot** = Positions open, will wait
- **Animated pulse** = System checking status

### Preview Panel
Shows all pending changes with:
- Account name
- Old → New strategy
- Enable/Disable actions
- Change timestamps

### Progress Modal
Real-time updates during restart:
- **Progress bar** (0% → 100%)
- **Status messages** (Checking positions... Applying config...)
- **Time remaining** for position close

## ⚡ Common Workflows

### Test a New Strategy on One Account
```
1. Switch strategy on account
2. Preview change
3. Apply
4. Monitor performance
5. Revert or expand to other accounts
```

### Disable All Momentum Strategies
```
1. Toggle OFF each momentum account
2. Review in preview panel
3. Apply all at once
4. System updates in one restart
```

### Switch Gold Strategy During High Volatility
```
1. Select gold account
2. Switch from scalping → conservative strategy
3. Apply immediately
4. System waits for current trades to close
5. New strategy active in 10-30 seconds
```

### A/B Test Two Strategies
```
1. Keep account A on strategy 1
2. Switch account B to strategy 2
3. Run for 2 days
4. Compare on Analytics Dashboard
5. Switch losing account to winning strategy
```

## 🔧 Technical Details

### API Endpoints

- `GET /api/strategies/config` - Get current configuration
- `POST /api/strategies/switch` - Stage strategy switch
- `POST /api/strategies/toggle` - Stage account toggle
- `GET /api/strategies/pending` - Get pending changes
- `POST /api/strategies/clear` - Clear pending changes
- `GET /api/strategies/status` - Get restart status
- `POST /api/strategies/apply` - Apply changes & restart

### File Locations

- **API Logic**: `src/api/strategy_manager.py`
- **Restart Manager**: `src/core/graceful_restart.py`
- **UI Template**: `src/templates/strategy_switcher.html`
- **Main Routes**: `main.py` (lines 380-596)
- **Configuration**: `accounts.yaml` (modified by system)
- **Backups**: `config_backups/accounts_backup_YYYYMMDD_HHMMSS.yaml`

### WebSocket Events

Real-time updates via Socket.IO:
- `restart_progress` - Progress updates during restart
- `restart_complete` - Restart finished successfully
- `restart_failed` - Restart encountered error

## 🚨 Troubleshooting

### "Positions did not close in time"
**Cause**: Open positions didn't close within 30 seconds  
**Solution**: 
- Wait longer and try again
- Close positions manually in OANDA
- Use force apply (admin only)

### "Configuration validation failed"
**Cause**: Invalid YAML structure or missing strategy  
**Solution**:
- Check strategy name spelling
- Verify strategy exists in `strategies` section
- Contact admin if persistent

### "Scanner restart failed"
**Cause**: Error reinitializing trading scanner  
**Solution**:
- Configuration was still applied
- Scanner will reinitialize on next scheduled run (5 min)
- Check logs for details
- Redeploy if needed

### Changes not reflecting
**Cause**: Browser cache or WebSocket disconnected  
**Solution**:
- Click "🔄 Refresh" button
- Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
- Check browser console for errors

## 📊 Monitoring Changes

### Check Applied Configuration
```bash
# View current config
cat google-cloud-trading-system/accounts.yaml

# View recent backups
ls -lh google-cloud-trading-system/config_backups/
```

### View Logs
```bash
# Check system logs on Google Cloud
gcloud app logs tail -s default

# Look for restart messages
grep "restart" logs/*.log
```

### Verify Strategy is Active
1. Go to main dashboard
2. Check "Active Systems" section
3. Confirm strategy names match your changes
4. Monitor for new signals

## 🎓 Best Practices

1. **Test changes one account at a time** initially
2. **Review preview panel** before applying
3. **Apply during low-volatility periods** when possible
4. **Monitor system after changes** for 15-30 minutes
5. **Keep backups** if making major changes
6. **Document your strategy switches** for performance tracking
7. **Use A/B testing** to compare strategies objectively

## 🔮 Future Enhancements

Coming soon:
- One-click rollback to previous configuration
- Strategy performance comparison in switcher UI
- Scheduled strategy switches (time-based)
- Bulk operations (switch multiple accounts at once)
- Custom strategy templates
- Import/export configurations
- Strategy cloning across accounts

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review system logs
3. Check Telegram for error notifications
4. Verify `accounts.yaml` structure
5. Test with one account first
6. Contact system admin if persistent

## 🎉 Benefits Over Manual YAML Editing

| Feature | Manual YAML | Strategy Switcher |
|---------|-------------|-------------------|
| **Time to apply** | 2-3 minutes | 10-30 seconds |
| **User interface** | Text editor | Visual dashboard |
| **Error risk** | High (manual typos) | Low (validated) |
| **Preview changes** | No | Yes |
| **Rollback** | Manual git revert | One-click (soon) |
| **Position safety** | Manual check | Automatic monitoring |
| **Real-time feedback** | No | Yes (WebSocket) |
| **Audit trail** | Manual git commits | Automatic backups |

---

**Ready to switch strategies?** Head to the Strategy Manager and try it out! 🚀



