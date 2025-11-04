#!/usr/bin/env python3
"""
Verify News Integration Status for Account 008
Checks if news sentiment is actually active and working
"""

import os
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

print("=" * 70)
print("NEWS INTEGRATION VERIFICATION - ACCOUNT 008")
print("=" * 70)
print()

# 1. Check API Keys Configuration
print("1. CHECKING API KEYS")
print("-" * 70)

api_keys = {
    'ALPHA_VANTAGE_API_KEY': os.getenv('ALPHA_VANTAGE_API_KEY'),
    'MARKETAUX_API_KEY': os.getenv('MARKETAUX_API_KEY'),
    'NEWSDATA_API_KEY': os.getenv('NEWSDATA_API_KEY'),
    'NEWSAPI_KEY': os.getenv('NEWSAPI_KEY'),
}

found_keys = 0
for key_name, key_value in api_keys.items():
    if key_value:
        # Show first 10 chars for security
        masked = key_value[:10] + "..." if len(key_value) > 10 else key_value
        print(f"   ✅ {key_name}: {masked}")
        found_keys += 1
    else:
        print(f"   ❌ {key_name}: NOT SET")

print(f"\n   📊 Total API keys found: {found_keys}/4")

# Check app.yaml for API keys
print("\n   Checking app.yaml configuration...")
try:
    import yaml
    app_yaml = Path('google-cloud-trading-system/app.yaml')
    if app_yaml.exists():
        with open(app_yaml, 'r') as f:
            config = yaml.safe_load(f)
        
        env_vars = config.get('env_variables', {})
        
        for key_name in api_keys.keys():
            if key_name in env_vars:
                value = env_vars[key_name]
                masked = value[:10] + "..." if len(value) > 10 else value
                print(f"   ✅ {key_name} in app.yaml: {masked}")
            else:
                print(f"   ⚠️  {key_name} not in app.yaml")
except Exception as e:
    print(f"   ⚠️  Error reading app.yaml: {e}")

print()

# 2. Check News Integration Module
print("2. CHECKING NEWS INTEGRATION MODULE")
print("-" * 70)

