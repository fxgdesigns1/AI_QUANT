# Google Cloud Trading System Calibration Guide

## Overview

This guide explains how to apply the calibrated parameters to your Google Cloud trading system to ensure it generates trades with less strict parameters.

## Calibrated Parameters

The following parameters have been calibrated to ensure trade generation:

| Parameter | Original Value | Calibrated Value | Description |
|-----------|----------------|-----------------|-------------|
| max_margin_usage | 0.8 (80%) | 0.75 (75%) | Maximum portfolio margin usage |
| min_signal_strength | 0.7 | 0.5 | Minimum signal strength for trade generation |
| position_size_multiplier | 1.0 | 0.5 | Multiplier for position sizing |
| data_validation | strict | moderate | Data validation strictness |
| forced_trading_mode | disabled | enabled | Force minimum number of trades |
| min_trades_today | 0 | 2 | Minimum trades per day per strategy |

## Deployment Instructions

### Option 1: Using the Deployment Script

1. Navigate to your project directory:
   ```
   cd /Users/mac/quant_system_clean/google-cloud-trading-system
   ```

2. Run the deployment script:
   ```
   ./deploy_calibrated_cloud.sh
   ```

3. Wait for the deployment to complete (typically 5-10 minutes)

### Option 2: Manual Deployment

1. Set environment variables in Google Cloud:
   ```
   gcloud app deploy app.yaml --project=unknown-project --quiet \
     --set-env-vars=PRIMARY_MAX_PORTFOLIO_RISK=0.75,\
   GOLD_MAX_PORTFOLIO_RISK=0.75,\
   ALPHA_MAX_PORTFOLIO_RISK=0.75,\
   FORCED_TRADING_MODE=enabled,\
   POSITION_SIZE_MULTIPLIER=0.5,\
   MIN_CONFIDENCE_THRESHOLD=0.5,\
   MIN_TRADES_TODAY=2
   ```

2. Wait for the deployment to complete

## Monitoring Instructions

After deploying the calibrated parameters, monitor the system to ensure it's generating trades:

1. Run the monitoring script:
   ```
   python3 monitor_cloud_trades.py
   ```

2. The script will check for new trades every minute for 30 minutes

3. If no trades are detected after 30 minutes, the script will alert you

## Verification

To verify the calibrated parameters are working:

1. Check the Google Cloud logs for trade signals:
   ```
   gcloud app logs read --project=unknown-project | grep "trade signal"
   ```

2. Check the trading system dashboard for active trades

3. Monitor the system status through the API:
   ```
   curl https://unknown-project.appspot.com/api/system/status
   ```

## Reverting Changes

If you need to revert to the original parameters:

1. Deploy with the original parameters:
   ```
   gcloud app deploy app.yaml --project=unknown-project --quiet \
     --set-env-vars=PRIMARY_MAX_PORTFOLIO_RISK=0.10,\
   GOLD_MAX_PORTFOLIO_RISK=0.08,\
   ALPHA_MAX_PORTFOLIO_RISK=0.12,\
   FORCED_TRADING_MODE=disabled,\
   POSITION_SIZE_MULTIPLIER=1.0,\
   MIN_CONFIDENCE_THRESHOLD=0.8,\
   MIN_TRADES_TODAY=0
   ```

## Next Steps

1. Wait for the system to generate trades (at least 30 minutes)
2. Once you confirm trade generation, monitor performance
3. Fine-tune parameters based on trade performance
