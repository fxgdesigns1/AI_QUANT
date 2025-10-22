#!/usr/bin/env python3
"""
Test Analytics System
Verify all analytics components are working correctly
"""

import sys
sys.path.insert(0, 'src')

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_analytics_system():
    """Test all analytics components"""
    
    print("=" * 80)
    print("TESTING ANALYTICS SYSTEM")
    print("=" * 80)
    print()
    
    # Test 1: Database initialization
    print("Test 1: Database Initialization")
    print("-" * 80)
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        stats = db.get_database_stats()
        print(f"✅ Database initialized: {db.db_path}")
        print(f"   Total trades: {stats.get('total_trades', 0)}")
        print(f"   Database size: {stats.get('db_size_mb', 0):.2f} MB")
        print()
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print()
        return False
    
    # Test 2: Metrics Calculator
    print("Test 2: Metrics Calculator")
    print("-" * 80)
    try:
        from src.analytics.metrics_calculator import get_metrics_calculator
        calc = get_metrics_calculator()
        
        # Test with sample trade data
        sample_trades = [
            {'is_closed': 1, 'realized_pnl': 100, 'entry_time': '2025-10-21T10:00:00', 'exit_time': '2025-10-21T11:00:00', 'trade_duration_seconds': 3600},
            {'is_closed': 1, 'realized_pnl': -50, 'entry_time': '2025-10-21T12:00:00', 'exit_time': '2025-10-21T13:00:00', 'trade_duration_seconds': 3600},
            {'is_closed': 1, 'realized_pnl': 75, 'entry_time': '2025-10-21T14:00:00', 'exit_time': '2025-10-21T15:00:00', 'trade_duration_seconds': 3600},
        ]
        
        metrics = calc.calculate_all_metrics(sample_trades, 'test_strategy')
        print(f"✅ Metrics calculator working")
        print(f"   Win Rate: {metrics.get('win_rate', 0):.1f}%")
        print(f"   Total P&L: ${metrics.get('total_pnl', 0):.2f}")
        print(f"   Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print()
    except Exception as e:
        print(f"❌ Metrics calculator test failed: {e}")
        print()
        return False
    
    # Test 3: Strategy Version Manager
    print("Test 3: Strategy Version Manager")
    print("-" * 80)
    try:
        from src.analytics.strategy_version_manager import get_strategy_version_manager
        version_mgr = get_strategy_version_manager()
        
        # Test version detection
        test_config = {
            'strategy_id': 'test_strategy',
            'instruments': ['EUR_USD'],
            'risk_settings': {'max_risk': 0.01}
        }
        
        has_changed, version = version_mgr.detect_changes('test_strategy', test_config)
        print(f"✅ Version manager working")
        print(f"   Test strategy version: {version}")
        print(f"   Config changed: {has_changed}")
        print()
    except Exception as e:
        print(f"❌ Version manager test failed: {e}")
        print()
        return False
    
    # Test 4: Trade Logger
    print("Test 4: Trade Logger")
    print("-" * 80)
    try:
        from src.analytics.trade_logger import get_trade_logger
        logger_obj = get_trade_logger()
        print(f"✅ Trade logger initialized")
        print(f"   Open positions tracked: {len(logger_obj._open_positions)}")
        print()
    except Exception as e:
        print(f"❌ Trade logger test failed: {e}")
        print()
        return False
    
    # Test 5: Data Archiver
    print("Test 5: Data Archiver")
    print("-" * 80)
    try:
        from src.analytics.data_archiver import get_data_archiver
        archiver = get_data_archiver()
        
        archive_stats = archiver.get_archive_stats()
        print(f"✅ Data archiver initialized")
        print(f"   Archive directory: {archiver.archive_dir}")
        print(f"   Total archives: {archive_stats.get('total_archives', 0)}")
        print()
    except Exception as e:
        print(f"❌ Data archiver test failed: {e}")
        print()
        return False
    
    # Test 6: Analytics Dashboard
    print("Test 6: Analytics Dashboard")
    print("-" * 80)
    try:
        from src.analytics.analytics_dashboard import get_analytics_dashboard
        dashboard = get_analytics_dashboard(port=8081)
        print(f"✅ Analytics dashboard initialized")
        print(f"   Dashboard port: {dashboard.port}")
        print(f"   Flask app: {dashboard.app.name}")
        print()
    except Exception as e:
        print(f"❌ Analytics dashboard test failed: {e}")
        print()
        return False
    
    # Summary
    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Analytics System Status:")
    print(f"  ✅ Database: Operational ({db.db_path})")
    print(f"  ✅ Metrics Calculator: Ready")
    print(f"  ✅ Version Manager: Active")
    print(f"  ✅ Trade Logger: Monitoring")
    print(f"  ✅ Data Archiver: Ready")
    print(f"  ✅ Analytics Dashboard: Configured (Port 8081)")
    print()
    print("To start the full system:")
    print("  python main.py")
    print()
    print("Analytics Dashboard will be available at:")
    print("  http://localhost:8081")
    print()
    
    return True

if __name__ == '__main__':
    success = test_analytics_system()
    sys.exit(0 if success else 1)

