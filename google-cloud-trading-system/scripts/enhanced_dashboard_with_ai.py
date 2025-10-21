#!/usr/bin/env python3
"""
Simple Enhanced Trading System Dashboard
Shows all system information without SocketIO dependencies
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

# Import OANDA components for live data
from src.core.oanda_client import OandaClient
from src.core.account_manager import AccountManager
from src.core.data_feed import LiveDataFeed

app = Flask(__name__)

# Initialize OANDA components for live data
account_manager = None
data_feed = None

def initialize_oanda_components():
    """Initialize OANDA components for live data"""
    global account_manager, data_feed
    try:
        account_manager = AccountManager()
        data_feed = LiveDataFeed()
        # Start the background live data feed threads
        try:
            data_feed.start()
            logger.info("✅ Live data feed started")
        except Exception as start_err:
            logger.error(f"❌ Failed to start live data feed: {start_err}")
        logger.info("✅ OANDA components initialized for live data")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OANDA components: {e}")
        account_manager = None
        data_feed = None

# Initialize OANDA components
initialize_oanda_components()

# Global system state
system_state = {
    'auto_trading_enabled': True,
    'current_mode': 'balanced',
    'active_strategies': {
        'PRIMARY': True,
        'GOLD': True, 
        'ALPHA': True
    },
    'kill_switches': {
        'emergency_stop': False,
        'pause_trading': False,
        'disable_news': False
    },
    'news_filters': {
        'high_impact_only': True,
        'currency_pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
        'exclude_keywords': ['war', 'terrorism', 'pandemic']
    },
    'last_update': datetime.now()
}

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Trading System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status-bar { 
            background: rgba(255,255,255,0.1); 
            padding: 15px; border-radius: 10px; 
            margin-bottom: 20px; display: flex; justify-content: space-between;
            align-items: center; flex-wrap: wrap;
        }
        .status-item { margin: 5px 10px; }
        .status-indicator { 
            display: inline-block; width: 12px; height: 12px; 
            border-radius: 50%; margin-right: 8px;
        }
        .status-online { background: #4CAF50; }
        .status-offline { background: #f44336; }
        .status-warning { background: #ff9800; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; padding: 20px; 
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .card h3 { margin-bottom: 15px; color: #64B5F6; }
        
        .control-panel { grid-column: 1 / -1; }
        .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .control-group { background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px; }
        .control-group h4 { margin-bottom: 10px; color: #81C784; }
        
        .btn { 
            padding: 10px 20px; border: none; border-radius: 5px; 
            cursor: pointer; font-weight: bold; margin: 5px; transition: all 0.3s;
        }
        .btn-primary { background: #2196F3; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn-success { background: #4CAF50; color: white; }
        .btn-warning { background: #ff9800; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        
        .account-card { margin-bottom: 15px; }
        .account-header { 
            display: flex; justify-content: space-between; 
            align-items: center; margin-bottom: 10px;
        }
        .account-name { font-weight: bold; font-size: 1.1em; }
        .account-balance { font-size: 1.2em; color: #81C784; }
        .account-pl { font-size: 1.1em; }
        .pl-positive { color: #4CAF50; }
        .pl-negative { color: #f44336; }
        
        .session-info { 
            background: rgba(0,0,0,0.3); padding: 15px; 
            border-radius: 10px; margin-bottom: 15px;
        }
        .session-active { border-left: 4px solid #4CAF50; }
        .session-inactive { border-left: 4px solid #ff9800; }
        
        .news-item { 
            margin-bottom: 10px; padding: 10px; 
            background: rgba(0,0,0,0.2); border-radius: 5px;
        }
        .news-title { font-weight: bold; margin-bottom: 5px; }
        .news-impact { 
            display: inline-block; padding: 2px 8px; 
            border-radius: 3px; font-size: 0.8em; margin-right: 10px;
        }
        .impact-high { background: #f44336; }
        .impact-medium { background: #ff9800; }
        .impact-low { background: #4CAF50; }
        
        .signal-item { 
            margin-bottom: 10px; padding: 10px; 
            background: rgba(0,0,0,0.2); border-radius: 5px;
            border-left: 4px solid #2196F3;
        }
        .signal-buy { border-left-color: #4CAF50; }
        .signal-sell { border-left-color: #f44336; }
        
        .toggle-switch { 
            position: relative; display: inline-block; 
            width: 60px; height: 34px;
        }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { 
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc; transition: .4s; border-radius: 34px;
        }
        .slider:before { 
            position: absolute; content: ""; height: 26px; width: 26px; 
            left: 4px; bottom: 4px; background-color: white; 
            transition: .4s; border-radius: 50%;
        }
        input:checked + .slider { background-color: #2196F3; }
        input:checked + .slider:before { transform: translateX(26px); }
        
        .mode-selector { display: flex; gap: 10px; margin-bottom: 15px; }
        .mode-btn { 
            padding: 8px 16px; border: 2px solid transparent; 
            border-radius: 5px; cursor: pointer; transition: all 0.3s;
        }
        .mode-btn.active { border-color: #2196F3; background: rgba(33, 150, 243, 0.3); }
        .mode-aggressive { background: rgba(244, 67, 54, 0.3); }
        .mode-balanced { background: rgba(255, 152, 0, 0.3); }
        .mode-relaxed { background: rgba(76, 175, 80, 0.3); }
        
        .strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
        .strategy-item { 
            background: rgba(0,0,0,0.2); padding: 10px; 
            border-radius: 5px; text-align: center;
        }
        .strategy-active { background: rgba(76, 175, 80, 0.3); }
        
        .footer { 
            text-align: center; margin-top: 30px; 
            padding: 20px; background: rgba(0,0,0,0.3); 
            border-radius: 10px;
        }
        
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .pulse { animation: pulse 2s infinite; }
        
        .london-countdown { 
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            padding: 20px; border-radius: 10px; text-align: center;
            margin-bottom: 20px; font-size: 1.2em; font-weight: bold;
        }
        
        /* AI Assistant Styles */
        .ai-assistant-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 400px;
            max-height: 70vh;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid #374151;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            display: none;
            flex-direction: column;
            z-index: 1100;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }
        
        .ai-assistant-header {
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #111827;
            border-bottom: 1px solid #374151;
        }
        
        .ai-assistant-title {
            font-weight: 600;
            color: #f1f5f9;
        }
        
        .ai-mode-badge {
            font-size: 12px;
            color: #f39c12;
            background: rgba(243, 156, 18, 0.2);
            padding: 2px 8px;
            border-radius: 12px;
        }
        
        .chat-messages {
            padding: 10px;
            overflow-y: auto;
            flex: 1;
            font-size: 14px;
            max-height: 300px;
        }
        
        .chat-input {
            display: flex;
            gap: 8px;
            padding: 10px;
            border-top: 1px solid #374151;
        }
        
        .chat-input textarea {
            flex: 1;
            resize: none;
            height: 48px;
            background: #0b1220;
            color: #e5e7eb;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 8px;
            font-size: 14px;
        }
        
        .send-button {
            background: #f39c12;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0 16px;
            cursor: pointer;
            font-weight: 600;
        }
        
        .message {
            margin-bottom: 10px;
            padding: 8px 12px;
            border-radius: 8px;
        }
        
        .message.user {
            background: rgba(59, 130, 246, 0.2);
            border-left: 3px solid #3b82f6;
            margin-left: 20px;
        }
        
        .message.assistant {
            background: rgba(16, 185, 129, 0.2);
            border-left: 3px solid #10b981;
            margin-right: 20px;
        }
        
        .ai-toggle {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            background: #f39c12 !important;
            color: white !important;
            border: none !important;
            border-radius: 50% !important;
            width: 60px !important;
            height: 60px !important;
            font-size: 24px !important;
            cursor: pointer !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            z-index: 9999 !important;
            display: block !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Trading System Dashboard</h1>
            <p>AI-Powered Adaptive Trading with Full Control</p>
        </div>
        
        <!-- London Session Countdown -->
        <div class="london-countdown" id="london-countdown">
            🇬🇧 London Session: <span id="london-status">INACTIVE</span> | 
            Next Session: <span id="next-session">LONDON in 6 hours</span>
        </div>
        
        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-item">
                <span class="status-indicator status-online" id="system-status"></span>
                <strong>System:</strong> <span id="system-text">Online</span>
            </div>
            <div class="status-item">
                <strong>Mode:</strong> <span id="current-mode">Balanced</span>
            </div>
            <div class="status-item">
                <strong>Auto Trading:</strong> <span id="auto-trading-status">Enabled</span>
            </div>
            <div class="status-item">
                <strong>Last Update:</strong> <span id="last-update">Loading...</span>
            </div>
        </div>
        
        <div class="grid">
            <!-- Control Panel -->
            <div class="card control-panel">
                <h3>🎛️ System Controls</h3>
                
                <!-- Mode Selection -->
                <div class="control-group">
                    <h4>📊 Trading Mode</h4>
                    <div class="mode-selector">
                        <div class="mode-btn mode-aggressive" onclick="setMode('aggressive')">Aggressive</div>
                        <div class="mode-btn mode-balanced active" onclick="setMode('balanced')">Balanced</div>
                        <div class="mode-btn mode-relaxed" onclick="setMode('relaxed')">Relaxed</div>
                    </div>
                </div>
                
                <!-- Strategy Controls -->
                <div class="control-group">
                    <h4>🎯 Active Strategies</h4>
                    <div class="strategy-grid">
                        <div class="strategy-item strategy-active" onclick="toggleStrategy('PRIMARY')">
                            <div>PRIMARY</div>
                            <div>EMA Crossovers</div>
                        </div>
                        <div class="strategy-item strategy-active" onclick="toggleStrategy('GOLD')">
                            <div>GOLD</div>
                            <div>Bollinger + RSI</div>
                        </div>
                        <div class="strategy-item strategy-active" onclick="toggleStrategy('ALPHA')">
                            <div>ALPHA</div>
                            <div>All Strategies</div>
                        </div>
                    </div>
                </div>
                
                <!-- Kill Switches -->
                <div class="control-group">
                    <h4>🛑 Emergency Controls</h4>
                    <button class="btn btn-danger" onclick="emergencyStop()">🚨 EMERGENCY STOP</button>
                    <button class="btn btn-warning" onclick="pauseTrading()">⏸️ Pause Trading</button>
                    <button class="btn btn-primary" onclick="resumeTrading()">▶️ Resume Trading</button>
                </div>
                
                <!-- Auto Trading Toggle -->
                <div class="control-group">
                    <h4>🤖 Auto Trading</h4>
                    <label class="toggle-switch">
                        <input type="checkbox" id="auto-trading-toggle" checked onchange="toggleAutoTrading()">
                        <span class="slider"></span>
                    </label>
                    <span style="margin-left: 10px;">Enable Automatic Trading</span>
                </div>
            </div>
            
            <!-- Account Status -->
            <div class="card">
                <h3>💰 Account Status</h3>
                <div id="account-status">
                    <div style="text-align: center; padding: 20px; color: #64B5F6;">
                        <div class="pulse">🔄 Loading live account data...</div>
                    </div>
                </div>
            </div>
            
            <!-- Session Information -->
            <div class="card">
                <h3>📊 Trading Sessions</h3>
                <div class="session-info session-inactive" id="current-session">
                    <h4>Current Session: Tokyo</h4>
                    <p>Volatility: 0.8x | Max Positions: 4</p>
                    <p>Preferred Pairs: USD_JPY, AUD_JPY, NZD_JPY</p>
                </div>
                <div class="session-info session-active" id="london-session">
                    <h4>🇬🇧 London Session (8:00 AM - 5:00 PM UTC)</h4>
                    <p>Volatility: 1.5x | Max Positions: 8</p>
                    <p>Preferred Pairs: EUR_USD, GBP_USD, USD_JPY, XAU_USD</p>
                    <p><strong>Enhanced Trading: ACTIVE</strong></p>
                </div>
                <div class="session-info session-inactive" id="overlap-session">
                    <h4>🔄 London-NY Overlap (1:00 PM - 5:00 PM UTC)</h4>
                    <p>Volatility: 2.0x | Max Positions: 10</p>
                    <p>Maximum trading activity period</p>
                </div>
            </div>
            
            <!-- News Feed -->
            <div class="card">
                <h3>📰 Market News</h3>
                <div class="control-group">
                    <h4>🔍 News Filters</h4>
                    <label class="toggle-switch">
                        <input type="checkbox" id="high-impact-only" checked onchange="updateNewsFilters()">
                        <span class="slider"></span>
                    </label>
                    <span style="margin-left: 10px;">High Impact Only</span>
                </div>
                <div id="news-feed">
                    <div class="news-item">
                        <div class="news-title">Fed Signals Potential Rate Cut</div>
                        <span class="news-impact impact-high">HIGH</span>
                        <span>USD weakness expected, Gold bullish</span>
                    </div>
                    <div class="news-item">
                        <div class="news-title">ECB Maintains Current Policy</div>
                        <span class="news-impact impact-medium">MEDIUM</span>
                        <span>EUR stability, range-bound trading</span>
                    </div>
                </div>
            </div>
            
            <!-- Trading Signals -->
            <div class="card">
                <h3>📊 Live Signals</h3>
                <div id="signals-feed">
                    <div style="text-align: center; padding: 20px; color: #64B5F6;">
                        <div class="pulse">🔄 Loading live trading signals...</div>
                    </div>
                </div>
            </div>
            
            <!-- Live Prices -->
            <div class="card">
                <h3>💱 Live Prices</h3>
                <div id="live-prices">
                    <div style="text-align: center; padding: 20px; color: #64B5F6;">
                        <div class="pulse">🔄 Loading live market prices...</div>
                    </div>
                </div>
            </div>
            
            <!-- System Performance -->
            <div class="card">
                <h3>📈 Performance Metrics</h3>
                <div id="performance-metrics">
                    <div style="text-align: center; padding: 20px; color: #64B5F6;">
                        <div class="pulse">🔄 Loading live performance data...</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🚀 Enhanced Trading System | AI-Powered | Real-time Monitoring | Full Control</p>
            <p>Last Updated: <span id="footer-time">Loading...</span></p>
        </div>
    </div>

    <script>
        // Global state
        let currentMode = 'balanced';
        let autoTradingEnabled = true;
        let activeStrategies = {PRIMARY: true, GOLD: true, ALPHA: true};
        let killSwitches = {emergency_stop: false, pause_trading: false, disable_news: false};
        
        // Simple data loading function
        function loadData() {
            console.log('🔄 Loading data...');
            
            // Load accounts
            fetch('/api/accounts')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('account-status');
                    if (container && data.accounts) {
                        container.innerHTML = '';
                        Object.keys(data.accounts).forEach(function(name) {
                            var account = data.accounts[name];
                            var plClass = account.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                            var plSign = account.total_pl >= 0 ? '+' : '';
                            container.innerHTML += '<div class="account-card"><div class="account-header"><span class="account-name">' + name + '</span><span class="account-balance">$' + account.balance.toLocaleString() + '</span></div><div class="account-pl ' + plClass + '">' + plSign + '$' + account.total_pl.toFixed(2) + ' (' + plSign + account.pl_percentage.toFixed(2) + '%)</div><div>Positions: ' + account.open_positions + ' | Margin: ' + account.margin_used.toFixed(1) + '%</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Account error:', error); });
            
            // Load prices
            fetch('/api/prices')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('live-prices');
                    if (container && data.prices) {
                        container.innerHTML = '';
                        Object.keys(data.prices).forEach(function(instrument) {
                            var price = data.prices[instrument];
                            var spread = (price.ask - price.bid).toFixed(5);
                            var timestamp = new Date(price.timestamp).toLocaleTimeString();
                            container.innerHTML += '<div class="signal-item" style="margin-bottom: 10px;"><strong>' + instrument + '</strong><br><div style="font-size: 14px; margin: 5px 0;">Bid: <span style="color: #4CAF50;">' + price.bid.toFixed(5) + '</span> | Ask: <span style="color: #f44336;">' + price.ask.toFixed(5) + '</span></div><div style="font-size: 11px; color: #9ca3af;">Spread: ' + spread + ' | Live: ' + timestamp + '</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Prices error:', error); });
            
            // Load signals
            fetch('/api/signals')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('signals-feed');
                    if (container && data.signals) {
                        container.innerHTML = '';
                        data.signals.forEach(function(signal) {
                            var signalClass = signal.signal_type === 'BUY' ? 'signal-buy' : 'signal-sell';
                            container.innerHTML += '<div class="signal-item ' + signalClass + '"><strong>' + signal.instrument + ' ' + signal.signal_type + '</strong> - ' + signal.strategy + '<br><small>Entry: ' + signal.entry_price.toFixed(5) + ' | SL: ' + signal.stop_loss.toFixed(5) + ' | TP: ' + signal.take_profit.toFixed(5) + '</small><div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">Confidence: ' + (signal.confidence * 100).toFixed(0) + '% | Live: ' + new Date(signal.timestamp).toLocaleTimeString() + '</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Signals error:', error); });
            
            // Load performance
            fetch('/api/performance')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('performance-metrics');
                    if (container) {
                        var plClass = data.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                        var plSign = data.total_pl >= 0 ? '+' : '';
                        container.innerHTML = '<div style="margin-bottom: 10px;"><strong>Total P&L:</strong> <span class="' + plClass + '">' + plSign + '$' + data.total_pl.toFixed(2) + ' (' + plSign + data.pl_percentage.toFixed(2) + '%)</span></div><div style="margin-bottom: 10px;"><strong>Portfolio Value:</strong> $' + data.portfolio_value.toFixed(2) + '</div><div style="margin-bottom: 10px;"><strong>Open Positions:</strong> ' + data.session_trades + '</div><div style="margin-bottom: 10px;"><strong>London Session Ready:</strong> ' + (data.london_ready ? '✅ Yes' : '❌ No') + '</div><div style="margin-bottom: 10px;"><strong>Auto Trading:</strong> ' + (data.auto_trading ? '✅ Enabled' : '❌ Disabled') + '</div><div style="margin-bottom: 10px; font-size: 12px; color: #9ca3af;"><strong>Data Source:</strong> ' + data.data_source + '</div>';
                    }
                })
                .catch(function(error) { console.error('Performance error:', error); });
        }
        
        // Simple initialization
        window.onload = function() {
            console.log('🚀 Page loaded, loading data...');
            setTimeout(function() {
                loadData();
            }, 1000);
        };
        
        // Auto-refresh every 5 seconds
        setInterval(function() {
            loadData();
        }, 5000);
        
        // Real-time updates
        function startRealTimeUpdates() {
            setInterval(() => {
                updateStatus();
                loadAccountStatus();
                loadSignals();
                loadLivePrices();
                loadPerformanceMetrics();
                updateLondonCountdown();
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                document.getElementById('footer-time').textContent = new Date().toLocaleString();
            }, 5000);
        }
        
        // London session countdown
        function updateLondonCountdown() {
            const now = new Date();
            const utcHour = now.getUTCHours();
            
            let londonStatus, nextSession, hoursUntil;
            
            if (utcHour >= 8 && utcHour < 17) {
                londonStatus = 'ACTIVE';
                nextSession = 'London session is running';
                document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #4CAF50, #81C784)';
            } else if (utcHour >= 13 && utcHour < 17) {
                londonStatus = 'OVERLAP ACTIVE';
                nextSession = 'London-NY Overlap running';
                document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #ff9800, #ffc107)';
            } else {
                londonStatus = 'INACTIVE';
                if (utcHour < 8) {
                    hoursUntil = 8 - utcHour;
                    nextSession = 'LONDON in ' + hoursUntil + ' hours';
                } else {
                    hoursUntil = 24 - utcHour + 8;
                    nextSession = 'LONDON in ' + hoursUntil + ' hours';
                }
                document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #ff6b6b, #4ecdc4)';
            }
            
            document.getElementById('london-status').textContent = londonStatus;
            document.getElementById('next-session').textContent = nextSession;
        }
        
        // Status updates
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.system_online) {
                        document.getElementById('system-status').className = 'status-indicator status-online';
                        document.getElementById('system-text').textContent = 'Online';
                    } else {
                        document.getElementById('system-status').className = 'status-indicator status-offline';
                        document.getElementById('system-text').textContent = 'Offline';
                    }
                    
                    document.getElementById('current-mode').textContent = data.current_mode || 'Balanced';
                    document.getElementById('auto-trading-status').textContent = 
                        data.auto_trading_enabled ? 'Enabled' : 'Disabled';
                })
                .catch(error => {
                    console.error('Status update error:', error);
                    document.getElementById('system-status').className = 'status-indicator status-warning';
                    document.getElementById('system-text').textContent = 'Error';
                });
        }
        
        // Account status
        function loadAccountStatus() {
            fetch('/api/accounts')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('account-status');
                    container.innerHTML = '';
                    
                    Object.entries(data.accounts || {}).forEach(([name, account]) => {
                        const plClass = account.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                        const plSign = account.total_pl >= 0 ? '+' : '';
                        
                        container.innerHTML += 
                            '<div class="account-card">' +
                                '<div class="account-header">' +
                                    '<span class="account-name">' + name + '</span>' +
                                    '<span class="account-balance">$' + account.balance.toLocaleString() + '</span>' +
                                '</div>' +
                                '<div class="account-pl ' + plClass + '">' + plSign + '$' + account.total_pl.toFixed(2) + ' (' + plSign + account.pl_percentage.toFixed(2) + '%)</div>' +
                                '<div>Positions: ' + account.open_positions + ' | Margin: ' + account.margin_used.toFixed(1) + '%</div>' +
                            '</div>';
                    });
                })
                .catch(error => console.error('Account status error:', error));
        }
        
        // News feed
        function loadNewsFeed() {
            fetch('/api/news')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('news-feed');
                    container.innerHTML = '';
                    
                    (data.news || []).forEach(news => {
                        const impactClass = news.impact === 'high' ? 'impact-high' : 
                                          news.impact === 'medium' ? 'impact-medium' : 'impact-low';
                        
                        container.innerHTML += 
                            '<div class="news-item">' +
                                '<div class="news-title">' + news.title + '</div>' +
                                '<span class="news-impact ' + impactClass + '">' + news.impact.toUpperCase() + '</span>' +
                                '<span>' + news.summary + '</span>' +
                            '</div>';
                    });
                })
                .catch(error => console.error('News feed error:', error));
        }
        
        // Trading signals
        function loadSignals() {
            fetch('/api/signals')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('signals-feed');
                    container.innerHTML = '';
                    
                    if (data.signals && data.signals.length > 0) {
                        data.signals.forEach(signal => {
                            const signalClass = signal.signal_type === 'BUY' ? 'signal-buy' : 'signal-sell';
                            
                            container.innerHTML += 
                                '<div class="signal-item ' + signalClass + '">' +
                                    '<strong>' + signal.instrument + ' ' + signal.signal_type + '</strong> - ' + signal.strategy + '<br>' +
                                    '<small>Entry: ' + signal.entry_price.toFixed(5) + ' | SL: ' + signal.stop_loss.toFixed(5) + ' | TP: ' + signal.take_profit.toFixed(5) + '</small>' +
                                    '<div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">' +
                                        'Confidence: ' + (signal.confidence * 100).toFixed(0) + '% | Live: ' + new Date(signal.timestamp).toLocaleTimeString() +
                                    '</div>' +
                                '</div>';
                        });
                    } else {
                        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #9ca3af;">No active signals</div>';
                    }
                })
                .catch(error => {
                    console.error('Signals error:', error);
                    document.getElementById('signals-feed').innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336;">Error loading signals</div>';
                });
        }
        
        // Live prices
        function loadLivePrices() {
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('live-prices');
                    container.innerHTML = '';
                    
                    if (data.prices && Object.keys(data.prices).length > 0) {
                        Object.entries(data.prices).forEach(([instrument, price]) => {
                            const spread = (price.ask - price.bid).toFixed(5);
                            const timestamp = new Date(price.timestamp).toLocaleTimeString();
                            
                            container.innerHTML += 
                                '<div class="signal-item" style="margin-bottom: 10px;">' +
                                    '<strong>' + instrument + '</strong><br>' +
                                    '<div style="font-size: 14px; margin: 5px 0;">' +
                                        'Bid: <span style="color: #4CAF50;">' + price.bid.toFixed(5) + '</span> | ' +
                                        'Ask: <span style="color: #f44336;">' + price.ask.toFixed(5) + '</span>' +
                                    '</div>' +
                                    '<div style="font-size: 11px; color: #9ca3af;">' +
                                        'Spread: ' + spread + ' | Live: ' + timestamp +
                                    '</div>' +
                                '</div>';
                        });
                    } else {
                        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #9ca3af;">No price data available</div>';
                    }
                })
                .catch(error => {
                    console.error('Prices error:', error);
                    document.getElementById('live-prices').innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336;">Error loading prices</div>';
                });
        }
        
        // Performance metrics
        function loadPerformanceMetrics() {
            fetch('/api/performance')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('performance-metrics');
                    const plClass = data.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                    const plSign = data.total_pl >= 0 ? '+' : '';
                    
                    container.innerHTML = 
                        '<div style="margin-bottom: 10px;">' +
                            '<strong>Total P&L:</strong> <span class="' + plClass + '">' + plSign + '$' + data.total_pl.toFixed(2) + ' (' + plSign + data.pl_percentage.toFixed(2) + '%)</span>' +
                        '</div>' +
                        '<div style="margin-bottom: 10px;">' +
                            '<strong>Portfolio Value:</strong> $' + data.portfolio_value.toFixed(2) +
                        '</div>' +
                        '<div style="margin-bottom: 10px;">' +
                            '<strong>Open Positions:</strong> ' + data.session_trades +
                        '</div>' +
                        '<div style="margin-bottom: 10px;">' +
                            '<strong>London Session Ready:</strong> ' + (data.london_ready ? '✅ Yes' : '❌ No') +
                        '</div>' +
                        '<div style="margin-bottom: 10px;">' +
                            '<strong>Auto Trading:</strong> ' + (data.auto_trading ? '✅ Enabled' : '❌ Disabled') +
                        '</div>' +
                        '<div style="margin-bottom: 10px; font-size: 12px; color: #9ca3af;">' +
                            '<strong>Data Source:</strong> ' + data.data_source +
                        '</div>';
                })
                .catch(error => {
                    console.error('Performance error:', error);
                    document.getElementById('performance-metrics').innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336;">Error loading performance data</div>';
                });
        }
        
        // Mode switching
        function setMode(mode) {
            currentMode = mode;
            
            // Update UI
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update backend
            fetch('/api/set-mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Mode changed to ' + mode.toUpperCase());
                }
            })
            .catch(error => console.error('Mode change error:', error));
        }
        
        // Strategy toggling
        function toggleStrategy(strategy) {
            activeStrategies[strategy] = !activeStrategies[strategy];
            
            const element = event.target.closest('.strategy-item');
            if (activeStrategies[strategy]) {
                element.classList.add('strategy-active');
            } else {
                element.classList.remove('strategy-active');
            }
            
            // Update backend
            fetch('/api/toggle-strategy', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({strategy: strategy, enabled: activeStrategies[strategy]})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log(strategy + ' strategy ' + (activeStrategies[strategy] ? 'enabled' : 'disabled'));
                }
            })
            .catch(error => console.error('Strategy toggle error:', error));
        }
        
        // Emergency controls
        function emergencyStop() {
            if (confirm('🚨 EMERGENCY STOP: This will immediately halt all trading activities. Continue?')) {
                fetch('/api/emergency-stop', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            killSwitches.emergency_stop = true;
                            console.log('🚨 EMERGENCY STOP ACTIVATED');
                            updateStatus();
                        }
                    })
                    .catch(error => console.error('Emergency stop error:', error));
            }
        }
        
        function pauseTrading() {
            fetch('/api/pause-trading', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        killSwitches.pause_trading = true;
                        console.log('⏸️ Trading paused');
                        updateStatus();
                    }
                })
                .catch(error => console.error('Pause trading error:', error));
        }
        
        function resumeTrading() {
            fetch('/api/resume-trading', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        killSwitches.pause_trading = false;
                        console.log('▶️ Trading resumed');
                        updateStatus();
                    }
                })
                .catch(error => console.error('Resume trading error:', error));
        }
        
        // Auto trading toggle
        function toggleAutoTrading() {
            autoTradingEnabled = document.getElementById('auto-trading-toggle').checked;
            
            fetch('/api/toggle-auto-trading', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: autoTradingEnabled})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Auto trading ' + (autoTradingEnabled ? 'enabled' : 'disabled'));
                    updateStatus();
                }
            })
            .catch(error => console.error('Auto trading toggle error:', error));
        }
        
        // News filters
        function updateNewsFilters() {
            const highImpactOnly = document.getElementById('high-impact-only').checked;
            
            fetch('/api/update-news-filters', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({high_impact_only: highImpactOnly})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadNewsFeed(); // Reload with new filters
                }
            })
            .catch(error => console.error('News filters error:', error));
        }

        // AI Assistant Functions
        function toggleAIAssistant() {
            const panel = document.getElementById('aiAssistantPanel');
            if (panel.style.display === 'none') {
                panel.style.display = 'flex';
            } else {
                panel.style.display = 'none';
            }
        }

        async function sendAIMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessageToChat('user', message);
            input.value = '';
            
            try {
                const response = await fetch('/ai/interpret', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: 'dashboard'
                    })
                });
                
                const data = await response.json();
                
                if (data.reply) {
                    addMessageToChat('assistant', data.reply);
                } else {
                    addMessageToChat('assistant', 'Sorry, I encountered an error processing your request.');
                }
                
            } catch (error) {
                console.error('AI Assistant error:', error);
                addMessageToChat('assistant', 'Sorry, I\'m having trouble connecting. Please try again.');
            }
        }

        function addMessageToChat(type, message) {
            const messages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;
            
            const time = new Date().toLocaleTimeString();
            messageDiv.innerHTML = 
                '<div>' + message + '</div>' +
                '<div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">' + time + '</div>';
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }

        // Initialize AI Assistant
        function initAIAssistant() {
            console.log('🤖 Initializing AI Assistant...');
            
            // Get UI elements
            const aiButton = document.getElementById('aiToggleButton');
            const aiPanel = document.getElementById('aiAssistantPanel');
            
            console.log('Button:', aiButton);
            console.log('Panel:', aiPanel);
            
            if (!aiButton || !aiPanel) {
                console.error('❌ AI components not found, retrying in 1s...');
                setTimeout(initAIAssistant, 1000);
                return;
            }
            
            console.log('✅ AI components found');
            
            // Setup toggle functionality
            function toggleAIAssistant() {
                console.log('🔄 Toggling AI panel');
                if (aiPanel.style.display === 'none' || !aiPanel.style.display) {
                    aiPanel.style.display = 'flex';
                    aiButton.style.backgroundColor = '#2196F3';
                } else {
                    aiPanel.style.display = 'none';
                    aiButton.style.backgroundColor = '#f39c12';
                }
            }
            
            // Add click handler
            aiButton.onclick = toggleAIAssistant;
            
            // Initial state
            aiButton.style.display = 'block';
            aiPanel.style.display = 'none';
            
            // Setup chat input
            const chatInput = document.getElementById('chatInput');
            if (chatInput) {
                chatInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendAIMessage();
                    }
                });
            }
        }
        
        // Simple data loading - inline execution
        setTimeout(function() {
            console.log('🚀 Loading data...');
            
            // Load accounts
            fetch('/api/accounts')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('account-status');
                    if (container && data.accounts) {
                        container.innerHTML = '';
                        Object.keys(data.accounts).forEach(function(name) {
                            var account = data.accounts[name];
                            var plClass = account.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                            var plSign = account.total_pl >= 0 ? '+' : '';
                            container.innerHTML += '<div class="account-card"><div class="account-header"><span class="account-name">' + name + '</span><span class="account-balance">$' + account.balance.toLocaleString() + '</span></div><div class="account-pl ' + plClass + '">' + plSign + '$' + account.total_pl.toFixed(2) + ' (' + plSign + account.pl_percentage.toFixed(2) + '%)</div><div>Positions: ' + account.open_positions + ' | Margin: ' + account.margin_used.toFixed(1) + '%</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Account error:', error); });
            
            // Load prices
            fetch('/api/prices')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('live-prices');
                    if (container && data.prices) {
                        container.innerHTML = '';
                        Object.keys(data.prices).forEach(function(instrument) {
                            var price = data.prices[instrument];
                            var spread = (price.ask - price.bid).toFixed(5);
                            var timestamp = new Date(price.timestamp).toLocaleTimeString();
                            container.innerHTML += '<div class="signal-item" style="margin-bottom: 10px;"><strong>' + instrument + '</strong><br><div style="font-size: 14px; margin: 5px 0;">Bid: <span style="color: #4CAF50;">' + price.bid.toFixed(5) + '</span> | Ask: <span style="color: #f44336;">' + price.ask.toFixed(5) + '</span></div><div style="font-size: 11px; color: #9ca3af;">Spread: ' + spread + ' | Live: ' + timestamp + '</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Prices error:', error); });
            
            // Load signals
            fetch('/api/signals')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('signals-feed');
                    if (container && data.signals) {
                        container.innerHTML = '';
                        data.signals.forEach(function(signal) {
                            var signalClass = signal.signal_type === 'BUY' ? 'signal-buy' : 'signal-sell';
                            container.innerHTML += '<div class="signal-item ' + signalClass + '"><strong>' + signal.instrument + ' ' + signal.signal_type + '</strong> - ' + signal.strategy + '<br><small>Entry: ' + signal.entry_price.toFixed(5) + ' | SL: ' + signal.stop_loss.toFixed(5) + ' | TP: ' + signal.take_profit.toFixed(5) + '</small><div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">Confidence: ' + (signal.confidence * 100).toFixed(0) + '% | Live: ' + new Date(signal.timestamp).toLocaleTimeString() + '</div></div>';
                        });
                    }
                })
                .catch(function(error) { console.error('Signals error:', error); });
            
            // Load performance
            fetch('/api/performance')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    var container = document.getElementById('performance-metrics');
                    if (container) {
                        var plClass = data.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
                        var plSign = data.total_pl >= 0 ? '+' : '';
                        container.innerHTML = '<div style="margin-bottom: 10px;"><strong>Total P&L:</strong> <span class="' + plClass + '">' + plSign + '$' + data.total_pl.toFixed(2) + ' (' + plSign + data.pl_percentage.toFixed(2) + '%)</span></div><div style="margin-bottom: 10px;"><strong>Portfolio Value:</strong> $' + data.portfolio_value.toFixed(2) + '</div><div style="margin-bottom: 10px;"><strong>Open Positions:</strong> ' + data.session_trades + '</div><div style="margin-bottom: 10px;"><strong>London Session Ready:</strong> ' + (data.london_ready ? '✅ Yes' : '❌ No') + '</div><div style="margin-bottom: 10px;"><strong>Auto Trading:</strong> ' + (data.auto_trading ? '✅ Enabled' : '❌ Disabled') + '</div><div style="margin-bottom: 10px; font-size: 12px; color: #9ca3af;"><strong>Data Source:</strong> ' + data.data_source + '</div>';
                    }
                })
                .catch(function(error) { console.error('Performance error:', error); });
        }, 2000);
    </script>

    <!-- AI Assistant Panel -->
    <div class="ai-assistant-panel" id="aiAssistantPanel">
        <div class="ai-assistant-header">
            <div class="ai-assistant-title">🤖 AI Assistant</div>
            <div class="ai-mode-badge">Demo Mode</div>
            <button onclick="toggleAIAssistant()" style="background: none; border: none; color: #f1f5f9; cursor: pointer; font-size: 18px;">×</button>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div style="padding: 10px; color: #94a3b8; font-size: 14px;">
                🤖 AI Assistant ready. Ask me about market conditions, positions, or system status.
            </div>
        </div>
        <div class="chat-input">
            <textarea id="chatInput" placeholder="Ask about market overview, positions, or system health..."></textarea>
            <button class="send-button" onclick="sendAIMessage()">Send</button>
        </div>
    </div>

    <!-- AI Toggle Button -->
    <button id="aiToggleButton" class="ai-toggle">🤖</button>
</body>
</html>
    ''')

# AI Assistant API Routes
@app.route('/ai/interpret', methods=['POST'])
def ai_interpret():
    """AI Assistant interpret endpoint"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', 'dashboard')
        
        # Simple AI responses based on keywords
        message_lower = message.lower()
        
        if 'market overview' in message_lower or 'market' in message_lower:
            reply = "📊 **Market Overview**: Current market conditions show mixed signals across major pairs. EUR/USD is consolidating around 1.0850, GBP/USD showing bullish momentum at 1.2650, and XAU/USD testing resistance at 2020. Volatility remains moderate with upcoming economic data releases."
        elif 'positions' in message_lower or 'position' in message_lower:
            reply = "📈 **Current Positions**: You have 3 active positions across EUR/USD, GBP/USD, and XAU/USD. Overall portfolio exposure is at 8.5% with a net unrealized P&L of +$1,250. Risk management parameters are within acceptable limits."
        elif 'risk' in message_lower or 'exposure' in message_lower:
            reply = "🛡️ **Risk Assessment**: Total portfolio exposure is 8.5% (within 10% limit). Maximum drawdown is 2.1%. All positions have stop-loss orders in place. Risk metrics are healthy and within predefined parameters."
        elif 'signals' in message_lower or 'signal' in message_lower:
            reply = "🎯 **Recent Signals**: Generated 2 new signals in the last hour - BUY EUR/USD (confidence: 78%) and SELL XAU/USD (confidence: 65%). Both signals meet our risk criteria and are being monitored for entry opportunities."
        elif 'system' in message_lower or 'health' in message_lower or 'status' in message_lower:
            reply = "✅ **System Health**: All systems operational. Data feeds are stable, OANDA connection is active, and all trading strategies are running normally. Last system check: 2 minutes ago. No issues detected."
        elif 'help' in message_lower:
            reply = "🤖 **AI Assistant Help**: I can help you with:\n• Market overview and analysis\n• Position and portfolio status\n• Risk assessment and exposure\n• Trading signals and opportunities\n• System health and status\n• Strategy performance metrics\n\nJust ask me about any of these topics!"
        else:
            reply = f"🤖 I understand you're asking about: '{message}'. I can help with market analysis, position management, risk assessment, trading signals, and system status. Could you be more specific about what you'd like to know?"
        
        return jsonify({
            'reply': reply,
            'intent': 'information_request',
            'requires_confirmation': False,
            'mode': 'demo',
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ai/health', methods=['GET'])
def ai_health():
    """AI Assistant health check"""
    return jsonify({
        'status': 'healthy',
        'mode': 'demo',
        'features': ['market_analysis', 'position_management', 'risk_assessment', 'signal_analysis', 'system_status']
    })

# API Endpoints
@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        return jsonify({
            'system_online': True,
            'current_mode': system_state['current_mode'],
            'auto_trading_enabled': system_state['auto_trading_enabled'],
            'kill_switches': system_state['kill_switches'],
            'active_strategies': system_state['active_strategies'],
            'last_update': system_state['last_update'].isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts')
def api_accounts():
    """Get live account status from OANDA"""
    try:
        if not account_manager:
            return jsonify({'error': 'OANDA not initialized'}), 500
            
        account_data = {}
        
        # Get live data from all accounts
        for account_name, client in account_manager.accounts.items():
            try:
                account_info = client.get_account_info()
                if account_info:
                    account_data[account_name] = {
                        'balance': account_info.balance,
                        'total_pl': account_info.unrealized_pl + account_info.realized_pl,
                        'pl_percentage': ((account_info.unrealized_pl + account_info.realized_pl) / account_info.balance * 100) if account_info.balance > 0 else 0,
                        'open_positions': account_info.open_position_count,
                        'margin_used': account_info.margin_used,
                        'margin_available': account_info.margin_available,
                        'currency': account_info.currency
                    }
            except Exception as e:
                logger.error(f"Failed to get data for {account_name}: {e}")
                # Fallback to basic data if API fails
                account_data[account_name] = {
                    'balance': 0,
                    'total_pl': 0,
                    'pl_percentage': 0,
                    'open_positions': 0,
                    'margin_used': 0,
                    'margin_available': 0,
                    'currency': 'USD',
                    'error': 'API connection failed'
                }
        
        return jsonify({'accounts': account_data})
    except Exception as e:
        logger.error(f"Account API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    """Get filtered news feed"""
    try:
        news_data = [
            {
                'title': 'Fed Signals Potential Rate Cut',
                'summary': 'USD weakness expected, Gold bullish',
                'impact': 'high',
                'timestamp': datetime.now().isoformat()
            },
            {
                'title': 'ECB Maintains Current Policy',
                'summary': 'EUR stability, range-bound trading',
                'impact': 'medium',
                'timestamp': datetime.now().isoformat()
            },
            {
                'title': 'Bank of Japan Intervention Watch',
                'summary': 'JPY volatility expected',
                'impact': 'medium',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Apply filters
        if system_state['news_filters']['high_impact_only']:
            news_data = [news for news in news_data if news['impact'] == 'high']
        
        return jsonify({'news': news_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals')
def api_signals():
    """Get live trading signals from OANDA data"""
    try:
        signals_data = []
        
        if data_feed:
            # Get live prices for major pairs
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
            
            for instrument in instruments:
                try:
                    market_data = data_feed.get_market_data(instrument)
                    if instrument in market_data:
                        price_data = market_data[instrument]
                        # Simple signal generation based on live prices
                        current_price = (price_data.bid + price_data.ask) / 2
                        
                        # Basic signal logic (replace with your strategy)
                        if instrument == 'EUR_USD':
                            if current_price > 1.1000:
                                signals_data.append({
                                    'instrument': instrument,
                                    'signal_type': 'BUY',
                                    'strategy': 'Price above 1.1000',
                                    'entry_price': current_price,
                                    'stop_loss': current_price - 0.0020,
                                    'take_profit': current_price + 0.0030,
                                    'confidence': 0.75,
                                    'timestamp': price_data.timestamp,
                                    'bid': price_data.bid,
                                    'ask': price_data.ask,
                                    'spread': price_data.spread
                                })
                        elif instrument == 'XAU_USD':
                            if current_price > 2650:
                                signals_data.append({
                                    'instrument': instrument,
                                    'signal_type': 'SELL',
                                    'strategy': 'Resistance level',
                                    'entry_price': current_price,
                                    'stop_loss': current_price + 10,
                                    'take_profit': current_price - 20,
                                    'confidence': 0.70,
                                    'timestamp': price_data.timestamp,
                                    'bid': price_data.bid,
                                    'ask': price_data.ask,
                                    'spread': price_data.spread
                                })
                except Exception as e:
                    logger.error(f"Failed to get signal for {instrument}: {e}")
        
        # If no live data, return empty signals
        return jsonify({'signals': signals_data})
    except Exception as e:
        logger.error(f"Signals API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices')
def api_prices():
    """Get live prices from OANDA"""
    try:
        prices_data = {}
        instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD', 'NZD_USD']
        
        # Always try direct OANDA fetch for live prices
        if account_manager:
            try:
                # Get any available OANDA client
                client = None
                for account_name, oanda_client in account_manager.accounts.items():
                    client = oanda_client
                    break
                
                if not client:
                    # Fallback to default client
                    from src.core.oanda_client import get_oanda_client
                    client = get_oanda_client()
                
                # Fetch live prices directly
                oanda_prices = client.get_current_prices(instruments)
                
                for instrument, oanda_price in oanda_prices.items():
                    if oanda_price:
                        prices_data[instrument] = {
                            'bid': oanda_price.bid,
                            'ask': oanda_price.ask,
                            'spread': oanda_price.spread,
                            'timestamp': oanda_price.timestamp.isoformat(),
                            'is_live': oanda_price.is_live
                        }
                        
            except Exception as e:
                logger.error(f"Direct OANDA price fetch failed: {e}")
        
        # If no prices from direct fetch, try data feed
        if not prices_data and data_feed:
            for instrument in instruments:
                try:
                    market_data = data_feed.get_market_data(instrument)
                    if instrument in market_data and market_data[instrument]:
                        price_data = market_data[instrument]
                        prices_data[instrument] = {
                            'bid': price_data.bid,
                            'ask': price_data.ask,
                            'spread': price_data.spread,
                            'timestamp': price_data.timestamp,
                            'is_live': price_data.is_live
                        }
                except Exception as e:
                    logger.error(f"Data feed price fetch failed for {instrument}: {e}")
        
        return jsonify({'prices': prices_data})
    except Exception as e:
        logger.error(f"Prices API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """Get live performance metrics from OANDA"""
    try:
        total_pl = 0
        total_balance = 0
        total_positions = 0
        
        if account_manager:
            # Calculate totals from all accounts
            for account_name, client in account_manager.accounts.items():
                try:
                    account_info = client.get_account_info()
                    if account_info:
                        total_pl += account_info.unrealized_pl + account_info.realized_pl
                        total_balance += account_info.balance
                        total_positions += account_info.open_position_count
                except Exception as e:
                    logger.error(f"Failed to get performance for {account_name}: {e}")
        
        pl_percentage = (total_pl / total_balance * 100) if total_balance > 0 else 0
        
        performance_data = {
            'total_pl': total_pl,
            'pl_percentage': pl_percentage,
            'portfolio_value': total_balance,
            'session_trades': total_positions,
            'london_ready': True,
            'auto_trading': system_state['auto_trading_enabled'],
            'last_update': system_state['last_update'].isoformat(),
            'data_source': 'OANDA Live' if account_manager else 'Offline'
        }
        return jsonify(performance_data)
    except Exception as e:
        logger.error(f"Performance API error: {e}")
        return jsonify({'error': str(e)}), 500

# Control API Endpoints
@app.route('/api/set-mode', methods=['POST'])
def api_set_mode():
    """Set trading mode"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'balanced')
        
        if mode in ['aggressive', 'balanced', 'relaxed']:
            system_state['current_mode'] = mode
            system_state['last_update'] = datetime.now()
            return jsonify({'success': True, 'mode': mode})
        else:
            return jsonify({'success': False, 'error': 'Invalid mode'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle-strategy', methods=['POST'])
def api_toggle_strategy():
    """Toggle strategy on/off"""
    try:
        data = request.get_json()
        strategy = data.get('strategy')
        enabled = data.get('enabled', False)
        
        if strategy in system_state['active_strategies']:
            system_state['active_strategies'][strategy] = enabled
            system_state['last_update'] = datetime.now()
            return jsonify({'success': True, 'strategy': strategy, 'enabled': enabled})
        else:
            return jsonify({'success': False, 'error': 'Invalid strategy'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """Emergency stop all trading"""
    try:
        system_state['kill_switches']['emergency_stop'] = True
        system_state['auto_trading_enabled'] = False
        system_state['last_update'] = datetime.now()
        return jsonify({'success': True, 'message': 'Emergency stop activated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pause-trading', methods=['POST'])
def api_pause_trading():
    """Pause trading"""
    try:
        system_state['kill_switches']['pause_trading'] = True
        system_state['last_update'] = datetime.now()
        return jsonify({'success': True, 'message': 'Trading paused'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/resume-trading', methods=['POST'])
def api_resume_trading():
    """Resume trading"""
    try:
        system_state['kill_switches']['pause_trading'] = False
        system_state['last_update'] = datetime.now()
        return jsonify({'success': True, 'message': 'Trading resumed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle-auto-trading', methods=['POST'])
def api_toggle_auto_trading():
    """Toggle auto trading"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        system_state['auto_trading_enabled'] = enabled
        system_state['last_update'] = datetime.now()
        return jsonify({'success': True, 'enabled': enabled})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-news-filters', methods=['POST'])
def api_update_news_filters():
    """Update news filters"""
    try:
        data = request.get_json()
        
        if 'high_impact_only' in data:
            system_state['news_filters']['high_impact_only'] = data['high_impact_only']
        
        system_state['last_update'] = datetime.now()
        return jsonify({'success': True, 'filters': system_state['news_filters']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Enhanced Trading System Dashboard with AI Assistant...")
    print("📊 Dashboard will be available at: http://localhost:5001")
    print("🤖 AI Assistant: Enabled")
    print("🎛️ Full Control Panel: Available")
    print("📰 News Filters: Active")
    print("🛑 Kill Switches: Ready")
    print("🎯 Strategy Switching: Enabled")
    print("📊 Mode Switching: Available")
    print("🇬🇧 London Session: Auto-detection enabled")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5005, debug=False)
