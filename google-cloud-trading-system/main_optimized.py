#!/usr/bin/env python3
"""
Google Cloud Trading System - Memory Optimized Version
Optimized for F1 FREE TIER with reduced memory usage for additional strategies
"""

import os
import sys
import logging
import json
import time
import threading
import asyncio
from datetime import datetime, timedelta
import uuid
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import gc  # Garbage collection for memory optimization

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# =============================================================================
# MEMORY OPTIMIZATION CONFIGURATION
# =============================================================================
MEMORY_OPTIMIZATION = {
    "strategy_memory_limit": 30,  # MB per strategy (reduced from 50)
    "base_system_memory": 150,    # MB base system (reduced from 200)
    "data_cache_size": 50,        # MB for data caching (reduced)
    "dashboard_memory": 20,       # MB for dashboard (reduced)
    "enable_garbage_collection": True,
    "memory_cleanup_interval": 300,  # 5 minutes
    "max_concurrent_strategies": 10,  # Increased capacity
}

# Setup optimized logging (reduced memory footprint)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # Removed file handler to save memory
    ]
)
logger = logging.getLogger(__name__)

# Memory optimization functions
def optimize_memory():
    """Optimize memory usage"""
    if MEMORY_OPTIMIZATION["enable_garbage_collection"]:
        gc.collect()
        logger.info("🧹 Memory garbage collection completed")

def log_memory_usage():
    """Log current memory usage"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"💾 Current memory usage: {memory_mb:.1f}MB")
        return memory_mb
    except ImportError:
        logger.warning("psutil not available for memory monitoring")
        return 0

# Initialize Flask app with memory optimization
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'optimized-trading-system-2025')

# Initialize SocketIO with memory optimization
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=1024*1024)  # Reduced buffer size

# =============================================================================
# OPTIMIZED DASHBOARD MANAGER
# =============================================================================
dashboard_manager = None
try:
    logger.info("🔄 Initializing optimized dashboard manager...")
    from src.dashboard.advanced_dashboard import AdvancedDashboardManager
    
    # Create optimized dashboard manager
    dashboard_manager = AdvancedDashboardManager()
    
    # Apply memory optimizations
    if hasattr(dashboard_manager, 'optimize_memory'):
        dashboard_manager.optimize_memory()
    
    logger.info("✅ Optimized dashboard manager initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize dashboard manager: {e}")
    dashboard_manager = None

# =============================================================================
# OPTIMIZED NEWS INTEGRATION
# =============================================================================
news_integration = None
try:
    logger.info("🔄 Initializing optimized news integration...")
    from src.core.news_integration import safe_news_integration
    news_integration = safe_news_integration
    logger.info("✅ Optimized news integration initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize news integration: {e}")
    news_integration = None

# =============================================================================
# OPTIMIZED TRADING SYSTEM
# =============================================================================
class OptimizedTradingSystem:
    """Memory-optimized trading system for additional strategies"""
    
    def __init__(self):
        self.system_id = f"optimized-system-{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now()
        self.strategies = {}
        self.performance_data = {}
        self.memory_usage = 0
        self.last_cleanup = datetime.now()
        
        # Memory optimization settings
        self.max_strategies = MEMORY_OPTIMIZATION["max_concurrent_strategies"]
        self.memory_cleanup_interval = MEMORY_OPTIMIZATION["memory_cleanup_interval"]
        
        logger.info(f"🚀 Optimized Trading System initialized: {self.system_id}")
        logger.info(f"📊 Max strategies capacity: {self.max_strategies}")
        logger.info(f"💾 Memory optimization enabled")
    
    def add_strategy(self, strategy_name: str, strategy_config: Dict[str, Any]) -> bool:
        """Add a new strategy with memory optimization"""
        if len(self.strategies) >= self.max_strategies:
            logger.warning(f"⚠️ Maximum strategies reached ({self.max_strategies})")
            return False
        
        # Estimate memory usage
        estimated_memory = MEMORY_OPTIMIZATION["strategy_memory_limit"]
        if self.memory_usage + estimated_memory > 580:  # Leave 20MB buffer
            logger.warning(f"⚠️ Insufficient memory for new strategy")
            return False
        
        # Add strategy with optimized memory usage
        self.strategies[strategy_name] = {
            "config": strategy_config,
            "memory_limit": estimated_memory,
            "created_at": datetime.now(),
            "performance": {}
        }
        
        self.memory_usage += estimated_memory
        logger.info(f"✅ Strategy '{strategy_name}' added (Memory: {self.memory_usage}MB)")
        
        # Trigger memory cleanup
        self.cleanup_memory()
        return True
    
    def cleanup_memory(self):
        """Clean up memory usage"""
        current_time = datetime.now()
        if (current_time - self.last_cleanup).seconds >= self.memory_cleanup_interval:
            optimize_memory()
            self.last_cleanup = current_time
            logger.info("🧹 Memory cleanup completed")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get optimized system status"""
        current_memory = log_memory_usage()
        
        return {
            "system_id": self.system_id,
            "status": "optimized",
            "uptime": str(datetime.now() - self.start_time),
            "memory_optimization": {
                "enabled": True,
                "current_usage_mb": current_memory,
                "max_capacity_mb": 580,
                "utilization_pct": round((current_memory / 580) * 100, 1),
                "strategies_count": len(self.strategies),
                "max_strategies": self.max_strategies,
                "available_strategies": self.max_strategies - len(self.strategies)
            },
            "optimization_settings": MEMORY_OPTIMIZATION,
            "timestamp": datetime.now().isoformat()
        }

