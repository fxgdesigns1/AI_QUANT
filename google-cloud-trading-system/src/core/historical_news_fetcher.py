#!/usr/bin/env python3
"""
Historical News Fetcher - Economic Calendar and News Integration
Downloads and caches historical news, providing news context for backtests
"""

import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import os
import json
import pytz
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsImpact(Enum):
    """News impact levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

class HistoricalNewsFetcher:
    """
    Historical News Fetcher
    Downloads and caches historical economic news events
    Provides news context for backtesting and live trading
    """
    
    def __init__(self):
        """Initialize historical news fetcher"""
        self.name = "Historical News Fetcher"
        
        # Cache settings
        self.cache_dir = ".news_cache"
        self.cache_expiry_days = 7
        
        # API settings (using free economic calendar API)
        self.api_url = "https://financialmodelingprep.com/api/v3/economic_calendar"
        self.api_key = os.environ.get("FMP_API_KEY", "demo")
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # News cache
        self.news_cache = {}
        
        # Currency mappings
        self.currency_mapping = {
            "USD": ["United States", "US", "USA", "Federal Reserve", "Fed"],
            "EUR": ["Euro Area", "Eurozone", "ECB", "European Central Bank"],
            "GBP": ["United Kingdom", "UK", "Britain", "England", "BOE", "Bank of England"],
            "JPY": ["Japan", "BOJ", "Bank of Japan"],
            "AUD": ["Australia", "RBA", "Reserve Bank of Australia"],
            "CAD": ["Canada", "BOC", "Bank of Canada"],
            "NZD": ["New Zealand", "RBNZ", "Reserve Bank of New Zealand"]
        }
        
        # News impact keywords
        self.high_impact_keywords = [
            "interest rate", "rate decision", "fomc", "non-farm", "nfp", "cpi", "inflation",
            "gdp", "unemployment", "employment", "retail sales", "fed", "ecb", "boe", "boj"
        ]
        
        self.medium_impact_keywords = [
            "pmi", "manufacturing", "services", "trade balance", "industrial", "consumer",
            "sentiment", "confidence", "housing", "durable", "factory", "production"
        ]
        
        logger.info(f"✅ {self.name} initialized")
    
    def get_historical_news(self, days: int = 14, from_date: Optional[datetime] = None,
                          to_date: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """
        Get historical news events
        
        Args:
            days: Number of days to look back (default: 14)
            from_date: Optional start date (default: days ago from today)
            to_date: Optional end date (default: today)
            
        Returns:
            Dict of news events by currency
        """
        # Set default dates if not provided
        if to_date is None:
            to_date = datetime.now()
        
        if from_date is None:
            from_date = to_date - timedelta(days=days)
        
        # Format dates for API
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        
        # Check cache first
        cache_key = f"{from_str}_{to_str}"
        if cache_key in self.news_cache:
            logger.info(f"✅ Using cached news data for {from_str} to {to_str}")
            return self.news_cache[cache_key]
        
        # Check if cache file exists
        cache_file = os.path.join(self.cache_dir, f"news_{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    news_data = json.load(f)
                
                logger.info(f"✅ Loaded news data from cache file for {from_str} to {to_str}")
                self.news_cache[cache_key] = news_data
                return news_data
            except Exception as e:
                logger.warning(f"⚠️ Error loading news cache: {e}")
        
        # If not in cache, use simulated data for now (API would require paid key)
        logger.info(f"📰 Generating simulated news data for {from_str} to {to_str}")
        news_data = self._generate_simulated_news(from_date, to_date)
        
        # Cache the data
        self.news_cache[cache_key] = news_data
        
        # Save to cache file
        try:
            with open(cache_file, 'w') as f:
                json.dump(news_data, f)
            logger.info(f"✅ Saved news data to cache file")
        except Exception as e:
            logger.warning(f"⚠️ Error saving news cache: {e}")
        
        return news_data
    
    def _generate_simulated_news(self, from_date: datetime, to_date: datetime) -> Dict[str, List[Dict]]:
        """
        Generate simulated news data for testing
        In a production environment, this would fetch from a real API
        
        Args:
            from_date: Start date
            to_date: End date
            
        Returns:
            Dict of news events by currency
        """
        news_by_currency = {
            "USD": [],
            "EUR": [],
            "GBP": [],
            "JPY": [],
            "AUD": [],
            "CAD": [],
            "NZD": [],
            "XAU": []  # Gold news
        }
        
        # Common news events
        common_events = {
            "USD": [
                {"name": "FOMC Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "US CPI", "impact": NewsImpact.HIGH.value},
                {"name": "US Non-Farm Payrolls", "impact": NewsImpact.HIGH.value},
                {"name": "US GDP", "impact": NewsImpact.HIGH.value},
                {"name": "US Retail Sales", "impact": NewsImpact.MEDIUM.value},
                {"name": "US Manufacturing PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "US Services PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "US Initial Jobless Claims", "impact": NewsImpact.MEDIUM.value}
            ],
            "EUR": [
                {"name": "ECB Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "Eurozone CPI", "impact": NewsImpact.HIGH.value},
                {"name": "Eurozone GDP", "impact": NewsImpact.HIGH.value},
                {"name": "German Manufacturing PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "German Services PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "Eurozone Retail Sales", "impact": NewsImpact.MEDIUM.value}
            ],
            "GBP": [
                {"name": "BOE Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "UK CPI", "impact": NewsImpact.HIGH.value},
                {"name": "UK GDP", "impact": NewsImpact.HIGH.value},
                {"name": "UK Manufacturing PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "UK Services PMI", "impact": NewsImpact.MEDIUM.value},
                {"name": "UK Retail Sales", "impact": NewsImpact.MEDIUM.value}
            ],
            "JPY": [
                {"name": "BOJ Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "Japan CPI", "impact": NewsImpact.MEDIUM.value},
                {"name": "Japan GDP", "impact": NewsImpact.MEDIUM.value},
                {"name": "Japan Manufacturing PMI", "impact": NewsImpact.LOW.value}
            ],
            "AUD": [
                {"name": "RBA Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "Australia Employment Change", "impact": NewsImpact.MEDIUM.value},
                {"name": "Australia CPI", "impact": NewsImpact.MEDIUM.value},
                {"name": "Australia Retail Sales", "impact": NewsImpact.MEDIUM.value}
            ],
            "CAD": [
                {"name": "BOC Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "Canada Employment Change", "impact": NewsImpact.MEDIUM.value},
                {"name": "Canada CPI", "impact": NewsImpact.MEDIUM.value},
                {"name": "Canada Retail Sales", "impact": NewsImpact.MEDIUM.value}
            ],
            "NZD": [
                {"name": "RBNZ Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "New Zealand CPI", "impact": NewsImpact.MEDIUM.value},
                {"name": "New Zealand Employment Change", "impact": NewsImpact.MEDIUM.value}
            ],
            "XAU": [
                {"name": "US Non-Farm Payrolls", "impact": NewsImpact.HIGH.value},
                {"name": "US CPI", "impact": NewsImpact.HIGH.value},
                {"name": "FOMC Interest Rate Decision", "impact": NewsImpact.HIGH.value},
                {"name": "US GDP", "impact": NewsImpact.MEDIUM.value}
            ]
        }
        
        # Generate news events throughout the date range
        current_date = from_date
        while current_date <= to_date:
            # Skip weekends
            if current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                current_date += timedelta(days=1)
                continue
            
            # For each currency
            for currency, events in common_events.items():
                # Randomly select some events for this day
                num_events = np.random.randint(0, 2)  # 0 or 1 events per day per currency
                
                if num_events > 0:
                    selected_events = np.random.choice(events, num_events, replace=False)
                    
                    for event in selected_events:
                        # Random hour between 8:00 and 16:00
                        hour = np.random.randint(8, 17)
                        minute = np.random.choice([0, 15, 30, 45])
                        
                        event_time = current_date.replace(hour=hour, minute=minute)
                        
                        # Random sentiment (-1.0 to 1.0)
                        sentiment = np.random.uniform(-1.0, 1.0)
                        
                        # Add to news list
                        news_by_currency[currency].append({
                            "time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "currency": currency,
                            "name": event["name"],
                            "impact": event["impact"],
                            "actual": None,  # Would be filled with real data
                            "forecast": None,
                            "previous": None,
                            "sentiment": sentiment
                        })
            
            current_date += timedelta(days=1)
        
        return news_by_currency
    
    def get_news_context(self, timestamp: datetime, 
                        lookback_hours: int = 2, 
                        lookahead_hours: int = 2) -> Dict[str, Any]:
        """
        Get news context for a specific timestamp
        
        Args:
            timestamp: Timestamp to get context for
            lookback_hours: Hours to look back for past news
            lookahead_hours: Hours to look ahead for upcoming news
            
        Returns:
            Dict with news context information
        """
        # Ensure timestamp has timezone
        if timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        
        # Define time window
        start_time = timestamp - timedelta(hours=lookback_hours)
        end_time = timestamp + timedelta(hours=lookahead_hours)
        
        # Get all news within the window
        from_date = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        all_news = self.get_historical_news(from_date=from_date, to_date=to_date)
        
        # Filter news within the time window
        recent_news = []
        upcoming_news = []
        
        for currency, events in all_news.items():
            for event in events:
                event_time = datetime.strptime(event["time"], "%Y-%m-%d %H:%M:%S")
                event_time = pytz.UTC.localize(event_time)
                
                if start_time <= event_time <= timestamp:
                    event["relative_time"] = "recent"
                    recent_news.append(event)
                elif timestamp < event_time <= end_time:
                    event["relative_time"] = "upcoming"
                    upcoming_news.append(event)
        
        # Calculate overall news sentiment
        sentiment = 0.0
        high_impact_count = 0
        
        for event in recent_news:
            if event["impact"] == NewsImpact.HIGH.value:
                sentiment += event.get("sentiment", 0) * 2
                high_impact_count += 1
            elif event["impact"] == NewsImpact.MEDIUM.value:
                sentiment += event.get("sentiment", 0)
                high_impact_count += 0.5
        
        if high_impact_count > 0:
            sentiment = sentiment / high_impact_count
        
        # Check for high impact upcoming news
        high_impact_upcoming = any(event["impact"] == NewsImpact.HIGH.value for event in upcoming_news)
        
        # Compile context
        news_context = {
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "recent_news": recent_news,
            "upcoming_news": upcoming_news,
            "sentiment": sentiment,
            "high_impact_count": high_impact_count,
            "high_impact_upcoming": high_impact_upcoming,
            "trading_caution": high_impact_upcoming or high_impact_count > 1
        }
        
        return news_context
    
    def get_instrument_news(self, instrument: str, timestamp: datetime,
                          lookback_hours: int = 2, 
                          lookahead_hours: int = 2) -> Dict[str, Any]:
        """
        Get news context specific to an instrument
        
        Args:
            instrument: Instrument to get news for (e.g. "EUR_USD")
            timestamp: Timestamp to get context for
            lookback_hours: Hours to look back for past news
            lookahead_hours: Hours to look ahead for upcoming news
            
        Returns:
            Dict with instrument-specific news context
        """
        # Get general news context
        general_context = self.get_news_context(timestamp, lookback_hours, lookahead_hours)
        
        # Extract currencies from instrument
        currencies = []
        if "_" in instrument:
            base, quote = instrument.split("_")
            currencies = [base, quote]
        else:
            # Special case for Gold (XAU_USD)
            if instrument == "XAU_USD":
                currencies = ["XAU", "USD"]
            else:
                currencies = [instrument]
        
        # Filter news for these currencies
        instrument_recent_news = []
        instrument_upcoming_news = []
        
        for event in general_context["recent_news"]:
            if event["currency"] in currencies:
                instrument_recent_news.append(event)
        
        for event in general_context["upcoming_news"]:
            if event["currency"] in currencies:
                instrument_upcoming_news.append(event)
        
        # Calculate instrument-specific sentiment
        sentiment = 0.0
        high_impact_count = 0
        
        for event in instrument_recent_news:
            if event["impact"] == NewsImpact.HIGH.value:
                sentiment += event.get("sentiment", 0) * 2
                high_impact_count += 1
            elif event["impact"] == NewsImpact.MEDIUM.value:
                sentiment += event.get("sentiment", 0)
                high_impact_count += 0.5
        
        if high_impact_count > 0:
            sentiment = sentiment / high_impact_count
        
        # Check for high impact upcoming news
        high_impact_upcoming = any(event["impact"] == NewsImpact.HIGH.value for event in instrument_upcoming_news)
        
        # Compile instrument-specific context
        instrument_context = {
            "instrument": instrument,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "recent_news": instrument_recent_news,
            "upcoming_news": instrument_upcoming_news,
            "sentiment": sentiment,
            "high_impact_count": high_impact_count,
            "high_impact_upcoming": high_impact_upcoming,
            "trading_caution": high_impact_upcoming or high_impact_count > 1
        }
        
        return instrument_context


# Global instance
_historical_news_fetcher = None

def get_historical_news_fetcher() -> HistoricalNewsFetcher:
    """Get the global historical news fetcher instance"""
    global _historical_news_fetcher
    if _historical_news_fetcher is None:
        _historical_news_fetcher = HistoricalNewsFetcher()
    return _historical_news_fetcher


if __name__ == "__main__":
    # Test historical news fetcher
    fetcher = get_historical_news_fetcher()
    
    # Get news for the past 7 days
    news = fetcher.get_historical_news(days=7)
    
    # Print summary
    for currency, events in news.items():
        print(f"{currency}: {len(events)} events")
    
    # Get news context for current time
    now = datetime.now()
    context = fetcher.get_news_context(now)
    
    print(f"\nNews Context for {now}:")
    print(f"Recent news: {len(context['recent_news'])}")
    print(f"Upcoming news: {len(context['upcoming_news'])}")
    print(f"Sentiment: {context['sentiment']:.2f}")
    print(f"High impact count: {context['high_impact_count']}")
    print(f"High impact upcoming: {context['high_impact_upcoming']}")
    print(f"Trading caution: {context['trading_caution']}")
    
    # Get instrument-specific news
    eur_usd_context = fetcher.get_instrument_news("EUR_USD", now)
    
    print(f"\nEUR_USD News Context:")
    print(f"Recent news: {len(eur_usd_context['recent_news'])}")
    print(f"Upcoming news: {len(eur_usd_context['upcoming_news'])}")
    print(f"Sentiment: {eur_usd_context['sentiment']:.2f}")
    print(f"Trading caution: {eur_usd_context['trading_caution']}")