#!/usr/bin/env python3
"""
Google Cloud System Connection Client
Connects to the cloud trading system for performance metrics and controls
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
import time

logger = logging.getLogger(__name__)

class CloudSystemClient:
    """HTTP client for connecting to Google Cloud trading system"""
    
    def __init__(self):
        """Initialize client with configuration"""
        self.cloud_url = os.getenv('CLOUD_SYSTEM_URL', 'https://ai-quant-trading.uc.r.appspot.com')
        self.fallback_url = os.getenv('CLOUD_FALLBACK_URL', 'http://localhost:8080')
        self.timeout = int(os.getenv('CLOUD_TIMEOUT', '10'))
        self.cache_ttl = int(os.getenv('CLOUD_CACHE_TTL', '15'))
        
        # Cache for responses
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.connection_status = {'online': False, 'last_check': None, 'last_error': None}
        
        logger.info(f"✅ Cloud System Client initialized: {self.cloud_url}")
    
    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired"""
        with self.cache_lock:
            if key in self.cache:
                cached = self.cache[key]
                age = (datetime.now() - cached['timestamp']).total_seconds()
                if age < self.cache_ttl:
                    return cached['data']
                else:
                    del self.cache[key]
        return None
    
    def _set_cached(self, key: str, data: Dict[str, Any]):
        """Cache response with timestamp"""
        with self.cache_lock:
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            # Clean old cache entries (keep only last 50)
            if len(self.cache) > 50:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP request to cloud system"""
        try:
            url = f"{self.cloud_url}{endpoint}"
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            self.connection_status = {
                'online': True,
                'last_check': datetime.now(),
                'last_error': None
            }
            
            return response.json()
        except requests.exceptions.RequestException as e:
            self.connection_status = {
                'online': False,
                'last_check': datetime.now(),
                'last_error': str(e)
            }
            logger.warning(f"⚠️ Cloud system request failed: {e}")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from cloud system"""
        cache_key = 'performance_metrics'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Try primary endpoint
        data = self._make_request('/api/metrics')
        if data:
            self._set_cached(cache_key, data)
            return data
        
        # Try fallback endpoint
        data = self._make_request('/api/performance')
        if data:
            self._set_cached(cache_key, data)
            return data
        
        # Return default if both fail
        return {
            'status': 'offline',
            'error': 'Cloud system unavailable'
        }
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get trading status from cloud system"""
        cache_key = 'trading_status'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        data = self._make_request('/api/strategies/status')
        if data:
            self._set_cached(cache_key, data)
            return data
        
        return {
            'status': 'offline',
            'error': 'Cloud system unavailable'
        }
    
    def get_opportunities(self) -> Dict[str, Any]:
        """Get trading opportunities from cloud system"""
        cache_key = 'opportunities'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        data = self._make_request('/api/opportunities')
        if data:
            self._set_cached(cache_key, data)
            return data
        
        return {
            'status': 'offline',
            'opportunities': []
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check cloud system health"""
        data = self._make_request('/api/health')
        if data:
            return {
                'status': 'healthy',
                'details': data
            }
        return {
            'status': 'unhealthy',
            'details': self.connection_status
        }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""
        return {
            'online': self.connection_status['online'],
            'cloud_url': self.cloud_url,
            'last_check': self.connection_status['last_check'].isoformat() if self.connection_status['last_check'] else None,
            'last_error': self.connection_status['last_error']
        }
    
    def send_control_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send control action to cloud system"""
        try:
            url = f"{self.cloud_url}/api/controls/{action}"
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Control action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
_cloud_client: Optional[CloudSystemClient] = None

def get_cloud_client() -> CloudSystemClient:
    """Get or create global cloud client instance"""
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = CloudSystemClient()
    return _cloud_client
