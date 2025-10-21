"""
Persistent Price History Storage - API Optimized
Stores price history on disk to avoid re-fetching on restarts
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from collections import deque
import threading

from .data_feed import MarketData

logger = logging.getLogger(__name__)

class PersistentHistoryManager:
    """Manages persistent price history storage"""
    
    def __init__(self, storage_dir: str = "price_history"):
        self.storage_dir = storage_dir
        self.history_files = {}
        self.max_history = 1000
        self.lock = threading.Lock()
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        logger.info(f"✅ PersistentHistoryManager initialized: {storage_dir}")
    
    def save_price_history(self, instrument: str, market_data: MarketData):
        """Save price data to persistent storage"""
        try:
            with self.lock:
                # Get or create history file for instrument
                if instrument not in self.history_files:
                    self.history_files[instrument] = deque(maxlen=self.max_history)
                
                # Add to memory buffer
                self.history_files[instrument].append({
                    'instrument': market_data.instrument,
                    'bid': market_data.bid,
                    'ask': market_data.ask,
                    'timestamp': market_data.timestamp,
                    'spread': market_data.spread,
                    'saved_at': datetime.now(timezone.utc).isoformat()
                })
                
                # Save to disk every 10 updates
                if len(self.history_files[instrument]) % 10 == 0:
                    self._save_to_disk(instrument)
                
        except Exception as e:
            logger.error(f"❌ Error saving price history for {instrument}: {e}")
    
    def _save_to_disk(self, instrument: str):
        """Save instrument history to disk"""
        try:
            file_path = os.path.join(self.storage_dir, f"{instrument.replace('/', '_')}.json")
            
            # Convert deque to list for JSON serialization
            history_data = list(self.history_files[instrument])
            
            with open(file_path, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            logger.debug(f"💾 Saved {len(history_data)} price points for {instrument}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to disk for {instrument}: {e}")
    
    def load_price_history(self, instrument: str) -> List[Dict[str, Any]]:
        """Load price history from disk"""
        try:
            file_path = os.path.join(self.storage_dir, f"{instrument.replace('/', '_')}.json")
            
            if not os.path.exists(file_path):
                logger.info(f"📁 No history file for {instrument}")
                return []
            
            with open(file_path, 'r') as f:
                history_data = json.load(f)
            
            logger.info(f"📂 Loaded {len(history_data)} price points for {instrument}")
            return history_data
            
        except Exception as e:
            logger.error(f"❌ Error loading history for {instrument}: {e}")
            return []
    
    def get_latest_prices(self, instrument: str, count: int = 100) -> List[MarketData]:
        """Get latest price data for instrument"""
        try:
            with self.lock:
                if instrument not in self.history_files:
                    # Try to load from disk
                    disk_data = self.load_price_history(instrument)
                    if disk_data:
                        # Convert to MarketData objects
                        market_data_list = []
                        for item in disk_data[-count:]:
                            market_data = MarketData(
                                instrument=item['instrument'],
                                bid=item['bid'],
                                ask=item['ask'],
                                timestamp=item['timestamp'],
                                spread=item['spread']
                            )
                            market_data_list.append(market_data)
                        return market_data_list
                    return []
                
                # Get from memory buffer
                recent_data = list(self.history_files[instrument])[-count:]
                market_data_list = []
                
                for item in recent_data:
                    market_data = MarketData(
                        instrument=item['instrument'],
                        bid=item['bid'],
                        ask=item['ask'],
                        timestamp=item['timestamp'],
                        spread=item['spread']
                    )
                    market_data_list.append(market_data)
                
                return market_data_list
                
        except Exception as e:
            logger.error(f"❌ Error getting latest prices for {instrument}: {e}")
            return []
    
    def save_all_histories(self):
        """Save all instrument histories to disk"""
        try:
            with self.lock:
                for instrument in self.history_files:
                    self._save_to_disk(instrument)
                
                logger.info(f"💾 Saved all histories: {len(self.history_files)} instruments")
                
        except Exception as e:
            logger.error(f"❌ Error saving all histories: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                'storage_dir': self.storage_dir,
                'instruments_tracked': len(self.history_files),
                'total_files': 0,
                'total_size_bytes': 0
            }
            
            # Count files and size
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    stats['total_files'] += 1
                    stats['total_size_bytes'] += os.path.getsize(file_path)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting storage stats: {e}")
            return {'error': str(e)}

# Global instance
_history_manager = None

def get_persistent_history() -> PersistentHistoryManager:
    """Get persistent history manager instance"""
    global _history_manager
    if _history_manager is None:
        _history_manager = PersistentHistoryManager()
    return _history_manager
