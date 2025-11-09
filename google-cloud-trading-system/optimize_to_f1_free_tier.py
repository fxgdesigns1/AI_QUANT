#!/usr/bin/env python3
"""
OPTIMIZE TO F1 FREE TIER
Switches from F2 to F1 instance for maximum cost savings (potentially FREE!)
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_f1_optimized_app_yaml():
    """Create F1 optimized app.yaml for FREE TIER usage"""
    logger.info("🔧 Creating F1 FREE TIER optimized configuration...")
    
    app_yaml_content = """# Google Cloud Trading System - F1 FREE TIER OPTIMIZED
# Optimized for maximum cost savings using Google Cloud Free Tier

# =============================================================================
# Runtime Configuration
# =============================================================================
runtime: python311

# =============================================================================
# Service Configuration
# =============================================================================
service: default
entrypoint: python main.py

# =============================================================================
# F1 FREE TIER OPTIMIZATION
# =============================================================================
automatic_scaling:
  # FREE TIER: 28 instance-hours per day (F1 only)
  min_instances: 1
  max_instances: 1
  
  # Optimized for F1 efficiency
  target_cpu_utilization: 0.9
  target_throughput_utilization: 0.9
  
  # Faster response times for F1
  min_pending_latency: 5ms
  max_pending_latency: 50ms

# =============================================================================
# Instance Configuration - F1 FREE TIER
# =============================================================================
instance_class: F1

# =============================================================================
# Environment Variables - F1 OPTIMIZED
# =============================================================================
env_variables:
  # Flask Configuration
  FLASK_ENV: production
  FLASK_DEBUG: "False"
  PORT: "8080"
  
  # OANDA API Configuration
  OANDA_API_KEY: "REMOVED_SECRET"
  OANDA_ENVIRONMENT: "practice"
  OANDA_BASE_URL: "https://api-fxpractice.oanda.com"
  
  # F1 FREE TIER OPTIMIZATION
  F1_FREE_TIER_MODE: "true"
  ULTRA_OPTIMIZED_RESOURCE_USAGE: "true"
  MINIMAL_MEMORY_USAGE: "true"
  
  # Strategy Groups - All 3 on F1 instance
  GROUP_1_ACCOUNT: "101-004-30719775-008"
  GROUP_2_ACCOUNT: "101-004-30719775-007"
  GROUP_3_ACCOUNT: "101-004-30719775-006"
  
  # Account Configuration
  OANDA_ACCOUNT_ID: "101-004-30719775-008"
  PRIMARY_ACCOUNT: "101-004-30719775-008"
  GOLD_SCALP_ACCOUNT: "101-004-30719775-007"
  STRATEGY_ALPHA_ACCOUNT: "101-004-30719775-006"
  
  # Top 3 Optimized Strategies
  TOP_STRATEGY_1_ACCOUNT: "101-004-30719775-008"
  TOP_STRATEGY_2_ACCOUNT: "101-004-30719775-007"
  TOP_STRATEGY_3_ACCOUNT: "101-004-30719775-006"
  
  # Strategy Mapping
  PRIMARY_STRATEGY: "gbp_usd_5m_strategy_rank_1"
  GOLD_SCALP_STRATEGY: "gbp_usd_5m_strategy_rank_2"
  STRATEGY_ALPHA_STRATEGY: "gbp_usd_5m_strategy_rank_3"
  
  # Telegram Configuration
  TELEGRAM_TOKEN: "${TELEGRAM_TOKEN}"
  TELEGRAM_CHAT_ID: "${TELEGRAM_CHAT_ID}"
  
  # Google Cloud Configuration
  GOOGLE_CLOUD_PROJECT: "ai-quant-trading"
  GOOGLE_CLOUD_REGION: "us-central1"
  
  # F1 OPTIMIZED Risk Management
  PRIMARY_MAX_RISK_PER_TRADE: "0.015"
  PRIMARY_MAX_PORTFOLIO_RISK: "0.6"
  PRIMARY_MAX_POSITIONS: "3"
  PRIMARY_DAILY_TRADE_LIMIT: "8"
  
  GOLD_MAX_RISK_PER_TRADE: "0.01"
  GOLD_MAX_PORTFOLIO_RISK: "0.6"
  GOLD_MAX_POSITIONS: "2"
  GOLD_DAILY_TRADE_LIMIT: "6"
  
  ALPHA_MAX_RISK_PER_TRADE: "0.02"
  ALPHA_MAX_PORTFOLIO_RISK: "0.6"
  ALPHA_MAX_POSITIONS: "4"
  ALPHA_DAILY_TRADE_LIMIT: "8"
  
  # Global Risk Settings
  MAX_CORRELATION_RISK: "0.6"
  POSITION_SIZING_METHOD: "risk_based"
  POSITION_SIZE_MULTIPLIER: "0.3"
  FORCED_TRADING_MODE: "enabled"
  MIN_TRADES_TODAY: "1"
  
  # Data Validation Settings
  MAX_DATA_AGE_SECONDS: "600"
  MIN_CONFIDENCE_THRESHOLD: "0.6"
  REQUIRE_LIVE_DATA: "True"
  
  # Trading System Configuration
  MOCK_TRADING: "False"
  DEVELOPMENT_MODE: "False"
  
  # Logging Configuration
  LOG_LEVEL: "WARNING"
  ENABLE_STRUCTURED_LOGGING: "False"
  
  # F1 OPTIMIZED Performance Settings
  DASHBOARD_UPDATE_INTERVAL: "60"
  MARKET_DATA_UPDATE_INTERVAL: "30"
  SYSTEM_STATUS_CHECK_INTERVAL: "120"
  
  # Security Settings
  API_RATE_LIMIT: "50"
  API_RATE_WINDOW: "60"
  CORS_ORIGINS: "*"
  
  # News API Configuration
  ALPHA_VANTAGE_API_KEY: "${ALPHA_VANTAGE_API_KEY}"
  MARKETAUX_API_KEY: "${MARKETAUX_API_KEY}"
  NEWSDATA_API_KEY: "pub_1234567890abcdef"
  NEWSAPI_KEY: "your_newsapi_key"
  
  # News Integration Settings - F1 OPTIMIZED
  NEWS_TRADING_ENABLED: "True"
  HIGH_IMPACT_PAUSE: "True"
  NEGATIVE_SENTIMENT_THRESHOLD: "-0.4"
  POSITIVE_SENTIMENT_THRESHOLD: "0.4"
  NEWS_CONFIDENCE_THRESHOLD: "0.7"
  
  # News API Performance - REDUCED for F1
  NEWS_COLLECTION_INTERVAL: "600"
  CACHE_DEFAULT_TTL: "30"
  API_REQUEST_TIMEOUT: "60"

  # AI Assistant Configuration - F1 OPTIMIZED
  AI_ASSISTANT_ENABLED: "true"
  AI_MODEL_PROVIDER: "demo"
  AI_RATE_LIMIT_PER_MINUTE: "5"
  AI_REQUIRE_LIVE_CONFIRMATION: "true"
  
  # Live actions toggle
  ALLOW_LIVE_ACTIONS: "true"
  
  # Weekend mode configuration
  WEEKEND_MODE: "true"
  TRADING_DISABLED: "true"
  SIGNAL_GENERATION: "disabled"

  # Secure manual scan trigger token
  SCAN_TRIGGER_TOKEN: "${SCAN_TRIGGER_TOKEN}"

