
import sys
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv("google-cloud-trading-system/.env")

# Add src to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)

from src.control_plane.outlook_engine import OutlookEngine

def debug_outlook():
    print("Initializing OutlookEngine...")
    engine = OutlookEngine()
    
    print("\n--- Analyzing XAU_USD (Daily) ---")
    # Access private method for debugging
    result = engine._analyze_instrument("XAU_USD", "daily")
    
    print(f"Instrument: {result.get('instrument')}")
    print(f"Bias: {result.get('bias')}")
    print(f"Bias Reason: {result.get('bias_reason')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Warnings: {result.get('warnings')}")
    
    print("\n--- Scenarios ---")
    for s in result.get('scenarios', []):
        print(f"- {s['name']}: {s['description']} ({s['probability']})")

if __name__ == "__main__":
    debug_outlook()
