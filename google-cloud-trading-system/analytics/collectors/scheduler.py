#!/usr/bin/env python3
"""
Collector Scheduler
Manages automated data collection at different intervals
"""

import logging
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List
import schedule

logger = logging.getLogger(__name__)


class CollectorScheduler:
    """Schedule and manage data collection tasks"""
    
    def __init__(self, collector):
        """Initialize scheduler with collector instance"""
        self.collector = collector
        self.running = False
        self.thread = None
        
        # Collection statistics
        self.stats = {
            'collections_run': 0,
            'last_collection': None,
            'errors': 0,
            'last_error': None
        }
        
        logger.info("✅ CollectorScheduler initialized")
    
    def setup_schedules(self):
        """Setup collection schedules"""
        
        # High-frequency: Account snapshots every 1 minute
        schedule.every(1).minutes.do(self._collect_snapshots)
        
        # Medium-frequency: Closed trades every 5 minutes
        schedule.every(5).minutes.do(self._collect_trades)
        
        # Low-frequency: Full collection every 15 minutes
        schedule.every(15).minutes.do(self._full_collection)
        
        logger.info("✅ Collection schedules configured")
        logger.info("   • Account snapshots: Every 1 minute")
        logger.info("   • Closed trades: Every 5 minutes")
        logger.info("   • Full collection: Every 15 minutes")
    
    def _collect_snapshots(self):
        """Collect account snapshots"""
        try:
            logger.info("📸 Running scheduled snapshot collection...")
            for account_name in self.collector.clients:
                self.collector.collect_account_snapshot(account_name)
            
            self._update_stats(success=True)
            
        except Exception as e:
            logger.error(f"❌ Snapshot collection failed: {e}")
            self._update_stats(success=False, error=str(e))
    
    def _collect_trades(self):
        """Collect closed trades"""
        try:
            logger.info("📊 Running scheduled trade collection...")
            total_trades = 0
            for account_name in self.collector.clients:
                trades = self.collector.collect_closed_trades(account_name)
                total_trades += trades
            
            logger.info(f"✅ Collected {total_trades} trades")
            self._update_stats(success=True)
            
        except Exception as e:
            logger.error(f"❌ Trade collection failed: {e}")
            self._update_stats(success=False, error=str(e))
    
    def _full_collection(self):
        """Run full data collection"""
        try:
            logger.info("🔄 Running full data collection...")
            self.collector.collect_all_data()
            self._update_stats(success=True)
            
        except Exception as e:
            logger.error(f"❌ Full collection failed: {e}")
            self._update_stats(success=False, error=str(e))
    
    def _update_stats(self, success: bool, error: str = None):
        """Update collection statistics"""
        self.stats['collections_run'] += 1
        self.stats['last_collection'] = datetime.now().isoformat()
        
        if not success:
            self.stats['errors'] += 1
            self.stats['last_error'] = error
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            logger.warning("⚠️ Scheduler already running")
            return
        
        self.setup_schedules()
        self.running = True
        
        def run_scheduler():
            logger.info("🚀 Scheduler thread started")
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Scheduler error: {e}")
                    time.sleep(5)
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("✅ CollectorScheduler started in background")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        schedule.clear()
        logger.info("✅ CollectorScheduler stopped")
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            **self.stats,
            'running': self.running,
            'scheduled_jobs': len(schedule.get_jobs())
        }


