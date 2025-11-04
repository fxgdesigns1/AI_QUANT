#!/usr/bin/env python3
"""
Live Data Feed System
Production-ready real-time market data streaming for Google Cloud deployment
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import threading
import queue
import time

from .oanda_client import OandaClient, OandaPrice, get_oanda_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Enhanced market data with validation"""
    pair: str
    bid: float
    ask: float
    timestamp: str
    is_live: bool
    data_source: str
    spread: float
    last_update_age: int
    volatility_score: float = 0.0
    regime: str = 'unknown'
    correlation_risk: float = 0.0
    confidence: float = 1.0
    validation_status: str = 'valid'

@dataclass
class DataValidationResult:
    """Data validation result"""
    is_valid: bool
    confidence: float
    age_seconds: int
    validation_errors: List[str]
    timestamp: datetime

class LiveDataFeed:
    """Production live data feed manager for OANDA market data"""
    
    def __init__(self, account_id: str = None, instruments: List[str] = None):
        """Initialize live data feed with optional account-specific settings"""
        from .dynamic_account_manager import get_account_manager
        
        # Get account manager and client
        self.account_manager = get_account_manager()
        self.account_id = account_id
        self.oanda_client = (self.account_manager.get_account_client(account_id) 
                           if account_id else get_oanda_client())
        
        # Configuration
        self.instruments = instruments or ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
        self.market_data: Dict[str, MarketData] = {}
        
        # Data validation settings
        self.max_data_age_seconds = int(os.getenv('MAX_DATA_AGE_SECONDS', '300'))  # 5 minutes
        self.min_confidence_threshold = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.5'))
        self.require_live_data = os.getenv('REQUIRE_LIVE_DATA', 'True').lower() == 'true'
        
        # Callbacks for data updates
        self.data_callbacks: List[Callable] = []
        self.validation_callbacks: List[Callable] = []
        
        # Threading
        self.running = False
        self.data_thread: Optional[threading.Thread] = None
        self.validation_thread: Optional[threading.Thread] = None
        
        # Data validation log
        self.validation_log: List[DataValidationResult] = []
        
        logger.info("✅ Live data feed initialized")
        logger.info(f"📊 Monitoring {len(self.instruments)} instruments")
        logger.info(f"⏱️ Max data age: {self.max_data_age_seconds} seconds")
    
    def add_data_callback(self, callback: Callable):
        """Add callback for data updates"""
        self.data_callbacks.append(callback)
        logger.info(f"✅ Added data callback: {callback.__name__}")
    
    def add_validation_callback(self, callback: Callable):
        """Add callback for validation results"""
        self.validation_callbacks.append(callback)
        logger.info(f"✅ Added validation callback: {callback.__name__}")
    
    def add_instruments(self, instruments: List[str]):
        """Add instruments to monitor"""
        if instruments:
            self.instruments.extend(instruments)
            # Remove duplicates
            self.instruments = list(set(self.instruments))
            logger.info(f"✅ Added instruments: {instruments}")
            logger.info(f"📊 Total instruments: {len(self.instruments)}")
    
    def start(self):
        """Start live data feed"""
        if self.running:
            logger.warning("⚠️ Data feed already running")
            return
        
        # Test OANDA connection first
        if not self.oanda_client.is_connected():
            logger.error("❌ Cannot start data feed - OANDA connection failed")
            raise ConnectionError("OANDA connection failed")
        
        self.running = True
        
        # Start data collection thread
        self.data_thread = threading.Thread(target=self._data_collection_loop, daemon=True)
        self.data_thread.start()
        
        # Start validation thread
        self.validation_thread = threading.Thread(target=self._validation_loop, daemon=True)
        self.validation_thread.start()
        
        logger.info("✅ Live data feed started")
    
    def stop(self):
        """Stop live data feed"""
        self.running = False
        
        # Wait for threads to finish
        if self.data_thread:
            self.data_thread.join(timeout=5)
        if self.validation_thread:
            self.validation_thread.join(timeout=5)
        
        logger.info("✅ Live data feed stopped")
    
    def _data_collection_loop(self):
        """Main data collection loop"""
        logger.info("🔄 Starting data collection loop")
        
        while self.running:
            try:
                # Get latest prices from OANDA - FORCE FRESH DATA
                prices = self.oanda_client.get_current_prices(
                    self.instruments,
                    force_refresh=True  # Bypass cache for real-time data
                )
                
                # Log fetch timestamp for debugging
                fetch_time = datetime.now()
                logger.info(f"📊 Fetched prices at {fetch_time.isoformat()}: {list(prices.keys())}")
                
                # Convert to MarketData format
                for instrument, oanda_price in prices.items():
                    market_data = self._convert_to_market_data(oanda_price)
                    self.market_data[instrument] = market_data
                    logger.debug(f"  ✓ {instrument}: bid={oanda_price.bid:.5f}, age={market_data.last_update_age}s")
                
                # Notify callbacks
                self._notify_data_callbacks()
                
                # Wait before next update - reduced to 2 seconds for faster updates
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Data collection error: {e}", exc_info=True)
                time.sleep(10)  # Wait longer on error
    
    def _validation_loop(self):
        """Data validation loop"""
        logger.info("🔄 Starting validation loop")
        
        while self.running:
            try:
                for instrument, data in self.market_data.items():
                    validation_result = self._validate_data(data)
                    self.validation_log.append(validation_result)
                    
                    # Keep only recent validation results
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    self.validation_log = [
                        result for result in self.validation_log
                        if result.timestamp > cutoff_time
                    ]
                
                # Notify validation callbacks
                self._notify_validation_callbacks()
                
                # Wait before next validation
                time.sleep(15)  # Validate every 15 seconds
                
            except Exception as e:
                logger.error(f"❌ Validation error: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _convert_to_market_data(self, oanda_price: OandaPrice) -> MarketData:
        """Convert OANDA price to MarketData format"""
        now = datetime.now()
        # Handle timezone-aware timestamps
        if oanda_price.timestamp.tzinfo is not None:
            now = now.replace(tzinfo=oanda_price.timestamp.tzinfo)
        age_seconds = int((now - oanda_price.timestamp).total_seconds())
        
        # Calculate volatility score (simplified)
        volatility_score = self._calculate_volatility_score(oanda_price)
        
        # Determine market regime
        regime = self._determine_market_regime(oanda_price)
        
        return MarketData(
            pair=oanda_price.instrument,
            bid=oanda_price.bid,
            ask=oanda_price.ask,
            timestamp=oanda_price.timestamp.isoformat(),
            is_live=oanda_price.is_live,
            data_source='OANDA',
            spread=oanda_price.spread,
            last_update_age=age_seconds,
            volatility_score=volatility_score,
            regime=regime,
            correlation_risk=0.0,  # Will be calculated separately
            confidence=1.0,
            validation_status='valid'
        )
    
    def _calculate_volatility_score(self, price: OandaPrice) -> float:
        """Calculate volatility score (0-1)"""
        # Simplified volatility calculation based on spread
        spread_pct = price.spread / price.bid * 100
        
        if spread_pct < 0.01:
            return 0.2  # Low volatility
        elif spread_pct < 0.05:
            return 0.5  # Medium volatility
        else:
            return 0.8  # High volatility
    
    def _determine_market_regime(self, price: OandaPrice) -> str:
        """Determine market regime based on price characteristics"""
        # Simplified regime detection
        spread_pct = price.spread / price.bid * 100
        
        if spread_pct < 0.01:
            return 'trending'
        elif spread_pct < 0.03:
            return 'ranging'
        else:
            return 'volatile'
    
    def _validate_data(self, data: MarketData) -> DataValidationResult:
        """Validate market data"""
        errors = []
        confidence = 1.0
        
        # Check data age
        if data.last_update_age > self.max_data_age_seconds:
            errors.append(f"Data too old: {data.last_update_age}s > {self.max_data_age_seconds}s")
            confidence -= 0.3
        
        # Check if data is live
        if self.require_live_data and not data.is_live:
            errors.append("Live data required but data is not live")
            confidence -= 0.5
        
        # Check spread reasonableness
        spread_pct = data.spread / data.bid * 100
        if spread_pct > 1.0:  # Spread > 1%
            errors.append(f"Unreasonable spread: {spread_pct:.2f}%")
            confidence -= 0.2
        
        # Check price reasonableness
        if data.bid <= 0 or data.ask <= 0:
            errors.append("Invalid price values")
            confidence = 0.0
        
        if data.ask <= data.bid:
            errors.append("Ask price <= Bid price")
            confidence = 0.0
        
        # Update data validation status
        data.validation_status = 'valid' if confidence >= self.min_confidence_threshold else 'invalid'
        data.confidence = confidence
        
        return DataValidationResult(
            is_valid=confidence >= self.min_confidence_threshold,
            confidence=confidence,
            age_seconds=data.last_update_age,
            validation_errors=errors,
            timestamp=datetime.now()
        )
    
    def _notify_data_callbacks(self):
        """Notify all data callbacks"""
        for callback in self.data_callbacks:
            try:
                callback(self.market_data)
            except Exception as e:
                logger.error(f"❌ Data callback error: {e}")
    
    def _notify_validation_callbacks(self):
        """Notify all validation callbacks"""
        for callback in self.validation_callbacks:
            try:
                callback(self.validation_log[-len(self.instruments):])  # Last validation for each instrument
            except Exception as e:
                logger.error(f"❌ Validation callback error: {e}")
    
    def get_market_data(self, instrument: Optional[str] = None) -> Dict[str, MarketData]:
        """Get current market data"""
        if instrument:
            return {instrument: self.market_data.get(instrument)} if instrument in self.market_data else {}
        return self.market_data.copy()
    
    def get_latest_prices(self, instruments: Optional[List[str]] = None) -> Dict[str, MarketData]:
        """Return latest MarketData per instrument.
        This aligns with callers expecting `get_latest_prices([instrument, ...])`.
        If `instruments` is None, returns all known market data.
        """
        if not self.market_data:
            return {}
        if instruments is None:
            return self.market_data.copy()
        return {sym: data for sym, data in self.market_data.items() if sym in instruments}
    
    def get_latest_data(self) -> Dict[str, MarketData]:
        """Get latest market data for all instruments"""
        return self.market_data.copy()
    
    def get_validation_log(self, limit: int = 100) -> List[DataValidationResult]:
        """Get recent validation log"""
        return self.validation_log[-limit:]
    
    def is_data_fresh(self, max_age_seconds: int = None) -> bool:
        """Check if data is fresh for all instruments"""
        if max_age_seconds is None:
            max_age_seconds = self.max_data_age_seconds
        
        if not self.market_data:
            return False
        
        # Check if any data is fresh
        for data in self.market_data.values():
            if data.last_update_age <= max_age_seconds:
                return True
        
        return False
    
    def get_data_quality_score(self) -> float:
        """Get overall data quality score (0-1)"""
        if not self.market_data:
            return 0.0
        
        total_confidence = sum(data.confidence for data in self.market_data.values())
        return total_confidence / len(self.market_data)

# Global data feed instance (lazy initialization)
data_feed = None

def get_data_feed() -> LiveDataFeed:
    """Get the global data feed instance"""
    global data_feed
    if data_feed is None:
        data_feed = LiveDataFeed()
    return data_feed
