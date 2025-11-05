#!/usr/bin/env python3
"""
Inspect OANDA data format to understand the structure
"""

import os
import sys
import yaml
import logging
import json

sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Import required modules
from src.core.oanda_client import OandaClient

def main():
    """Inspect OANDA data format"""
    client = OandaClient()
    
    # Get candles for XAU_USD
    logger.info("Fetching XAU_USD candles...")
    response = client.get_candles(
        instrument="XAU_USD",
        granularity="M5",
        count=5
    )
    
    # Print raw response
    logger.info("Raw response:")
    print(json.dumps(response, indent=2))
    
    # Analyze structure
    logger.info("\nAnalyzing response structure:")
    if not response:
        logger.error("Empty response")
        return
    
    if 'candles' not in response:
        logger.error("No 'candles' key in response")
        return
    
    candles = response['candles']
    logger.info(f"Number of candles: {len(candles)}")
    
    if not candles:
        logger.error("Empty candles list")
        return
    
    # Analyze first candle
    first_candle = candles[0]
    logger.info(f"First candle keys: {list(first_candle.keys())}")
    
    # Check if 'mid' exists and its structure
    if 'mid' in first_candle:
        logger.info(f"'mid' structure: {first_candle['mid']}")
        logger.info(f"'mid' type: {type(first_candle['mid'])}")
    else:
        logger.info("No 'mid' key in candle")
        
        # Check for alternative price data
        for key in first_candle.keys():
            if key not in ['time', 'volume', 'complete']:
                logger.info(f"Alternative price data key: {key}")
                logger.info(f"Value: {first_candle[key]}")
    
    # Check time format
    if 'time' in first_candle:
        logger.info(f"Time format: {first_candle['time']}")
    
    # Try to create a simple working example
    logger.info("\nAttempting to process candles:")
    for i, candle in enumerate(candles):
        try:
            # Extract time
            time = candle.get('time', 'Unknown')
            
            # Try different ways to extract price data
            if 'mid' in candle and isinstance(candle['mid'], dict):
                close = float(candle['mid'].get('c', 0))
            elif 'ask' in candle and isinstance(candle['ask'], dict):
                close = float(candle['ask'].get('c', 0))
            elif 'bid' in candle and isinstance(candle['bid'], dict):
                close = float(candle['bid'].get('c', 0))
            elif isinstance(candle.get('c'), str):
                close = float(candle['c'])
            else:
                close = "Unknown"
                
            logger.info(f"Candle {i+1}: Time={time}, Close={close}")
        except Exception as e:
            logger.error(f"Error processing candle {i+1}: {e}")
            logger.error(f"Candle data: {candle}")

if __name__ == "__main__":
    main()



