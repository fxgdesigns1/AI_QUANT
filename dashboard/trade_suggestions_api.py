#!/usr/bin/env python3
"""
TRADE SUGGESTIONS API
====================

Dashboard API for trade suggestions and execution:
1. Generate trade suggestions based on market analysis
2. Allow users to approve/reject suggestions
3. Execute trades directly from dashboard
4. Real-time trade status updates
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
from typing import Dict, List, Optional
import requests
import threading
import time

# Ensure project paths are importable relative to this repository
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
GCLOUD_DIR = os.path.join(REPO_ROOT, 'google-cloud-trading-system')
SRC_DIR = os.path.join(GCLOUD_DIR, 'src')
CORE_DIR = os.path.join(SRC_DIR, 'core')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if GCLOUD_DIR not in sys.path:
    sys.path.insert(0, GCLOUD_DIR)

from src.core.yaml_manager import get_yaml_manager  # type: ignore
from src.core.oanda_client import OandaClient  # type: ignore
from src.core.data_feed import get_data_feed  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradeSuggestionsAPI:
    """API for trade suggestions and execution"""
    
    def __init__(self):
        self.suggestions = []
        self.pending_trades = []
        self.executed_trades = []
        self.semi_auto_account_id = "101-004-30719775-001"
        
        # Load accounts
        self.load_accounts()
        
        # Start live data feed once to ensure suggestions have real prices
        try:
            self.data_feed = get_data_feed()
            # Start only if not already running (best-effort)
            if hasattr(self.data_feed, 'running') and not self.data_feed.running:
                self.data_feed.start()
                logger.info("✅ Live data feed started for trade suggestions")
        except Exception as e:
            logger.error(f"❌ Failed to start live data feed: {e}")
            # We don't raise here to keep API available for health/status
        
    def load_accounts(self):
        """Load all trading accounts"""
        try:
            yaml_mgr = get_yaml_manager()
            self.accounts_config = yaml_mgr.get_all_accounts()
            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts for trade suggestions")
        except Exception as e:
            logger.error(f"❌ Error loading accounts: {e}")
            self.accounts_config = []
    
    def generate_trade_suggestions(self) -> List[Dict]:
        """Generate trade suggestions based on market analysis"""
        suggestions = []
        
        try:
            # Get market data (feed should already be running)
            data_feed = getattr(self, 'data_feed', None) or get_data_feed()
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
            
            for instrument in instruments:
                try:
                    # Get current prices
                    prices = data_feed.get_latest_prices([instrument]) if data_feed else {}
                    if instrument in prices:
                        price_data = prices[instrument]
                        mid_price = (price_data.bid + price_data.ask) / 2
                        spread = price_data.ask - price_data.bid
                        
                        # Generate suggestions based on analysis
                        suggestion = self._analyze_instrument(instrument, mid_price, spread)
                        if suggestion:
                            suggestions.append(suggestion)
                            
                except Exception as e:
                    logger.error(f"❌ Error analyzing {instrument}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error generating suggestions: {e}")
            
        return suggestions
    
    def _analyze_instrument(self, instrument: str, price: float, spread: float) -> Optional[Dict]:
        """Analyze instrument and generate trade suggestion"""
        
        # Simple analysis logic (can be enhanced)
        if spread < 0.0005:  # Low spread opportunity
            return {
                'id': f"suggestion_{len(self.suggestions) + 1}",
                'instrument': instrument,
                'direction': 'BUY',  # Default to BUY for low spread
                'price': price,
                'spread': spread,
                'confidence': 0.8,
                'reason': 'Low spread opportunity',
                'suggested_account': self.semi_auto_account_id,
                'risk_level': 'LOW',
                'potential_profit': 0.001,  # 10 pips
                'stop_loss': 0.0005,  # 5 pips
                'take_profit': 0.001,  # 10 pips
                'timestamp': datetime.now().isoformat(),
                'status': 'PENDING'
            }
        elif spread > 0.001:  # High volatility opportunity
            return {
                'id': f"suggestion_{len(self.suggestions) + 1}",
                'instrument': instrument,
                'direction': 'SELL',  # Default to SELL for high volatility
                'price': price,
                'spread': spread,
                'confidence': 0.7,
                'reason': 'High volatility opportunity',
                'suggested_account': self.semi_auto_account_id,
                'risk_level': 'MEDIUM',
                'potential_profit': 0.002,  # 20 pips
                'stop_loss': 0.001,  # 10 pips
                'take_profit': 0.002,  # 20 pips
                'timestamp': datetime.now().isoformat(),
                'status': 'PENDING'
            }
        
        return None
    
    def approve_suggestion(self, suggestion_id: str) -> Dict:
        """Approve a trade suggestion and prepare for execution"""
        try:
            # Find the suggestion
            suggestion = None
            for s in self.suggestions:
                if s['id'] == suggestion_id:
                    suggestion = s
                    break
            
            if not suggestion:
                return {'success': False, 'error': 'Suggestion not found'}
            
            # Update suggestion status
            suggestion['status'] = 'APPROVED'
            suggestion['approved_at'] = datetime.now().isoformat()
            
            # Add to pending trades
            pending_trade = {
                'id': f"trade_{len(self.pending_trades) + 1}",
                'suggestion_id': suggestion_id,
                'instrument': suggestion['instrument'],
                'direction': suggestion['direction'],
                'price': suggestion['price'],
                'account_id': suggestion['suggested_account'],
                'status': 'READY_TO_EXECUTE',
                'created_at': datetime.now().isoformat()
            }
            
            self.pending_trades.append(pending_trade)
            
            logger.info(f"✅ Trade suggestion approved: {suggestion_id}")
            return {'success': True, 'trade_id': pending_trade['id']}
            
        except Exception as e:
            logger.error(f"❌ Error approving suggestion: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_trade(self, trade_id: str) -> Dict:
        """Execute a pending trade"""
        try:
            # Find the pending trade
            pending_trade = None
            for t in self.pending_trades:
                if t['id'] == trade_id:
                    pending_trade = t
                    break
            
            if not pending_trade:
                return {'success': False, 'error': 'Trade not found'}
            
            # Execute the trade (reads API key/env from environment)
            client = OandaClient(account_id=pending_trade['account_id'])
            
            # Calculate position size
            units = self._calculate_position_size(
                pending_trade['instrument'],
                pending_trade['account_id']
            )
            
            # Place the order
            order_result = client.place_market_order(
                instrument=pending_trade['instrument'],
                units=units if pending_trade['direction'] == 'BUY' else -units,
                stop_loss=0.0005,  # 5 pips
                take_profit=0.001  # 10 pips
            )
            
            if order_result.get('success', False):
                # Update trade status
                pending_trade['status'] = 'EXECUTED'
                pending_trade['executed_at'] = datetime.now().isoformat()
                pending_trade['order_id'] = order_result.get('order_id')
                
                # Move to executed trades
                self.executed_trades.append(pending_trade)
                self.pending_trades.remove(pending_trade)
                
                logger.info(f"✅ Trade executed successfully: {trade_id}")
                return {
                    'success': True,
                    'order_id': order_result.get('order_id'),
                    'message': 'Trade executed successfully'
                }
            else:
                return {
                    'success': False,
                    'error': order_result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_position_size(self, instrument: str, account_id: str) -> int:
        """Calculate position size based on risk management"""
        try:
            # Get account balance
            client = OandaClient(account_id=account_id)
            account_info = client.get_account_info()
            balance = getattr(account_info, 'balance', 100000)
            
            # Calculate position size (1% risk)
            risk_amount = balance * 0.01  # 1% of balance
            
            if 'XAU' in instrument:  # Gold
                return int(risk_amount / 10)  # Smaller units for gold
            else:  # Forex pairs
                return int(risk_amount / 100)  # Standard forex units
                
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return 1000  # Default fallback
    
    def get_trade_suggestions(self) -> List[Dict]:
        """Get current trade suggestions"""
        return self.suggestions
    
    def get_pending_trades(self) -> List[Dict]:
        """Get pending trades"""
        return self.pending_trades
    
    def get_executed_trades(self) -> List[Dict]:
        """Get executed trades"""
        return self.executed_trades
    
    def reject_suggestion(self, suggestion_id: str) -> Dict:
        """Reject a trade suggestion"""
        try:
            for suggestion in self.suggestions:
                if suggestion['id'] == suggestion_id:
                    suggestion['status'] = 'REJECTED'
                    suggestion['rejected_at'] = datetime.now().isoformat()
                    logger.info(f"✅ Trade suggestion rejected: {suggestion_id}")
                    return {'success': True}
            
            return {'success': False, 'error': 'Suggestion not found'}
            
        except Exception as e:
            logger.error(f"❌ Error rejecting suggestion: {e}")
            return {'success': False, 'error': str(e)}

# Flask app for trade suggestions API
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Health endpoint (define early so it's always registered before server starts)
@app.route('/health', methods=['GET'])
def health():
    """Lightweight health endpoint to verify service readiness"""
    try:
        api_key_present = bool(os.getenv('OANDA_API_KEY'))
        status = {
            'status': 'ok',
            'time': datetime.utcnow().isoformat() + 'Z',
            'oanda_api_key_configured': api_key_present,
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Initialize API
trade_api = TradeSuggestionsAPI()

@app.route('/api/trade-suggestions', methods=['GET'])
def get_suggestions():
    """Get trade suggestions"""
    try:
        suggestions = trade_api.get_trade_suggestions()
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trade-suggestions/generate', methods=['POST'])
def generate_suggestions():
    """Generate new trade suggestions"""
    try:
        suggestions = trade_api.generate_trade_suggestions()
        trade_api.suggestions = suggestions
        
        # Emit to WebSocket clients
        socketio.emit('new_suggestions', {
            'suggestions': suggestions,
            'count': len(suggestions)
        })
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trade-suggestions/<suggestion_id>/approve', methods=['POST'])
def approve_suggestion(suggestion_id):
    """Approve a trade suggestion"""
    try:
        result = trade_api.approve_suggestion(suggestion_id)
        
        if result['success']:
            # Emit to WebSocket clients
            socketio.emit('suggestion_approved', {
                'suggestion_id': suggestion_id,
                'trade_id': result['trade_id']
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trade-suggestions/<suggestion_id>/reject', methods=['POST'])
def reject_suggestion(suggestion_id):
    """Reject a trade suggestion"""
    try:
        result = trade_api.reject_suggestion(suggestion_id)
        
        if result['success']:
            # Emit to WebSocket clients
            socketio.emit('suggestion_rejected', {
                'suggestion_id': suggestion_id
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trades/<trade_id>/execute', methods=['POST'])
def execute_trade(trade_id):
    """Execute a pending trade"""
    try:
        result = trade_api.execute_trade(trade_id)
        
        if result['success']:
            # Emit to WebSocket clients
            socketio.emit('trade_executed', {
                'trade_id': trade_id,
                'order_id': result.get('order_id')
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trades/pending', methods=['GET'])
def get_pending_trades():
    """Get pending trades"""
    try:
        trades = trade_api.get_pending_trades()
        return jsonify({
            'success': True,
            'trades': trades,
            'count': len(trades)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trades/executed', methods=['GET'])
def get_executed_trades():
    """Get executed trades"""
    try:
        trades = trade_api.get_executed_trades()
        return jsonify({
            'success': True,
            'trades': trades,
            'count': len(trades)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dashboard/trade-suggestions')
def trade_suggestions_dashboard():
    """Trade suggestions dashboard page"""
    return render_template('trade_suggestions.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected to trade suggestions API')
    emit('connected', {'message': 'Connected to trade suggestions API'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected from trade suggestions API')

def start_trade_suggestions_api():
    """Start the trade suggestions API server"""
    logger.info("🚀 Starting Trade Suggestions API...")
    # Ensure minimal required configuration comes from environment
    if not os.getenv('OANDA_API_KEY'):
        logger.warning("⚠️ OANDA_API_KEY is not set. Live operations will fail until configured.")

    # Start the server
    socketio.run(app, host='0.0.0.0', port=8082, debug=False)

if __name__ == "__main__":
    start_trade_suggestions_api()

