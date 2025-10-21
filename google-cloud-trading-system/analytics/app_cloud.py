#!/usr/bin/env python3
"""
Analytics Dashboard for Google Cloud
Optimized for App Engine deployment
"""

import os
import sys

# Set port from environment (App Engine uses PORT env var)
port = int(os.environ.get('PORT', 8080))

# Override analytics port
os.environ['ANALYTICS_PORT'] = str(port)

# Import and run main app
from app import app, socketio, scheduler, collector, logger

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🚀 Analytics Dashboard - Google Cloud")
    logger.info(f"🌐 Port: {port}")
    logger.info("📊 Mode: Read-Only Analytics")
    logger.info("="*60)
    
    # Start data collector
    try:
        scheduler.start()
        logger.info("✅ Data collector started")
        
        # Initial data collection
        collector.collect_all_data()
        logger.info("✅ Initial data collected")
    except Exception as e:
        logger.error(f"⚠️ Collector start failed: {e}")
    
    # Run app
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)


