#!/usr/bin/env python3
"""
OANDA API Client for Dashboard
Simplified OANDA client for dashboard market data
"""

import os
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class OandaClient:
    """Simplified OANDA API client for dashboard"""
    
    def __init__(self, api_key: str, account_id: str, environment: str = 'practice'):
        """Initialize OANDA client"""
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        
        if environment == 'practice':
            self.base_url = 'https://api-fxpractice.oanda.com'
        else:
            self.base_url = 'https://api-fxtrade.oanda.com'
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"✅ OANDA client initialized for account {account_id}")
    
    def get_current_prices(self, instruments: List[str]) -> Dict:
        """Get current prices for instruments"""
        try:
            # Convert instruments to OANDA format
            oanda_instruments = []
            for instrument in instruments:
                if '_' in instrument:
                    oanda_instruments.append(instrument.replace('_', '_'))
                else:
                    oanda_instruments.append(instrument)
            
            # Make API request
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {
                'instruments': ','.join(oanda_instruments)
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                
                for price_info in data.get('prices', []):
                    instrument = price_info['instrument']
                    bid = float(price_info['bids'][0]['price'])
                    ask = float(price_info['asks'][0]['price'])
                    
                    # Create price object
                    price_obj = type('PriceData', (), {
                        'bid': bid,
                        'ask': ask,
                        'timestamp': datetime.now().isoformat(),
                        'instrument': instrument
                    })()
                    
                    prices[instrument] = price_obj
                
                logger.info(f"✅ Retrieved prices for {len(prices)} instruments")
                return prices
                
            else:
                logger.error(f"❌ OANDA API error: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error getting prices: {e}")
            return {}
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Account info error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return None
