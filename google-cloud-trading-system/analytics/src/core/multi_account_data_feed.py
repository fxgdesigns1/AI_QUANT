#!/usr/bin/env python3
"""
Multi-Account Data Feed System - FIXED VERSION
Production-ready multi-account market data management for Google Cloud deployment
FIXED: Added missing get_latest_data method
"""

import os
import logging
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .data_feed import LiveDataFeed, MarketData
from .account_manager import get_account_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAccountDataFeed:
    """Production multi-account market data feed system - FIXED"""
    
    def __init__(self):
        """Initialize multi-account data feed"""
        self.account_manager = get_account_manager()
        self.data_feeds: Dict[str, LiveDataFeed] = {}
        self.market_data: Dict[str, Dict[str, MarketData]] = {}
        
        # Streaming control
        self.streaming = False
        self.stream_threads: Dict[str, threading.Thread] = {}
        self.data_queues: Dict[str, queue.Queue] = {}
        
        # Initialize data feeds for each account
        self._initialize_data_feeds()
        
        logger.info("✅ Multi-account data feed initialized")
        logger.info(f"📊 Active feeds: {len(self.data_feeds)}")
    
    def _initialize_data_feeds(self):
        """Initialize data feeds for each active account"""
        for account_id in self.account_manager.get_active_accounts():
            try:
                # Get account configuration
                config = self.account_manager.get_account_config(account_id)
                if not config:
                    continue
                
                # Create data feed for this account
                data_feed = LiveDataFeed(account_id)
                
                # Get instruments for this account
                instruments = config.instruments
                if instruments:
                    data_feed.add_instruments(instruments)
                
                self.data_feeds[account_id] = data_feed
                self.market_data[account_id] = {}
                
                # Create data queue for streaming
                self.data_queues[account_id] = queue.Queue()
                
                # Get account name for logging
                account_name = config.account_name
                logger.info(f"✅ Data feed initialized for {account_name} ({account_id})")
                logger.info(f"   • Instruments: {instruments}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize data feed for {account_id}: {e}")
    
    def start(self):
        """Start all data feeds"""
        if self.streaming:
            logger.warning("⚠️ Data feeds already streaming")
            return
        
        self.streaming = True
        
        for account_id in self.data_feeds:
            try:
                # Start individual data feed
                self.data_feeds[account_id].start()
                
                # Start streaming thread
                stream_thread = threading.Thread(
                    target=self._stream_data,
                    args=(account_id,),
                    daemon=True
                )
                stream_thread.start()
                self.stream_threads[account_id] = stream_thread
                
                logger.info(f"✅ Started streaming for account {account_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to start data feed for {account_id}: {e}")
        
        logger.info("✅ Multi-account data feed started")
    
    def stop(self):
        """Stop all data feeds"""
        if not self.streaming:
            logger.warning("⚠️ Data feeds not streaming")
            return
        
        self.streaming = False
        
        for account_id in self.data_feeds:
            try:
                # Stop individual data feed
                self.data_feeds[account_id].stop()
                
                # Wait for stream thread to finish
                if account_id in self.stream_threads:
                    self.stream_threads[account_id].join(timeout=5)
                
                logger.info(f"✅ Stopped streaming for account {account_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to stop data feed for {account_id}: {e}")
        
        # Clear threads
        self.stream_threads.clear()
        
        logger.info("✅ Multi-account data feed stopped")
    
    def _stream_data(self, account_id: str):
        """Stream data for specific account"""
        try:
            data_feed = self.data_feeds[account_id]
            data_queue = self.data_queues[account_id]
            
            while self.streaming:
                try:
                    # Get latest market data
                    latest_data = data_feed.get_latest_data()
                    
                    if latest_data:
                        # Update market data cache
                        for instrument, data in latest_data.items():
                            self.market_data[account_id][instrument] = data
                    
                    # Small delay to prevent excessive CPU usage
                    threading.Event().wait(1)
                    
                except Exception as e:
                    logger.error(f"❌ Streaming error for {account_id}: {e}")
                    threading.Event().wait(5)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"❌ Stream thread error for {account_id}: {e}")
    
    def get_market_data(self, account_id: str) -> Dict[str, MarketData]:
        """Get current market data for specific account"""
        try:
            return self.market_data.get(account_id, {})
        except Exception as e:
            logger.error(f"❌ Failed to get market data for {account_id}: {e}")
            return {}
    
    def get_latest_data(self, account_id: str) -> Dict[str, Any]:
        """Get latest market data for specific account - LIVE DATA ONLY"""
        try:
            data_feed = self.data_feeds.get(account_id)
            if not data_feed:
                return {}
            
            # Get latest data from the individual data feed - KEEP AS MarketData OBJECTS
            latest_data = data_feed.get_latest_data()
            
            # Return MarketData objects directly (not converted to dictionaries)
            return latest_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest data for {account_id}: {e}")
            return {}
    
    def get_all_market_data(self) -> Dict[str, Dict[str, MarketData]]:
        """Get current market data for all accounts"""
        return self.market_data.copy()
    
    def get_instrument_data(self, account_id: str, instrument: str) -> Optional[MarketData]:
        """Get current data for specific instrument on specific account"""
        try:
            account_data = self.market_data.get(account_id, {})
            return account_data.get(instrument)
        except Exception as e:
            logger.error(f"❌ Failed to get instrument data for {account_id}/{instrument}: {e}")
            return None
    
    def is_data_fresh(self, account_id: str, max_age_seconds: int = 300) -> bool:
        """Check if data is fresh for specific account"""
        try:
            data_feed = self.data_feeds.get(account_id)
            if not data_feed:
                return False
            
            return data_feed.is_data_fresh(max_age_seconds)
            
        except Exception as e:
            logger.error(f"❌ Failed to check data freshness for {account_id}: {e}")
            return False
    
    def get_data_status(self, account_id: str) -> Dict[str, Any]:
        """Get data feed status for specific account"""
        try:
            data_feed = self.data_feeds.get(account_id)
            if not data_feed:
                return {
                    'account_id': account_id,
                    'status': 'not_found',
                    'error': 'Data feed not found'
                }
            
            return {
                'account_id': account_id,
                'status': 'active' if self.streaming else 'stopped',
                'instruments': list(self.market_data.get(account_id, {}).keys()),
                'data_count': len(self.market_data.get(account_id, {})),
                'streaming': self.streaming,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get data status for {account_id}: {e}")
            return {
                'account_id': account_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_all_data_status(self) -> Dict[str, Dict[str, Any]]:
        """Get data feed status for all accounts"""
        status = {}
        for account_id in self.data_feeds:
            status[account_id] = self.get_data_status(account_id)
        return status

# Global multi-account data feed instance
multi_account_data_feed = MultiAccountDataFeed()

def get_multi_account_data_feed() -> MultiAccountDataFeed:
    """Get the global multi-account data feed instance"""
    return multi_account_data_feed
