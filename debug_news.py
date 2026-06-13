
import sys
import os
import logging
import json
from datetime import datetime

# Add workspace root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_news")

print("--- DEBUG NEWS START ---")

try:
    from src.control_plane.news_provider import fetch_news_with_registry
    
    print("Fetching news...")
    # Add query parameter (required)
    items, status = fetch_news_with_registry(query="finance")
    
    # Simulate news context construction from working_trading_system.py
    # working_trading_system.py seems to call fetch_news_with_registry then wrap it
    
    print(f"Status: {status}")
    print(f"Item Count: {len(items)}")
    
    print(f"Top 5 Items:")
    trigger_found = False
    for i, item in enumerate(items[:15]): # Check top 15 to be safe
        impact = (item.get("impact") or "").lower()
        category = (item.get("category") or "").lower() # NewsProvider might not return category in dict, check source
        title = item.get("title", "")
        
        print(f"  {i+1}. [{impact}] {title} (Cat: {category})")
        
        if impact == "high" or category == "central_banks":
            print(f"     !!! TRIGGER FOUND: Impact={impact}, Category={category} !!!")
            trigger_found = True

    if not trigger_found:
        print("No high impact or central bank news found in top items.")

except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Runtime Error: {e}")

print("--- DEBUG NEWS END ---")