# =============================================================================
# Handlers Configuration
# =============================================================================
handlers:
  # Static files handler
  - url: /static
    static_dir: static
    secure: always
    
  # Task endpoints
  - url: /tasks/full_scan
    script: auto
    secure: always
  - url: /tasks/full_scan_public
    script: auto
    secure: always
  - url: /tasks/progressive_scan
    script: auto
    secure: always
  - url: /tasks/.*
    script: auto
    secure: always
    login: admin
  - url: /.*
    script: auto
    secure: always

# =============================================================================
# Network Configuration - F1 OPTIMIZED
# =============================================================================
network:
  # Session affinity for F1
  session_affinity: true
  
  # Forwarded port configuration
  forwarded_ports:
    - 8080

# =============================================================================
# Health Check Configuration - F1 OPTIMIZED
# =============================================================================
readiness_check:
  path: "/api/health"
  check_interval_sec: 30
  timeout_sec: 10
  failure_threshold: 5
  success_threshold: 2
  app_start_timeout_sec: 600

liveness_check:
  path: "/api/health"
  check_interval_sec: 60
  timeout_sec: 10
  failure_threshold: 5
  success_threshold: 2

# =============================================================================
# Resource Limits - F1 FREE TIER
# =============================================================================
resources:
  cpu: 0.2
  memory_gb: 0.2
  disk_size_gb: 5

# =============================================================================
# Beta Features
# =============================================================================
beta_settings:
  # Enable Cloud Build for automatic deployments
  cloud_build: true
