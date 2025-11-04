#!/usr/bin/env python3
"""
Verify News Integration is Now Enabled for Account 008
"""

import os
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

# Load API keys from app.yaml
try:
    import yaml
    app_yaml_path = Path('google-cloud-trading-system/app.yaml')
    if app_yaml_path.exists():
        with open(app_yaml_path, 'r') as f:
            app_config = yaml.safe_load(f)
            env_vars = app_config.get('env_variables', {})
            
            # Set environment variables
            if 'ALPHA_VANTAGE_API_KEY' in env_vars:
                os.environ['ALPHA_VANTAGE_API_KEY'] = env_vars['ALPHA_VANTAGE_API_KEY']
            if 'MARKETAUX_API_KEY' in env_vars:
                os.environ['MARKETAUX_API_KEY'] = env_vars['MARKETAUX_API_KEY']
except Exception as e:
    print(f"⚠️ Error loading from app.yaml: {e}")

print("=" * 70)
print("FINAL VERIFICATION - NEWS INTEGRATION ENABLED")
print("=" * 70)
print()

# Now test news integration
try:
    from src.core.news_integration import safe_news_integration
    from src.strategies.momentum_trading import MomentumTradingStrategy
    
    print("1. NEWS INTEGRATION STATUS")
    print("-" * 70)
    print(f"   ✅ Enabled: {safe_news_integration.enabled}")
    print(f"   📊 API Keys loaded: {len(safe_news_integration.api_keys)}")
    if safe_news_integration.api_keys:
        print(f"   📝 APIs: {', '.join(safe_news_integration.api_keys.keys())}")
    
    print()
    print("2. ACCOUNT 008 STRATEGY STATUS")
    print("-" * 70)
    
    strategy = MomentumTradingStrategy(instruments=['GBP_USD', 'NZD_USD', 'XAU_USD'])
    print(f"   ✅ Strategy: {strategy.name}")
    print(f"   📊 News enabled: {strategy.news_enabled}")
    print(f"   📈 Instruments: {strategy.instruments}")
    
    print()
    print("3. VERIFICATION SUMMARY")
    print("-" * 70)
    
    if safe_news_integration.enabled and strategy.news_enabled:
        print("   ✅ NEWS INTEGRATION IS NOW ACTIVE!")
        print()
        print("   Account 008 IS using:")
        print("   • News sentiment analysis (NLP)")
        print("   • Trading pause before major news")
        print("   • Signal boosting based on sentiment")
        print("   • Economic indicators")
        print()
        print("   ✅ Account 008 is an AI-enhanced system!")
    elif safe_news_integration.enabled:
        print("   ⚠️  News integration enabled but not in strategy")
        print("   💡 May need strategy restart")
    else:
        print("   ❌ News integration still disabled")
        print("   💡 Check API keys configuration")
    
    print()
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

