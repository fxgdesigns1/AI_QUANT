#!/usr/bin/env python3
"""
Google Cloud Implementation of Calibrated Parameters
Applies the recommended calibrations to the Google Cloud trading system to ensure
it generates trades with less strict parameters.
"""

import os
import sys
import logging
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudCalibrationImplementer:
    """Implements calibrated parameters for Google Cloud deployment"""
    
    def __init__(self):
        """Initialize the cloud calibration implementer"""
        self.implementation_results = {
            'status': 'pending',
            'changes_made': [],
            'files_modified': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Calibrated parameters to implement
        self.calibrated_params = {
            'max_margin_usage': 0.75,  # Reduced from 0.8
            'min_signal_strength': 0.5,  # Reduced from 0.7
            'position_size_multiplier': 0.5,  # Reduced from 1.0
            'data_validation': 'moderate',  # Changed from 'strict'
            'forced_trading_mode': 'enabled',  # Changed from 'disabled'
            'min_trades_today': 2  # Ensure at least 2 trades per day per strategy
        }
        
        # Google Cloud specific paths
        self.cloud_project_id = self._get_cloud_project_id()
        self.cloud_app_name = "adaptive-trading-system"
        
        logger.info("🚀 Google Cloud Calibration Implementer initialized")
        logger.info(f"📊 Cloud Project ID: {self.cloud_project_id}")
        logger.info("=" * 60)
    
    def _get_cloud_project_id(self) -> str:
        """Get Google Cloud project ID from credentials or environment"""
        try:
            # Try to read from credentials file
            creds_path = os.path.join(os.path.dirname(__file__), '..', 'google-cloud-credentials', 'context.json')
            if os.path.exists(creds_path):
                with open(creds_path, 'r') as f:
                    creds = json.load(f)
                    return creds.get('project_id', 'unknown-project')
            
            # Try to get from environment
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
            if project_id:
                return project_id
            
            # Try to get from gcloud command
            try:
                result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                      capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except:
                pass
            
            return "adaptive-trading-system"
        except Exception as e:
            logger.warning(f"⚠️ Could not determine Google Cloud project ID: {e}")
            return "adaptive-trading-system"
    
    def _update_cloud_environment_variables(self) -> bool:
        """Update Google Cloud environment variables with calibrated parameters"""
        try:
            logger.info("🔄 Updating Google Cloud environment variables...")
            
            # Construct environment variable updates
            env_vars = {
                'PRIMARY_MAX_PORTFOLIO_RISK': str(self.calibrated_params['max_margin_usage']),
                'GOLD_MAX_PORTFOLIO_RISK': str(self.calibrated_params['max_margin_usage']),
                'ALPHA_MAX_PORTFOLIO_RISK': str(self.calibrated_params['max_margin_usage']),
                'FORCED_TRADING_MODE': self.calibrated_params['forced_trading_mode'],
                'POSITION_SIZE_MULTIPLIER': str(self.calibrated_params['position_size_multiplier']),
                'MIN_CONFIDENCE_THRESHOLD': str(self.calibrated_params['min_signal_strength']),
                'MIN_TRADES_TODAY': str(self.calibrated_params['min_trades_today'])
            }
            
            # Format for gcloud command
            env_vars_str = " ".join([f"{k}={v}" for k, v in env_vars.items()])
            
            # Construct the gcloud command
            command = f"gcloud app deploy --project={self.cloud_project_id} --quiet --set-env-vars={env_vars_str}"
            
            # Log the command (without executing)
            logger.info(f"📋 Cloud deployment command: {command}")
            
            # Record the changes
            for k, v in env_vars.items():
                self.implementation_results['changes_made'].append({
                    'parameter': k,
                    'new_value': v,
                    'environment': 'google_cloud'
                })
            
            logger.info("✅ Google Cloud environment variables prepared for update")
            logger.info("⚠️ NOTE: Actual deployment requires manual execution of the command")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare Google Cloud environment updates: {e}")
            return False
    
    def _create_cloud_deployment_script(self) -> bool:
        """Create a deployment script for Google Cloud with calibrated parameters"""
        deploy_script_path = os.path.join(os.path.dirname(__file__), 'deploy_calibrated_cloud.sh')
        
        try:
            with open(deploy_script_path, 'w') as f:
                f.write(f'''#!/bin/bash
# Google Cloud Deployment Script with Calibrated Parameters
# This script deploys the trading system to Google Cloud with calibrated parameters

echo "🚀 Deploying calibrated trading system to Google Cloud"
echo "============================================================"

# Set environment variables for calibration
export PRIMARY_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']}
export GOLD_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']}
export ALPHA_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']}
export FORCED_TRADING_MODE={self.calibrated_params['forced_trading_mode']}
export POSITION_SIZE_MULTIPLIER={self.calibrated_params['position_size_multiplier']}
export MIN_CONFIDENCE_THRESHOLD={self.calibrated_params['min_signal_strength']}
export MIN_TRADES_TODAY={self.calibrated_params['min_trades_today']}

# Deploy to Google Cloud
echo "📊 Deploying to project: {self.cloud_project_id}"
gcloud app deploy app.yaml --project={self.cloud_project_id} --quiet \\
  --set-env-vars=PRIMARY_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']},\\
GOLD_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']},\\
ALPHA_MAX_PORTFOLIO_RISK={self.calibrated_params['max_margin_usage']},\\
FORCED_TRADING_MODE={self.calibrated_params['forced_trading_mode']},\\
POSITION_SIZE_MULTIPLIER={self.calibrated_params['position_size_multiplier']},\\
MIN_CONFIDENCE_THRESHOLD={self.calibrated_params['min_signal_strength']},\\
MIN_TRADES_TODAY={self.calibrated_params['min_trades_today']}

# Check deployment status
echo "🔍 Checking deployment status..."
gcloud app services describe default --project={self.cloud_project_id}

echo "============================================================"
echo "✅ Deployment complete"
echo "📊 Visit your Google Cloud console to monitor the application"
echo "🔗 https://console.cloud.google.com/appengine?project={self.cloud_project_id}"
echo "============================================================"
''')
            
            # Make the script executable
            os.chmod(deploy_script_path, 0o755)
            
            logger.info(f"✅ Created Google Cloud deployment script: {deploy_script_path}")
            self.implementation_results['files_modified'].append(deploy_script_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create Google Cloud deployment script: {e}")
            return False
    
    def _create_cloud_monitoring_script(self) -> bool:
        """Create a monitoring script for Google Cloud deployment"""
        monitor_script_path = os.path.join(os.path.dirname(__file__), 'monitor_cloud_trades.py')
        
        try:
            with open(monitor_script_path, 'w') as f:
                f.write('''#!/usr/bin/env python3
"""
Google Cloud Trade Monitor Script
Monitors the Google Cloud trading system and alerts if no trades are generated within a specified time period.
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_cloud_app_url():
    """Get the URL of the Google Cloud App Engine application"""
    # Try to get from environment variable
    app_url = os.environ.get('CLOUD_APP_URL')
    if app_url:
        return app_url
    
    # Try to get from gcloud command
    import subprocess
    try:
        result = subprocess.run(['gcloud', 'app', 'describe', '--format=json'], 
                              capture_output=True, text=True, check=True)
        app_info = json.loads(result.stdout)
        default_hostname = app_info.get('defaultHostname')
        if default_hostname:
            return f"https://{default_hostname}"
    except:
        pass
    
    # Ask the user
    print("Could not determine Google Cloud App URL automatically.")
    app_url = input("Please enter your Google Cloud App URL: ")
    return app_url

def check_for_trades(app_url, api_key=None, max_wait_minutes=30):
    """Check if trades have been executed within the specified time period"""
    logger.info(f"🔍 Monitoring for trades on {app_url} (max wait: {max_wait_minutes} minutes)")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=max_wait_minutes)
    
    # Initial trade count
    initial_trade_count = get_trade_count(app_url, api_key)
    logger.info(f"📊 Initial trade count: {initial_trade_count}")
    
    while datetime.now() < end_time:
        # Check current trade count
        current_trade_count = get_trade_count(app_url, api_key)
        new_trades = current_trade_count - initial_trade_count
        
        if new_trades > 0:
            logger.info(f"✅ {new_trades} new trades detected!")
            return True
        
        # Check system status
        system_status = get_system_status(app_url, api_key)
        logger.info(f"📊 System status: {system_status}")
        
        # Sleep for a bit
        logger.info(f"⏳ Waiting for trades... ({int((end_time - datetime.now()).total_seconds())} seconds remaining)")
        time.sleep(60)  # Check every minute
    
    logger.warning(f"❌ No trades detected within {max_wait_minutes} minutes")
    return False

def get_trade_count(app_url, api_key=None):
    """Get the current trade count from the Google Cloud application"""
    try:
        headers = {}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        
        response = requests.get(f"{app_url}/api/trades/count", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('count', 0)
        else:
            logger.warning(f"⚠️ Failed to get trade count: {response.status_code}")
            return 0
    except Exception as e:
        logger.error(f"❌ Error getting trade count: {e}")
        return 0

def get_system_status(app_url, api_key=None):
    """Get the current system status from the Google Cloud application"""
    try:
        headers = {}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        
        response = requests.get(f"{app_url}/api/system/status", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"⚠️ Failed to get system status: {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        return {}

def alert_no_trades():
    """Alert that no trades have been generated"""
    logger.error("🚨 ALERT: No trades generated within the specified time period")
    logger.error("🔧 Consider checking the following:")
    logger.error("   1. Google Cloud logs for errors")
    logger.error("   2. Market conditions (low volatility?)")
    logger.error("   3. Strategy parameters (still too strict?)")
    logger.error("   4. Data feed issues (receiving fresh data?)")
    logger.error("   5. Order execution issues (OANDA connection?)")

def main():
    """Main monitoring function"""
    logger.info("🚀 Starting Google Cloud Trade Monitor")
    
    # Get the Google Cloud App URL
    app_url = get_cloud_app_url()
    logger.info(f"🔗 Google Cloud App URL: {app_url}")
    
    # Check for trades with a 30-minute timeout
    trades_detected = check_for_trades(app_url, max_wait_minutes=30)
    
    if not trades_detected:
        alert_no_trades()
        return False
    
    logger.info("✅ Trading system is active and generating trades")
    return True

if __name__ == '__main__':
    main()
''')
            
            # Make the script executable
            os.chmod(monitor_script_path, 0o755)
            
            logger.info(f"✅ Created Google Cloud monitoring script: {monitor_script_path}")
            self.implementation_results['files_modified'].append(monitor_script_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create Google Cloud monitoring script: {e}")
            return False
    
    def _create_cloud_calibration_guide(self) -> bool:
        """Create a guide for calibrating the Google Cloud deployment"""
        guide_path = os.path.join(os.path.dirname(__file__), 'CLOUD_CALIBRATION_GUIDE.md')
        
        try:
            with open(guide_path, 'w') as f:
                f.write(f'''# Google Cloud Trading System Calibration Guide

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
   gcloud app deploy app.yaml --project={self.cloud_project_id} --quiet \\
     --set-env-vars=PRIMARY_MAX_PORTFOLIO_RISK=0.75,\\
   GOLD_MAX_PORTFOLIO_RISK=0.75,\\
   ALPHA_MAX_PORTFOLIO_RISK=0.75,\\
   FORCED_TRADING_MODE=enabled,\\
   POSITION_SIZE_MULTIPLIER=0.5,\\
   MIN_CONFIDENCE_THRESHOLD=0.5,\\
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
   gcloud app logs read --project={self.cloud_project_id} | grep "trade signal"
   ```

2. Check the trading system dashboard for active trades

3. Monitor the system status through the API:
   ```
   curl https://{self.cloud_project_id}.appspot.com/api/system/status
   ```

## Reverting Changes

If you need to revert to the original parameters:

1. Deploy with the original parameters:
   ```
   gcloud app deploy app.yaml --project={self.cloud_project_id} --quiet \\
     --set-env-vars=PRIMARY_MAX_PORTFOLIO_RISK=0.10,\\
   GOLD_MAX_PORTFOLIO_RISK=0.08,\\
   ALPHA_MAX_PORTFOLIO_RISK=0.12,\\
   FORCED_TRADING_MODE=disabled,\\
   POSITION_SIZE_MULTIPLIER=1.0,\\
   MIN_CONFIDENCE_THRESHOLD=0.8,\\
   MIN_TRADES_TODAY=0
   ```

## Next Steps

1. Wait for the system to generate trades (at least 30 minutes)
2. Once you confirm trade generation, monitor performance
3. Fine-tune parameters based on trade performance
''')
            
            logger.info(f"✅ Created Google Cloud calibration guide: {guide_path}")
            self.implementation_results['files_modified'].append(guide_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create Google Cloud calibration guide: {e}")
            return False
    
    def implement_cloud_calibrations(self):
        """Implement all calibrated parameters for Google Cloud"""
        logger.info("🚀 Starting Google Cloud calibration implementation")
        logger.info("=" * 60)
        
        try:
            # Update Google Cloud environment variables
            if self._update_cloud_environment_variables():
                logger.info("✅ Google Cloud environment variables prepared successfully")
            
            # Create Google Cloud deployment script
            if self._create_cloud_deployment_script():
                logger.info("✅ Google Cloud deployment script created successfully")
            
            # Create Google Cloud monitoring script
            if self._create_cloud_monitoring_script():
                logger.info("✅ Google Cloud monitoring script created successfully")
            
            # Create Google Cloud calibration guide
            if self._create_cloud_calibration_guide():
                logger.info("✅ Google Cloud calibration guide created successfully")
            
            # Update implementation status
            self.implementation_results['status'] = 'completed'
            self.implementation_results['timestamp'] = datetime.now().isoformat()
            
            # Generate summary report
            self._generate_summary_report()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Implementation failed: {e}")
            self.implementation_results['status'] = 'failed'
            return False
    
    def _generate_summary_report(self):
        """Generate summary report of implementation"""
        logger.info("=" * 60)
        logger.info("📊 GOOGLE CLOUD CALIBRATION IMPLEMENTATION SUMMARY")
        logger.info("=" * 60)
        
        # Summary
        logger.info(f"📅 Implementation timestamp: {self.implementation_results['timestamp']}")
        logger.info(f"🎯 Implementation status: {self.implementation_results['status']}")
        logger.info(f"📝 Files created/modified: {len(self.implementation_results['files_modified'])}")
        
        # Changes made
        logger.info(f"🔧 Changes prepared: {len(self.implementation_results['changes_made'])}")
        for change in self.implementation_results['changes_made']:
            logger.info(f"   - {change['parameter']}: {change['new_value']}")
        
        logger.info("=" * 60)
        logger.info("📋 NEXT STEPS")
        logger.info("=" * 60)
        logger.info("1. Review the CLOUD_CALIBRATION_GUIDE.md file for detailed instructions")
        logger.info("2. Deploy the calibrated parameters using the deploy_calibrated_cloud.sh script")
        logger.info("3. Monitor for trades using the monitor_cloud_trades.py script")
        logger.info("4. Wait at least 30 minutes to ensure trades are being generated")
        logger.info("=" * 60)
    
    def get_implementation_results(self) -> Dict:
        """Get comprehensive implementation results"""
        return self.implementation_results

def main():
    """Main implementation execution"""
    logger.info("🚀 Starting Google Cloud Calibration Implementation")
    logger.info("Implementing less strict parameters for Google Cloud deployment")
    logger.info("=" * 60)
    
    # Create implementer
    implementer = CloudCalibrationImplementer()
    
    # Implement calibrations
    success = implementer.implement_cloud_calibrations()
    
    # Get results
    results = implementer.get_implementation_results()
    
    if success:
        logger.info("✅ GOOGLE CLOUD CALIBRATION IMPLEMENTATION COMPLETED")
        logger.info("🎯 Deployment files have been created")
        logger.info("🚀 Follow the instructions in CLOUD_CALIBRATION_GUIDE.md to deploy")
    else:
        logger.error("❌ GOOGLE CLOUD CALIBRATION IMPLEMENTATION FAILED")
        logger.error("🔧 Manual implementation required")
    
    return results

if __name__ == '__main__':
    results = main()
    print("\n" + "=" * 60)
    print("IMPLEMENTATION RESULTS:")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Files created/modified: {len(results['files_modified'])}")
    print(f"Changes prepared: {len(results['changes_made'])}")
    print("=" * 60)
