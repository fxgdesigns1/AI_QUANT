#!/usr/bin/env python3
"""
Data Archiver - 90-Day Retention Management
Automatically archives old trades to compressed files
"""

import os
import logging
import json
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading

from .trade_database import get_trade_database

logger = logging.getLogger(__name__)


class DataArchiver:
    """Manage trade data archival and retention"""
    
    def __init__(self, archive_dir: Optional[str] = None):
        """Initialize data archiver"""
        self.db = get_trade_database()
        
        if archive_dir is None:
            # Default archive directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            archive_dir = os.path.join(base_dir, 'data', 'archives')
        
        self.archive_dir = archive_dir
        os.makedirs(self.archive_dir, exist_ok=True)
        
        self._lock = threading.Lock()
        logger.info(f"✅ Data archiver initialized: {archive_dir}")
    
    def archive_old_trades(self, days: int = 90) -> Dict[str, Any]:
        """
        Archive trades older than specified days
        
        Returns:
            Summary of archival operation
        """
        with self._lock:
            try:
                logger.info(f"🔄 Starting archival of trades older than {days} days...")
                
                # Get trades to archive
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # Get all old closed trades from database
                trades_to_archive = self._get_old_trades(cutoff_date)
                
                if not trades_to_archive:
                    logger.info("✅ No trades to archive")
                    return {
                        'success': True,
                        'archived_count': 0,
                        'deleted_count': 0,
                        'archive_file': None
                    }
                
                # Group by month
                trades_by_month = self._group_trades_by_month(trades_to_archive)
                
                archived_count = 0
                archive_files = []
                
                # Archive each month's trades
                for month_key, trades in trades_by_month.items():
                    archive_file = self._archive_month_trades(month_key, trades)
                    if archive_file:
                        archived_count += len(trades)
                        archive_files.append(archive_file)
                
                # Delete archived trades from database
                deleted_count = self.db.delete_old_trades(days)
                
                # Optimize database
                self.db.vacuum_database()
                
                logger.info(f"✅ Archived {archived_count} trades, deleted {deleted_count} from DB")
                
                return {
                    'success': True,
                    'archived_count': archived_count,
                    'deleted_count': deleted_count,
                    'archive_files': archive_files,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Error archiving trades: {e}")
                logger.exception("Full traceback:")
                return {
                    'success': False,
                    'error': str(e),
                    'archived_count': 0,
                    'deleted_count': 0
                }
    
    def _get_old_trades(self, cutoff_date: str) -> List[Dict[str, Any]]:
        """Get all trades older than cutoff date"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE entry_time < ? AND is_closed = 1
                ORDER BY entry_time
            """, (cutoff_date,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _group_trades_by_month(self, trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group trades by month (YYYY-MM)"""
        trades_by_month = {}
        
        for trade in trades:
            try:
                entry_time = trade.get('entry_time', '')
                if entry_time:
                    dt = datetime.fromisoformat(entry_time)
                    month_key = dt.strftime('%Y-%m')
                    
                    if month_key not in trades_by_month:
                        trades_by_month[month_key] = []
                    
                    trades_by_month[month_key].append(trade)
            except:
                pass
        
        return trades_by_month
    
    def _archive_month_trades(self, month_key: str, trades: List[Dict[str, Any]]) -> Optional[str]:
        """Archive a month's worth of trades to compressed file"""
        try:
            # Create archive filename
            archive_filename = f"trades_{month_key}.json.gz"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            # Check if archive already exists
            if os.path.exists(archive_path):
                # Append to existing archive
                existing_trades = self._load_archive(archive_path)
                trades = existing_trades + trades
            
            # Prepare archive data
            archive_data = {
                'month': month_key,
                'archived_at': datetime.now().isoformat(),
                'trade_count': len(trades),
                'trades': trades
            }
            
            # Write compressed JSON
            with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2)
            
            logger.info(f"✅ Archived {len(trades)} trades to {archive_filename}")
            return archive_path
            
        except Exception as e:
            logger.error(f"❌ Failed to archive month {month_key}: {e}")
            return None
    
    def _load_archive(self, archive_path: str) -> List[Dict[str, Any]]:
        """Load trades from existing archive"""
        try:
            with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                archive_data = json.load(f)
                return archive_data.get('trades', [])
        except Exception as e:
            logger.error(f"❌ Failed to load archive {archive_path}: {e}")
            return []
    
    def restore_trades_from_archive(self, month_key: str) -> Dict[str, Any]:
        """
        Restore trades from archive back to database
        
        Args:
            month_key: Month in YYYY-MM format
            
        Returns:
            Summary of restoration
        """
        with self._lock:
            try:
                archive_filename = f"trades_{month_key}.json.gz"
                archive_path = os.path.join(self.archive_dir, archive_filename)
                
                if not os.path.exists(archive_path):
                    return {
                        'success': False,
                        'error': f"Archive not found: {archive_filename}"
                    }
                
                logger.info(f"🔄 Restoring trades from {archive_filename}...")
                
                # Load archive
                with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                    archive_data = json.load(f)
                
                trades = archive_data.get('trades', [])
                
                # Restore to database
                restored_count = 0
                for trade_dict in trades:
                    try:
                        # Convert dict to TradeRecord
                        from .trade_database import TradeRecord
                        trade = TradeRecord(**trade_dict)
                        
                        # Insert into database
                        if self.db.insert_trade(trade):
                            restored_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to restore trade: {e}")
                
                logger.info(f"✅ Restored {restored_count}/{len(trades)} trades from archive")
                
                return {
                    'success': True,
                    'restored_count': restored_count,
                    'total_trades': len(trades),
                    'month': month_key
                }
                
            except Exception as e:
                logger.error(f"❌ Error restoring from archive: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def list_archives(self) -> List[Dict[str, Any]]:
        """List all available archives"""
        try:
            archives = []
            
            for filename in os.listdir(self.archive_dir):
                if filename.startswith('trades_') and filename.endswith('.json.gz'):
                    filepath = os.path.join(self.archive_dir, filename)
                    
                    # Extract month from filename
                    month_key = filename.replace('trades_', '').replace('.json.gz', '')
                    
                    # Get file size
                    file_size = os.path.getsize(filepath)
                    
                    # Load archive to get trade count
                    try:
                        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                            archive_data = json.load(f)
                            trade_count = archive_data.get('trade_count', 0)
                            archived_at = archive_data.get('archived_at', '')
                    except:
                        trade_count = 0
                        archived_at = ''
                    
                    archives.append({
                        'filename': filename,
                        'month': month_key,
                        'trade_count': trade_count,
                        'file_size_mb': file_size / (1024 * 1024),
                        'archived_at': archived_at,
                        'filepath': filepath
                    })
            
            # Sort by month descending
            archives.sort(key=lambda x: x['month'], reverse=True)
            
            return archives
            
        except Exception as e:
            logger.error(f"❌ Error listing archives: {e}")
            return []
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get statistics about archived data"""
        try:
            archives = self.list_archives()
            
            total_trades = sum(a['trade_count'] for a in archives)
            total_size_mb = sum(a['file_size_mb'] for a in archives)
            
            return {
                'total_archives': len(archives),
                'total_trades_archived': total_trades,
                'total_size_mb': total_size_mb,
                'archives': archives,
                'archive_directory': self.archive_dir
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting archive stats: {e}")
            return {}
    
    def delete_archive(self, month_key: str) -> bool:
        """Delete an archive file (permanent)"""
        try:
            archive_filename = f"trades_{month_key}.json.gz"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            if not os.path.exists(archive_path):
                logger.warning(f"⚠️ Archive not found: {archive_filename}")
                return False
            
            os.remove(archive_path)
            logger.info(f"✅ Deleted archive: {archive_filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting archive: {e}")
            return False
    
    def export_archive_to_csv(self, month_key: str, output_path: Optional[str] = None) -> Optional[str]:
        """Export archived trades to CSV for analysis"""
        try:
            archive_filename = f"trades_{month_key}.json.gz"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            if not os.path.exists(archive_path):
                logger.error(f"❌ Archive not found: {archive_filename}")
                return None
            
            # Load archive
            with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                archive_data = json.load(f)
            
            trades = archive_data.get('trades', [])
            
            if not trades:
                logger.warning(f"⚠️ No trades in archive {archive_filename}")
                return None
            
            # Generate CSV
            if output_path is None:
                output_path = os.path.join(self.archive_dir, f"trades_{month_key}.csv")
            
            import csv
            
            # Get all field names
            fieldnames = list(trades[0].keys())
            
            with open(output_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(trades)
            
            logger.info(f"✅ Exported {len(trades)} trades to CSV: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error exporting to CSV: {e}")
            return None
    
    def cleanup_old_archives(self, months: int = 24) -> Dict[str, Any]:
        """
        Delete archives older than specified months
        Keeps daily snapshots and metrics forever
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            cutoff_month = cutoff_date.strftime('%Y-%m')
            
            archives = self.list_archives()
            deleted_count = 0
            
            for archive in archives:
                if archive['month'] < cutoff_month:
                    if self.delete_archive(archive['month']):
                        deleted_count += 1
            
            logger.info(f"✅ Deleted {deleted_count} old archives (>{months} months)")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'cutoff_month': cutoff_month
            }
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old archives: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
_data_archiver_instance = None
_data_archiver_lock = threading.Lock()


def get_data_archiver() -> DataArchiver:
    """Get singleton data archiver instance"""
    global _data_archiver_instance
    
    if _data_archiver_instance is None:
        with _data_archiver_lock:
            if _data_archiver_instance is None:
                _data_archiver_instance = DataArchiver()
    
    return _data_archiver_instance