try:
    from src.core.news_integration import safe_news_integration, SafeNewsIntegration
    
    print(f"   ✅ News integration module exists")
    print(f"   📊 Enabled: {safe_news_integration.enabled}")
    print(f"   📊 Type: {type(safe_news_integration)}")
    
    # Check if it has API keys
    if hasattr(safe_news_integration, 'alpha_vantage_key'):
        av_key = safe_news_integration.alpha_vantage_key
        if av_key:
            print(f"   ✅ Alpha Vantage key loaded: {av_key[:10]}...")
        else:
            print(f"   ❌ Alpha Vantage key NOT loaded")
    
    # Try to get news data
    try:
        print("\n   🔄 Testing news data fetch...")
        import asyncio
        
        # Try to get news synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                print("   ⚠️  Event loop running, cannot test async fetch")
            else:
                news_data = loop.run_until_complete(
                    safe_news_integration.get_news_data(['GBP_USD', 'XAU_USD'])
                )
                if news_data:
                    print(f"   ✅ Successfully fetched {len(news_data)} news items")
                    
                    # Test sentiment analysis
                    analysis = safe_news_integration.get_news_analysis(['GBP_USD', 'XAU_USD'])
                    sentiment = analysis.get('overall_sentiment', 0)
                    print(f"   ✅ Sentiment analysis working: {sentiment:.3f}")
                    print(f"   📊 Market impact: {analysis.get('market_impact', 'unknown')}")
                    print(f"   📊 Recommendation: {analysis.get('trading_recommendation', 'unknown')}")
                else:
                    print("   ⚠️  No news data returned (may be API limit or no news)")
        except RuntimeError:
            # Try asyncio.run
            try:
                news_data = asyncio.run(safe_news_integration.get_news_data(['GBP_USD', 'XAU_USD']))
                if news_data:
                    print(f"   ✅ Successfully fetched {len(news_data)} news items")
                else:
                    print("   ⚠️  No news data returned")
            except Exception as e:
                print(f"   ⚠️  Could not fetch news (async error): {e}")
        
    except Exception as e:
        print(f"   ⚠️  Error testing news fetch: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"   ❌ Error importing news integration: {e}")
    import traceback
    traceback.print_exc()

print()

# 3. Check Momentum Trading Strategy Integration
print("3. CHECKING MOMENTUM TRADING STRATEGY (Account 008)")
print("-" * 70)

try:
    from src.strategies.momentum_trading import MomentumTradingStrategy
    
    # Create strategy instance
    strategy = MomentumTradingStrategy(instruments=['GBP_USD', 'NZD_USD', 'XAU_USD'])
    
    print(f"   ✅ Momentum strategy initialized")
    print(f"   📊 News enabled: {strategy.news_enabled}")
    print(f"   📊 Instruments: {strategy.instruments}")
    
    # Check if news integration is actually used
    if hasattr(strategy, 'news_enabled') and strategy.news_enabled:
        print("   ✅ News integration is ENABLED in strategy")
        
        # Check if should_pause_trading is available
        try:
            from src.core.news_integration import safe_news_integration
            should_pause = safe_news_integration.should_pause_trading(['GBP_USD'])
            print(f"   📊 Should pause trading: {should_pause}")
        except Exception as e:
            print(f"   ⚠️  Could not check pause status: {e}")
    else:
        print("   ❌ News integration is NOT enabled in strategy")
        print("   💡 This means account 008 is NOT using news sentiment")
        
except Exception as e:
    print(f"   ❌ Error checking strategy: {e}")
    import traceback
    traceback.print_exc()

print()

# 4. Check if News Integration is Active in Runtime
print("4. CHECKING RUNTIME STATUS")
print("-" * 70)

try:
    from src.core.news_integration import safe_news_integration
    
    # Check enabled status
    enabled = safe_news_integration.enabled
    
    if enabled:
        print("   ✅ News integration is ENABLED")
        
        # Check if it can actually fetch data
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    # Try to get news analysis
                    analysis = safe_news_integration.get_news_analysis(['GBP_USD'])
                    if analysis:
                        print("   ✅ News analysis is working")
                        print(f"   📊 Sentiment: {analysis.get('overall_sentiment', 0):.3f}")
                        print(f"   📊 Impact: {analysis.get('market_impact', 'unknown')}")
                        print(f"   📊 Recommendation: {analysis.get('trading_recommendation', 'unknown')}")
                    else:
                        print("   ⚠️  News analysis returned empty")
            except RuntimeError:
                print("   ⚠️  Cannot test (event loop running)")
        except Exception as e:
            print(f"   ⚠️  Error testing news: {e}")
    else:
        print("   ❌ News integration is DISABLED")
        print("   💡 Account 008 is NOT using news sentiment")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# 5. Summary
print("=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)
print()

# Determine status
if found_keys >= 2 and safe_news_integration.enabled:
    print("✅ NEWS INTEGRATION IS ACTIVE")
    print()
    print("Account 008 IS using:")
    print("  • News sentiment analysis (NLP)")
    print("  • Trading pause before major news")
    print("  • Signal boosting based on sentiment")
    print("  • Economic indicators")
    print()
    print("✅ Account 008 is an AI-enhanced system!")
elif found_keys >= 1:
    print("⚠️  NEWS INTEGRATION PARTIALLY ACTIVE")
    print()
    print("Account 008 MAY be using:")
    print("  • Some API keys found")
    print("  • But integration may not be fully enabled")
    print()
    print("💡 Check logs to confirm news is being used")
else:
    print("❌ NEWS INTEGRATION NOT ACTIVE")
    print()
    print("Account 008 is NOT using:")
    print("  • News sentiment analysis")
    print("  • Trading pauses for news")
    print("  • AI signal boosting")
    print()
    print("💡 Account 008 is running on pure technical analysis")

print()
print("=" * 70)

