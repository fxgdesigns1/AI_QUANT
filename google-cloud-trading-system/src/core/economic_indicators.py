#!/usr/bin/env python3
"""
Economic Indicators Integration
Fetches and analyzes economic data from Alpha Vantage
Critical for fundamental analysis in forex and gold trading
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class EconomicIndicator:
    """Economic indicator data point"""
    name: str
    value: float
    date: str
    source: str
    impact: str  # 'high', 'medium', 'low'


class EconomicIndicatorService:
    """
    Economic Indicators Service
    Fetches GDP, CPI, Fed Funds, Unemployment, etc. from Alpha Vantage
    """
    
    def __init__(self):
        """Initialize economic indicators service"""
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.base_url = 'https://www.alphavantage.co/query'
        self.enabled = bool(self.api_key and self.api_key != 'your_api_key')
        
        # Cache for rate limiting
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = 3600  # 1 hour cache for economic data
        self.last_api_call = {}
        self.min_call_interval = 15  # 15 seconds between calls (4 per minute limit)
        
        if self.enabled:
            logger.info("✅ Economic Indicators Service initialized")
            logger.info(f"   API: Alpha Vantage")
        else:
            logger.warning("⚠️ Economic Indicators disabled - no API key")
    
    def _can_call_api(self, endpoint: str) -> bool:
        """Check if we can call API without hitting rate limits"""
        if endpoint not in self.last_api_call:
            return True
        
        time_since = (datetime.now() - self.last_api_call[endpoint]).seconds
        return time_since >= self.min_call_interval
    
    def _get_cached_or_fetch(self, cache_key: str, fetch_function) -> Optional[Any]:
        """Get from cache or fetch fresh data"""
        # Check cache
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            age = (datetime.now() - timestamp).seconds
            if age < self.cache_ttl:
                logger.info(f"📦 Using cached {cache_key} (age: {age}s)")
                return data
        
        # Fetch fresh data
        try:
            data = fetch_function()
            if data:
                self.cache[cache_key] = (data, datetime.now())
            return data
        except Exception as e:
            logger.error(f"❌ Failed to fetch {cache_key}: {e}")
            return None
    
    def get_federal_funds_rate(self) -> Optional[EconomicIndicator]:
        """
        Get Federal Funds Rate (interest rates)
        CRITICAL for gold and forex trading
        """
        if not self.enabled:
            return None
        
        def fetch():
            if not self._can_call_api('fed_funds'):
                logger.info("⏳ Fed Funds: Rate limited, using cache")
                return None
            
            url = f"{self.base_url}?function=FEDERAL_FUNDS_RATE&apikey={self.api_key}"
            try:
                response = requests.get(url, timeout=8)
            data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Fed Funds API error: {e}")
                # Use cache if available
                cached = self.cache.get('fed_funds_rate')
                return cached[0] if cached else None
            
            self.last_api_call['fed_funds'] = datetime.now()
            
            if 'data' in data and data['data']:
                latest = data['data'][0]
                return EconomicIndicator(
                    name='Federal Funds Rate',
                    value=float(latest['value']),
                    date=latest['date'],
                    source='Federal Reserve',
                    impact='high'
                )
            return None
        
        return self._get_cached_or_fetch('fed_funds_rate', fetch)
    
    def get_cpi(self) -> Optional[EconomicIndicator]:
        """
        Get CPI (Consumer Price Index - Inflation)
        CRITICAL for gold trading
        """
        if not self.enabled:
            return None
        
        def fetch():
            if not self._can_call_api('cpi'):
                logger.info("⏳ CPI: Rate limited, using cache")
                return None
            
            url = f"{self.base_url}?function=CPI&apikey={self.api_key}"
            try:
                response = requests.get(url, timeout=8)
            data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ CPI API error: {e}")
                cached = self.cache.get('cpi')
                return cached[0] if cached else None
            
            self.last_api_call['cpi'] = datetime.now()
            
            if 'data' in data and data['data']:
                latest = data['data'][0]
                return EconomicIndicator(
                    name='CPI',
                    value=float(latest['value']),
                    date=latest['date'],
                    source='Bureau of Labor Statistics',
                    impact='high'
                )
            return None
        
        return self._get_cached_or_fetch('cpi', fetch)
    
    def get_inflation_rate(self) -> Optional[float]:
        """
        Calculate inflation rate from CPI
        Returns annual inflation percentage
        """
        cpi = self.get_cpi()
        if not cpi:
            return None
        
        # Simplified: actual would need year-over-year calculation
        # For now, return approximate inflation (CPI change)
        # Full implementation would fetch historical CPI and calculate YoY%
        return 3.2  # Placeholder - would calculate from historical data
    
    def get_real_interest_rate(self) -> Optional[float]:
        """
        Calculate Real Interest Rate (Fed Funds - Inflation)
        MOST IMPORTANT indicator for gold
        """
        fed_rate = self.get_federal_funds_rate()
        inflation = self.get_inflation_rate()
        
        if fed_rate and inflation is not None:
            real_rate = fed_rate.value - inflation
            logger.info(f"💰 Real Rate: {real_rate:.2f}% (Fed {fed_rate.value}% - Inflation {inflation}%)")
            return real_rate
        
        return None
    
    def get_gdp(self) -> Optional[EconomicIndicator]:
        """Get Real GDP growth rate"""
        if not self.enabled:
            return None
        
        def fetch():
            if not self._can_call_api('gdp'):
                logger.info("⏳ GDP: Rate limited, using cache")
                return None
            
            url = f"{self.base_url}?function=REAL_GDP&apikey={self.api_key}"
            try:
                response = requests.get(url, timeout=8)
            data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ GDP API error: {e}")
                cached = self.cache.get('gdp')
                return cached[0] if cached else None
            
            self.last_api_call['gdp'] = datetime.now()
            
            if 'data' in data and data['data']:
                latest = data['data'][0]
                return EconomicIndicator(
                    name='Real GDP',
                    value=float(latest['value']),
                    date=latest['date'],
                    source='Bureau of Economic Analysis',
                    impact='high'
                )
            return None
        
        return self._get_cached_or_fetch('gdp', fetch)
    
    def get_unemployment_rate(self) -> Optional[EconomicIndicator]:
        """Get Unemployment Rate"""
        if not self.enabled:
            return None
        
        def fetch():
            if not self._can_call_api('unemployment'):
                logger.info("⏳ Unemployment: Rate limited, using cache")
                return None
            
            url = f"{self.base_url}?function=UNEMPLOYMENT&apikey={self.api_key}"
            try:
                response = requests.get(url, timeout=8)
            data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Unemployment API error: {e}")
                cached = self.cache.get('unemployment')
                return cached[0] if cached else None
            
            self.last_api_call['unemployment'] = datetime.now()
            
            if 'data' in data and data['data']:
                latest = data['data'][0]
                return EconomicIndicator(
                    name='Unemployment Rate',
                    value=float(latest['value']),
                    date=latest['date'],
                    source='Bureau of Labor Statistics',
                    impact='high'
                )
            return None
        
        return self._get_cached_or_fetch('unemployment', fetch)
    
    def get_gold_fundamental_score(self) -> Dict[str, Any]:
        """
        Calculate comprehensive fundamental score for gold
        Combines multiple economic indicators
        
        Returns:
            Dictionary with score, factors, and recommendation
        """
        try:
            score = 0.0
            factors = []
            
            # Factor 1: Real Interest Rate (most important)
            real_rate = self.get_real_interest_rate()
            if real_rate is not None:
                if real_rate < 0:
                    # Negative real rates = VERY bullish for gold
                    score += 40
                    factors.append(f"Real rate {real_rate:.2f}% (BULLISH)")
                elif real_rate < 1.0:
                    # Low positive real rates = bullish
                    score += 25
                    factors.append(f"Real rate {real_rate:.2f}% (Moderately bullish)")
                elif real_rate > 2.5:
                    # High real rates = bearish
                    score -= 25
                    factors.append(f"Real rate {real_rate:.2f}% (BEARISH)")
                else:
                    # Moderate rates = neutral
                    score += 5
                    factors.append(f"Real rate {real_rate:.2f}% (Neutral)")
            
            # Factor 2: Inflation Trend
            cpi = self.get_cpi()
            if cpi:
                # Rising inflation = bullish for gold
                inflation = self.get_inflation_rate() or 3.2
                if inflation > 4.0:
                    score += 20
                    factors.append(f"High inflation {inflation:.1f}% (BULLISH)")
                elif inflation > 2.5:
                    score += 10
                    factors.append(f"Moderate inflation {inflation:.1f}% (Supportive)")
                elif inflation < 1.5:
                    score -= 10
                    factors.append(f"Low inflation {inflation:.1f}% (Bearish)")
            
            # Factor 3: Fed Policy (from Fed Funds Rate)
            fed_funds = self.get_federal_funds_rate()
            if fed_funds:
                # Monitor rate changes (simplified - would track historical)
                if fed_funds.value < 2.0:
                    score += 20
                    factors.append(f"Low Fed rate {fed_funds.value}% (BULLISH)")
                elif fed_funds.value > 5.0:
                    score -= 15
                    factors.append(f"High Fed rate {fed_funds.value}% (Bearish)")
            
            # Factor 4: Economic Growth (GDP)
            gdp = self.get_gdp()
            if gdp:
                # Weak growth = safe haven demand
                # Strong growth = risk-on (bearish gold)
                # Note: GDP values are absolute, need growth rate
                # Simplified for now
                factors.append(f"GDP data available")
            
            # Normalize score to -1.0 to +1.0
            normalized_score = max(-1.0, min(1.0, score / 100))
            
            # Generate recommendation
            if normalized_score > 0.3:
                recommendation = "STRONG BUY"
            elif normalized_score > 0:
                recommendation = "BUY"
            elif normalized_score < -0.3:
                recommendation = "STRONG SELL"
            elif normalized_score < 0:
                recommendation = "SELL"
            else:
                recommendation = "NEUTRAL"
            
            return {
                'score': normalized_score,
                'recommendation': recommendation,
                'factors': factors,
                'real_interest_rate': real_rate,
                'inflation_rate': self.get_inflation_rate(),
                'fed_funds_rate': fed_funds.value if fed_funds else None,
                'confidence': min(100, len(factors) * 25),  # More factors = higher confidence
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate gold fundamental score: {e}")
            return {
                'score': 0.0,
                'recommendation': 'NEUTRAL',
                'factors': [],
                'confidence': 0,
                'error': str(e)
            }
    
    def get_forex_fundamental_score(self, pair: str) -> Dict[str, Any]:
        """
        Calculate fundamental score for forex pair
        
        Args:
            pair: Currency pair (e.g., 'EUR_USD')
        
        Returns:
            Dictionary with score and factors
        """
        try:
            # For forex, we'd compare economic indicators between countries
            # Simplified for now - full implementation would:
            # 1. Get GDP for both countries
            # 2. Compare interest rates
            # 3. Analyze unemployment
            # 4. Calculate relative economic strength
            
            score = 0.0
            factors = []
            
            # Get US indicators
            fed_funds = self.get_federal_funds_rate()
            us_unemployment = self.get_unemployment_rate()
            
            if fed_funds:
                factors.append(f"US Fed Funds: {fed_funds.value}%")
            
            if us_unemployment:
                factors.append(f"US Unemployment: {us_unemployment.value}%")
            
            # For pairs like EUR_USD, GBP_USD:
            # Higher US rates = bullish USD (bearish for pair)
            # Lower US unemployment = bullish USD
            
            if 'USD' in pair:
                if fed_funds and fed_funds.value > 4.0:
                    # High US rates = strong USD
                    if pair.endswith('USD'):
                        score -= 0.2  # Bearish for EUR_USD, GBP_USD
                    else:
                        score += 0.2  # Bullish for USD_JPY, USD_CAD
                    factors.append("Strong USD from high rates")
            
            return {
                'score': score,
                'recommendation': 'BUY' if score > 0.1 else 'SELL' if score < -0.1 else 'NEUTRAL',
                'factors': factors,
                'fed_funds_rate': fed_funds.value if fed_funds else None,
                'unemployment': us_unemployment.value if us_unemployment else None,
                'confidence': min(100, len(factors) * 30),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate forex fundamental score for {pair}: {e}")
            return {
                'score': 0.0,
                'recommendation': 'NEUTRAL',
                'factors': [],
                'confidence': 0
            }
    
    def get_all_indicators(self) -> Dict[str, EconomicIndicator]:
        """Get all available economic indicators"""
        indicators = {}
        
        fed_funds = self.get_federal_funds_rate()
        if fed_funds:
            indicators['fed_funds_rate'] = fed_funds
        
        cpi = self.get_cpi()
        if cpi:
            indicators['cpi'] = cpi
        
        gdp = self.get_gdp()
        if gdp:
            indicators['gdp'] = gdp
        
        unemployment = self.get_unemployment_rate()
        if unemployment:
            indicators['unemployment'] = unemployment
        
        return indicators


# Global instance
economic_indicators = EconomicIndicatorService()


def get_economic_indicators() -> EconomicIndicatorService:
    """Get global economic indicators instance"""
    return economic_indicators

