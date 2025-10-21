#!/usr/bin/env python3
"""
Fix syntax errors in price_context_analyzer.py
"""

import re

# Read the file
with open('/Users/mac/quant_system_clean/google-cloud-trading-system/src/core/price_context_analyzer.py', 'r') as f:
    content = f.read()

# Fix the main function
main_function = """
if __name__ == "__main__":
    # Test price context analyzer
    import yfinance as yf
    
    analyzer = get_price_context_analyzer()
    
    # Download some test data
    symbol = "EURUSD=X"
    data = yf.download(symbol, period="60d", interval="1h")
    
    # Convert to expected format
    df = pd.DataFrame({
        "open": data["Open"],
        "high": data["High"],
        "low": data["Low"],
        "close": data["Close"],
        "volume": data["Volume"]
    })
    
    # Create multi-timeframe data
    price_data = {
        "H1": df
    }
    
    # Analyze price context
    contexts = analyzer.analyze_price_context("EUR_USD", price_data)
    
    # Print results
    for timeframe, context in contexts.items():
        print(f"\\nTimeframe: {timeframe}")
        print(f"Trend: {context.trend}")
        print(f"Momentum: {context.momentum:.2f}")
        print(f"Volatility: {context.volatility:.4f}")
        
        print(f"\\nSupport Levels:")
        for level in context.support_levels[:3]:
            print(f"- {level.price:.5f} (Strength: {level.strength:.1f}, Touches: {level.touches})")
        
        print(f"\\nResistance Levels:")
        for level in context.resistance_levels[:3]:
            print(f"- {level.price:.5f} (Strength: {level.strength:.1f}, Touches: {level.touches})")
        
        print(f"\\nPatterns:")
        for pattern in context.patterns:
            print(f"- {pattern.pattern.value} (Strength: {pattern.strength:.1f})")
    
    # Get trade context
    current_price = df["close"].iloc[-1]
    trade_context = analyzer.get_trade_context("EUR_USD", current_price, contexts)
    
    print("\\nTrade Context:")
    print(f"Overall Trend: {trade_context['overall_trend']}")
    print(f"Nearest Support: {trade_context['nearest_support']:.5f}" if trade_context['nearest_support'] else "No support found")
    print(f"Nearest Resistance: {trade_context['nearest_resistance']:.5f}" if trade_context['nearest_resistance'] else "No resistance found")
    print(f"Risk-Reward: {trade_context['risk_reward']:.2f}")
"""

# Replace the main function
pattern = r"if __name__ == \"__main__\":(.*?)(?=\n\n|$)"
content = re.sub(pattern, main_function, content, flags=re.DOTALL)

# Write the fixed file
with open('/Users/mac/quant_system_clean/google-cloud-trading-system/src/core/price_context_analyzer.py', 'w') as f:
    f.write(content)

print("✅ Fixed price_context_analyzer.py")