"""
    
    # Write the F1 optimized app.yaml
    with open("app_f1_free_tier.yaml", 'w') as f:
        f.write(app_yaml_content)
    
    logger.info("✅ F1 FREE TIER app.yaml created: app_f1_free_tier.yaml")
    return True

def create_f1_deployment_script():
    """Create deployment script for F1 free tier"""
    logger.info("📝 Creating F1 FREE TIER deployment script...")
    
    deployment_script = """#!/bin/bash
# Deploy F1 FREE TIER Optimized Version
# Maximum cost savings: F2 ($60-90/month) → F1 (FREE!)

echo "🚀 DEPLOYING F1 FREE TIER OPTIMIZATION"
echo "======================================"
echo "Cost Reduction: 100% (F2 → F1 FREE TIER)"
echo "Strategy Groups: All 3 groups on 1 F1 instance"
echo "FREE TIER: 28 instance-hours per day"
echo ""

# Backup current app.yaml
cp app.yaml app_f2_backup.yaml
echo "✅ Backed up current F2 app.yaml"

# Use F1 optimized configuration
cp app_f1_free_tier.yaml app.yaml
echo "✅ Applied F1 FREE TIER optimization"

# Deploy to Google Cloud
echo "📦 Deploying F1 FREE TIER version..."
gcloud app deploy --version=f1-free-tier-$(date +%Y%m%d-%H%M%S) --no-promote

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 F1 FREE TIER DEPLOYMENT SUCCESSFUL!"
    echo "===================================="
    echo "✅ All 3 strategy groups running on 1 F1 instance"
    echo "💰 Cost reduction: 100% (FREE!)"
    echo "📊 FREE TIER: 28 hours/day (perfect for trading)"
    echo ""
    echo "🔍 Verify deployment:"
    echo "gcloud app versions list --service=default"
    echo ""
    echo "📊 Monitor FREE TIER usage:"
    echo "gcloud app logs tail -s default"
    echo ""
    echo "🚀 TO ACTIVATE:"
    echo "gcloud app services set-traffic default --splits=VERSION_ID=1.0"
else
    echo "❌ Deployment failed - restoring backup"
    cp app_f2_backup.yaml app.yaml
    echo "✅ Restored original F2 configuration"
    exit 1
fi
"""
    
    with open("deploy_f1_free_tier.sh", 'w') as f:
        f.write(deployment_script)
    
    # Make executable
    os.chmod("deploy_f1_free_tier.sh", 0o755)
    
    logger.info("✅ F1 deployment script created: deploy_f1_free_tier.sh")
    return True

def main():
    """Main F1 optimization function"""
    logger.info("🔧 OPTIMIZING TO F1 FREE TIER FOR MAXIMUM COST SAVINGS")
    logger.info("=" * 65)
    logger.info(f"Optimization Time: {datetime.now().isoformat()}")
    logger.info("")
    
    # Step 1: Create F1 optimized app.yaml
    if not create_f1_optimized_app_yaml():
        logger.error("❌ Failed to create F1 optimized app.yaml")
        return False
    
    # Step 2: Create deployment script
    if not create_f1_deployment_script():
        logger.error("❌ Failed to create F1 deployment script")
        return False
    
    # Final summary
    logger.info("")
    logger.info("🎉 F1 FREE TIER OPTIMIZATION READY!")
    logger.info("=" * 50)
    logger.info("✅ F1 optimized app.yaml created")
    logger.info("✅ Deployment script ready")
    logger.info("")
    logger.info("💰 COST SAVINGS:")
    logger.info("   Current F2: $60-90/month")
    logger.info("   F1 FREE TIER: $0/month (28 hours/day)")
    logger.info("   Savings: 100% reduction!")
    logger.info("")
    logger.info("🚀 TO DEPLOY:")
    logger.info("   ./deploy_f1_free_tier.sh")
    logger.info("")
    logger.info("✅ F1 FREE TIER BENEFITS:")
    logger.info("   • 28 instance-hours per day FREE")
    logger.info("   • Perfect for trading hours (8-10 hours/day)")
    logger.info("   • All 3 strategy groups supported")
    logger.info("   • Optimized for minimal resource usage")
    logger.info("")
    logger.info("⚠️  CONSIDERATIONS:")
    logger.info("   • F1 has 0.2 vCPU, 0.2GB RAM (vs F2: 1 vCPU, 2GB)")
    logger.info("   • Reduced update frequencies for efficiency")
    logger.info("   • Lower risk limits to match capacity")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 F1 FREE TIER optimization ready!")
        print("Run: ./deploy_f1_free_tier.sh")
    else:
        print("\n❌ F1 optimization failed!")
        print("Please check the logs.")