# Initialize optimized trading system
trading_system = OptimizedTradingSystem()

# =============================================================================
# OPTIMIZED API ENDPOINTS
# =============================================================================

@app.route('/')
def index():
    """Main dashboard with memory optimization info"""
    return render_template('index.html', 
                         system_id=trading_system.system_id,
                         optimization_enabled=True)

@app.route('/api/health')
def health_check():
    """Health check with memory optimization status"""
    status = trading_system.get_system_status()
    return jsonify({
        "status": "healthy",
        "optimization": "memory_optimized",
        "system": status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/system/status')
def system_status():
    """Detailed system status with memory optimization"""
    return jsonify(trading_system.get_system_status())

@app.route('/api/strategies/add', methods=['POST'])
def add_strategy():
    """Add new strategy with memory optimization"""
    try:
        data = request.get_json()
        strategy_name = data.get('name')
        strategy_config = data.get('config', {})
        
        if not strategy_name:
            return jsonify({"error": "Strategy name required"}), 400
        
        success = trading_system.add_strategy(strategy_name, strategy_config)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Strategy '{strategy_name}' added successfully",
                "system_status": trading_system.get_system_status()
            })
        else:
            return jsonify({
                "status": "failed",
                "message": "Failed to add strategy (memory limit or capacity reached)",
                "system_status": trading_system.get_system_status()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error adding strategy: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/memory/status')
def memory_status():
    """Memory optimization status"""
    return jsonify({
        "memory_optimization": {
            "enabled": True,
            "current_usage_mb": log_memory_usage(),
            "optimization_settings": MEMORY_OPTIMIZATION,
            "system_capacity": trading_system.get_system_status()["memory_optimization"],
            "timestamp": datetime.now().isoformat()
        }
    })

# =============================================================================
# OPTIMIZED SOCKET EVENTS
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection with memory optimization"""
    logger.info("🔌 Client connected (optimized)")
    emit('system_status', trading_system.get_system_status())

@socketio.on('request_memory_status')
def handle_memory_status():
    """Handle memory status request"""
    emit('memory_status', {
        "usage_mb": log_memory_usage(),
        "optimization_enabled": True,
        "timestamp": datetime.now().isoformat()
    })

# =============================================================================
# MEMORY OPTIMIZATION BACKGROUND TASK
# =============================================================================

def memory_optimization_task():
    """Background task for memory optimization"""
    while True:
        try:
            time.sleep(MEMORY_OPTIMIZATION["memory_cleanup_interval"])
            trading_system.cleanup_memory()
        except Exception as e:
            logger.error(f"❌ Memory optimization task error: {e}")

# Start memory optimization background task
memory_thread = threading.Thread(target=memory_optimization_task, daemon=True)
memory_thread.start()

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Initial memory optimization
    optimize_memory()
    
    # Log initial status
    logger.info("🚀 Starting Memory-Optimized Trading System")
    logger.info(f"💾 Memory optimization settings: {MEMORY_OPTIMIZATION}")
    logger.info(f"📊 System capacity: {MEMORY_OPTIMIZATION['max_concurrent_strategies']} strategies")
    
    # Get initial memory usage
    initial_memory = log_memory_usage()
    logger.info(f"💾 Initial memory usage: {initial_memory:.1f}MB")
    
    # Start the optimized system
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)




