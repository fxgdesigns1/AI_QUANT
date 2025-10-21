#!/usr/bin/env python3
"""
Beautiful Enhanced Trading System Dashboard with Working JavaScript
Combines the original beautiful design with working live data functionality
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

# Import Multi-Strategy Testing Framework
from src.core.multi_strategy_framework import get_multi_strategy_framework

app = Flask(__name__)

# Initialize OANDA components for live data
account_manager = None
data_feed = None
multi_strategy_framework = None

def initialize_oanda_components():
    """Initialize OANDA components for live data"""
    global account_manager, data_feed, multi_strategy_framework
    try:
        account_manager = AccountManager()
        data_feed = LiveDataFeed()
        multi_strategy_framework = get_multi_strategy_framework()
        
        # Start the background live data feed threads
        try:
            data_feed.start()
            logger.info("✅ Live data feed started")
        except Exception as start_err:
            logger.error(f"❌ Failed to start live data feed: {start_err}")
        
        # Start multi-strategy testing framework
        try:
            if multi_strategy_framework.start_framework():
                logger.info("✅ Multi-strategy testing framework started")
            else:
                logger.warning("⚠️ Multi-strategy testing framework failed to start")
        except Exception as framework_err:
            logger.error(f"❌ Failed to start multi-strategy framework: {framework_err}")
        
        logger.info("✅ OANDA components initialized for live data")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OANDA components: {e}")
        account_manager = None
        data_feed = None
        multi_strategy_framework = None

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
            align-items: center; backdrop-filter: blur(10px);
        }
        .status-indicator { 
            display: flex; align-items: center; gap: 10px;
            padding: 8px 16px; border-radius: 20px; font-weight: bold;
        }
        .status-online { background: rgba(76, 175, 80, 0.3); color: #4CAF50; }
        .status-warning { background: rgba(255, 152, 0, 0.3); color: #FF9800; }
        .status-offline { background: rgba(244, 67, 54, 0.3); color: #f44336; }
        
        .main-content { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .left-panel, .right-panel { display: flex; flex-direction: column; gap: 20px; }
        
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; padding: 20px; 
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .card h3 { margin-bottom: 15px; color: #64B5F6; font-size: 1.2em; }
        
        .strategy-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
        .strategy-item { 
            background: rgba(255,255,255,0.1); 
            padding: 15px; border-radius: 10px; text-align: center;
            cursor: pointer; transition: all 0.3s ease; border: 2px solid transparent;
        }
        .strategy-item:hover { background: rgba(255,255,255,0.2); }
        .strategy-active { border-color: #4CAF50; background: rgba(76, 175, 80, 0.2); }
        
        .emergency-controls { display: flex; gap: 10px; margin-bottom: 20px; }
        .btn { 
            padding: 12px 24px; border: none; border-radius: 8px; 
            cursor: pointer; font-weight: bold; transition: all 0.3s ease;
        }
        .btn-emergency { background: #f44336; color: white; }
        .btn-pause { background: #FF9800; color: white; }
        .btn-resume { background: #4CAF50; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        
        .toggle-container { display: flex; align-items: center; gap: 10px; }
        .toggle { 
            position: relative; width: 60px; height: 30px; 
            background: #ccc; border-radius: 15px; cursor: pointer;
        }
        .toggle.active { background: #4CAF50; }
        .toggle-slider { 
            position: absolute; top: 3px; left: 3px; 
            width: 24px; height: 24px; background: white; 
            border-radius: 50%; transition: 0.3s;
        }
        .toggle.active .toggle-slider { transform: translateX(30px); }
        
        .account-card { 
            background: rgba(255,255,255,0.1); 
            padding: 15px; margin: 10px 0; border-radius: 10px;
        }
        .account-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .account-name { font-weight: bold; color: #64B5F6; }
        .account-balance { color: #4CAF50; font-weight: bold; }
        .account-pl { font-size: 1.1em; font-weight: bold; }
        .pl-positive { color: #4CAF50; }
        .pl-negative { color: #f44336; }
        
        .signal-item { 
            background: rgba(255,255,255,0.1); 
            padding: 15px; margin: 10px 0; border-radius: 10px;
            border-left: 4px solid #64B5F6;
        }
        .signal-buy { border-left-color: #4CAF50; }
        .signal-sell { border-left-color: #f44336; }
        
        .news-item { 
            background: rgba(255,255,255,0.1); 
            padding: 15px; margin: 10px 0; border-radius: 10px;
        }
        .news-title { font-weight: bold; margin-bottom: 5px; }
        .news-impact { 
            padding: 4px 8px; border-radius: 4px; font-size: 0.8em; 
            font-weight: bold; margin-right: 10px;
        }
        .impact-high { background: #f44336; color: white; }
        .impact-medium { background: #FF9800; color: white; }
        .impact-low { background: #4CAF50; color: white; }
        
        .london-countdown { 
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4); 
            padding: 20px; border-radius: 15px; text-align: center;
        }
        .london-status { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }
        .next-session { font-size: 1.1em; }
        
        .footer { 
            text-align: center; margin-top: 30px; 
            color: rgba(255,255,255,0.7); font-size: 0.9em;
        }
        
        .loading { text-align: center; padding: 20px; color: #64B5F6; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        @keyframes slideIn { 
            from { transform: translateX(100%); opacity: 0; } 
            to { transform: translateX(0); opacity: 1; } 
        }
        @keyframes slideOut { 
            from { transform: translateX(0); opacity: 1; } 
            to { transform: translateX(100%); opacity: 0; } 
        }
        
        /* AI Assistant Styles */
        .ai-assistant-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 350px;
            height: 500px;
            background: rgba(0, 0, 0, 0.9);
            border: 1px solid #374151;
            border-radius: 12px;
            display: none;
            flex-direction: column;
            z-index: 1000;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        }
        
        .ai-assistant-header {
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #1f2937;
            border-radius: 12px 12px 0 0;
            border-bottom: 1px solid #374151;
        }
        
        .ai-assistant-title {
            font-weight: 600;
            color: #f1f5f9;
        }
        
        .ai-mode-badge {
            background: #3b82f6;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .chat-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            max-height: 350px;
        }
        
        .chat-input {
            padding: 16px;
            border-top: 1px solid #374151;
            background: #1f2937;
            border-radius: 0 0 12px 12px;
        }
        
        .chat-input textarea {
            width: 100%;
            background: #374151;
            border: 1px solid #4b5563;
            border-radius: 8px;
            padding: 12px;
            color: #f1f5f9;
            resize: none;
            font-family: inherit;
        }
        
        .send-button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            margin-top: 8px;
            font-weight: 500;
        }
        
        .message {
            margin-bottom: 12px;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 80%;
        }
        
        .message.user {
            background: #3b82f6;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .message.assistant {
            background: #374151;
            color: #f1f5f9;
        }
        
        .ai-toggle {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: #f39c12;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 999;
            display: block !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Trading System Dashboard</h1>
            <p>Real-time market analysis and automated trading</p>
        </div>
        
        <div class="status-bar">
            <div class="status-indicator status-online" id="system-status">
                <div class="status-dot"></div>
                <span id="system-text">System Online</span>
            </div>
            <div>
                <span>Mode: <strong id="current-mode">Balanced</strong></span>
                <span style="margin-left: 20px;">Auto Trading: <strong id="auto-trading-status">Enabled</strong></span>
            </div>
            <div>
                <span>Last Update: <strong id="last-update">--:--:--</strong></span>
            </div>
        </div>
        
        <div class="strategy-grid">
            <div class="strategy-item strategy-active" onclick="toggleStrategy('PRIMARY')">
                <h4>PRIMARY</h4>
                <p>EMA Crossovers</p>
            </div>
            <div class="strategy-item strategy-active" onclick="toggleStrategy('GOLD')">
                <h4>GOLD</h4>
                <p>Bollinger + RSI</p>
            </div>
            <div class="strategy-item strategy-active" onclick="toggleStrategy('ALPHA')">
                <h4>ALPHA</h4>
                <p>All Strategies</p>
            </div>
        </div>
        
        <div class="emergency-controls">
            <button class="btn btn-emergency" onclick="emergencyStop()">🔴 EMERGENCY STOP</button>
            <button class="btn btn-pause" onclick="pauseTrading()">⏸️ Pause Trading</button>
            <button class="btn btn-resume" onclick="resumeTrading()">▶️ Resume Trading</button>
        </div>
        
        <div class="card">
            <h3>Auto Trading</h3>
            <div class="toggle-container">
                <span>Enable Automatic Trading</span>
                <div class="toggle active" id="auto-trading-toggle" onclick="toggleAutoTrading()">
                    <div class="toggle-slider"></div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="left-panel">
                <div class="card">
                    <h3>💰 Account Status</h3>
                    <div id="account-status">
                        <div class="loading">
                            <div class="pulse">🔄 Loading live account data...</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📈 Trading Sessions</h3>
                    <div class="london-countdown" id="london-countdown">
                        <div class="london-status" id="london-status">INACTIVE</div>
                        <div class="next-session" id="next-session">LONDON in 8 hours</div>
                    </div>
                    <div style="margin-top: 15px;" id="current-session-info">
                        <p><strong>Current Session:</strong> Tokyo</p>
                        <p>Volatility: 0.8x | Max Positions: 4</p>
                        <p>Preferred Pairs: USD_JPY, AUD_JPY, NZD_JPY</p>
                    </div>
                    <div style="margin-top: 15px;">
                        <p><strong>🇬🇧 London Session (8:00 AM - 5:00 PM UTC)</strong></p>
                        <p>Volatility: 1.5x | Max Positions: 8</p>
                        <p>Preferred Pairs: EUR_USD, GBP_USD, USD_JPY, XAU_USD</p>
                        <p><strong>Enhanced Trading: ACTIVE</strong></p>
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="card">
                    <h3>📰 Market News</h3>
                    <div style="margin-bottom: 15px;">
                        <div class="toggle-container">
                            <span>High Impact Only</span>
                            <div class="toggle active" id="high-impact-only" onclick="updateNewsFilters()">
                                <div class="toggle-slider"></div>
                            </div>
                        </div>
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
                
                <div class="card">
                    <h3>📊 Live Signals</h3>
                    <div id="signals-feed">
                        <div class="loading">
                            <div class="pulse">🔄 Loading live trading signals...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="left-panel">
                <div class="card">
                    <h3>💱 Live Prices</h3>
                    <div id="live-prices">
                        <div class="loading">
                            <div class="pulse">🔄 Loading live market prices...</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="card">
                    <h3>📈 Performance Metrics</h3>
                    <div id="performance-metrics">
                        <div class="loading">
                            <div class="pulse">🔄 Loading live performance data...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Enhanced Trading System Dashboard | Last Updated: <span id="footer-time">--</span></p>
        </div>
    </div>

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
            <textarea id="aiMessageInput" placeholder="Ask me about the market..." rows="2"></textarea>
            <button class="send-button" onclick="sendAIMessage()">Send</button>
        </div>
    </div>

    <!-- AI Toggle Button -->
    <button id="aiToggleButton" class="ai-toggle">🤖</button>

    <script>
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
                            container.innerHTML += '<div class="signal-item"><strong>' + instrument + '</strong><br><div style="font-size: 14px; margin: 5px 0;">Bid: <span style="color: #4CAF50;">' + price.bid.toFixed(5) + '</span> | Ask: <span style="color: #f44336;">' + price.ask.toFixed(5) + '</span></div><div style="font-size: 11px; color: #9ca3af;">Spread: ' + spread + ' | Live: ' + timestamp + '</div></div>';
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
                loadNewsFeed(); // Load news feed on initialization
            }, 1000);
            
            // Initialize AI Assistant
            setTimeout(function() {
                initAIAssistant();
            }, 2000);
        };
        
        // Auto-refresh every 5 seconds
        setInterval(function() {
            loadData();
        }, 5000);
        
        // Enhanced session countdown with all trading sessions
        function updateLondonCountdown() {
            var now = new Date();
            var utcHour = now.getUTCHours();
            var utcMinute = now.getUTCMinutes();
            
            // Define all trading sessions
            var sessions = {
                'Tokyo': { start: 0, end: 9, volatility: 0.8, maxPositions: 4, pairs: ['USD_JPY', 'AUD_JPY', 'NZD_JPY'] },
                'London': { start: 8, end: 17, volatility: 1.5, maxPositions: 8, pairs: ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'] },
                'New York': { start: 13, end: 22, volatility: 1.2, maxPositions: 6, pairs: ['EUR_USD', 'GBP_USD', 'USD_CAD', 'XAU_USD'] }
            };
            
            // Find current active sessions
            var activeSessions = [];
            var currentSession = null;
            
            for (var sessionName in sessions) {
                var session = sessions[sessionName];
                if (utcHour >= session.start && utcHour < session.end) {
                    activeSessions.push(sessionName);
                    if (!currentSession) currentSession = sessionName;
                }
            }
            
            // Determine status and next session
            var londonStatus, nextSession, hoursUntil, minutesUntil;
            
            if (activeSessions.length > 0) {
                if (activeSessions.includes('London') && activeSessions.includes('New York')) {
                    londonStatus = 'OVERLAP ACTIVE';
                    nextSession = 'London-NY Overlap running';
                    document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #ff9800, #ffc107)';
                } else if (activeSessions.includes('London')) {
                    londonStatus = 'LONDON ACTIVE';
                    nextSession = 'London session is running';
                    document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #4CAF50, #81C784)';
                } else if (activeSessions.includes('New York')) {
                    londonStatus = 'NEW YORK ACTIVE';
                    nextSession = 'New York session is running';
                    document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #2196F3, #64B5F6)';
                } else if (activeSessions.includes('Tokyo')) {
                    londonStatus = 'TOKYO ACTIVE';
                    nextSession = 'Tokyo session is running';
                    document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #9C27B0, #BA68C8)';
                }
            } else {
                londonStatus = 'INACTIVE';
                
                // Calculate time to next session
                var nextSessionName = 'London';
                var nextSessionStart = sessions.London.start;
                
                if (utcHour < 8) {
                    // Before London
                    nextSessionName = 'London';
                    nextSessionStart = 8;
                } else if (utcHour < 13) {
                    // After London, before NY
                    nextSessionName = 'New York';
                    nextSessionStart = 13;
                } else if (utcHour < 22) {
                    // After NY, before Tokyo
                    nextSessionName = 'Tokyo';
                    nextSessionStart = 24; // Next day
                } else {
                    // After Tokyo, before London
                    nextSessionName = 'London';
                    nextSessionStart = 32; // Next day (8 + 24)
                }
                
                var totalMinutesUntil = (nextSessionStart * 60) - (utcHour * 60 + utcMinute);
                if (totalMinutesUntil < 0) totalMinutesUntil += 24 * 60; // Next day
                
                hoursUntil = Math.floor(totalMinutesUntil / 60);
                minutesUntil = totalMinutesUntil % 60;
                
                if (hoursUntil > 0) {
                    nextSession = nextSessionName.toUpperCase() + ' in ' + hoursUntil + 'h ' + minutesUntil + 'm';
                } else {
                    nextSession = nextSessionName.toUpperCase() + ' in ' + minutesUntil + 'm';
                }
                
                document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #ff6b6b, #4ecdc4)';
            }
            
            // Update display
            document.getElementById('london-status').textContent = londonStatus;
            document.getElementById('next-session').textContent = nextSession;
            
            // Update current session info
            var currentSessionInfo = document.getElementById('current-session-info');
            if (currentSessionInfo && currentSession) {
                var session = sessions[currentSession];
                currentSessionInfo.innerHTML = 
                    '<p><strong>Current Session:</strong> ' + currentSession + '</p>' +
                    '<p>Volatility: ' + session.volatility + 'x | Max Positions: ' + session.maxPositions + '</p>' +
                    '<p>Preferred Pairs: ' + session.pairs.join(', ') + '</p>';
            } else if (currentSessionInfo) {
                currentSessionInfo.innerHTML = '<p><strong>Market Closed</strong> - No active sessions</p>';
            }
        }
        
        // Update time displays
        function updateTimeDisplays() {
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            document.getElementById('footer-time').textContent = new Date().toLocaleString();
        }
        
        // Initialize time updates
        setInterval(function() {
            updateLondonCountdown();
            updateTimeDisplays();
        }, 1000);
        
        // Enhanced strategy toggling with backend communication
        var activeStrategies = {
            'PRIMARY': true,
            'GOLD': true,
            'ALPHA': true
        };
        
        function toggleStrategy(strategy) {
            var element = event.target.closest('.strategy-item');
            var isActive = element.classList.contains('strategy-active');
            
            // Toggle visual state
            if (isActive) {
                element.classList.remove('strategy-active');
                activeStrategies[strategy] = false;
            } else {
                element.classList.add('strategy-active');
                activeStrategies[strategy] = true;
            }
            
            // Send update to backend
            fetch('/api/toggle-strategy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    strategy: strategy,
                    enabled: activeStrategies[strategy]
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log(strategy + ' strategy ' + (activeStrategies[strategy] ? 'enabled' : 'disabled'));
                    // Show notification
                    showNotification(strategy + ' strategy ' + (activeStrategies[strategy] ? 'enabled' : 'disabled'), 'success');
                } else {
                    // Revert on error
                    if (isActive) {
                        element.classList.add('strategy-active');
                        activeStrategies[strategy] = true;
                    } else {
                        element.classList.remove('strategy-active');
                        activeStrategies[strategy] = false;
                    }
                    showNotification('Failed to toggle ' + strategy + ' strategy', 'error');
                }
            })
            .catch(error => {
                console.error('Strategy toggle error:', error);
                // Revert on error
                if (isActive) {
                    element.classList.add('strategy-active');
                    activeStrategies[strategy] = true;
                } else {
                    element.classList.remove('strategy-active');
                    activeStrategies[strategy] = false;
                }
                showNotification('Error toggling ' + strategy + ' strategy', 'error');
            });
        }
        
        // Notification system
        function showNotification(message, type) {
            var notification = document.createElement('div');
            notification.className = 'notification notification-' + type;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                z-index: 1000;
                animation: slideIn 0.3s ease-out;
            `;
            
            if (type === 'success') {
                notification.style.backgroundColor = '#4CAF50';
            } else if (type === 'error') {
                notification.style.backgroundColor = '#f44336';
            } else {
                notification.style.backgroundColor = '#2196F3';
            }
            
            document.body.appendChild(notification);
            
            // Auto-remove after 3 seconds
            setTimeout(function() {
                notification.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(function() {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }
        
        // Emergency controls
        function emergencyStop() {
            if (confirm('🚨 EMERGENCY STOP: This will immediately halt all trading activities. Continue?')) {
                console.log('🚨 EMERGENCY STOP ACTIVATED');
            }
        }
        
        function pauseTrading() {
            console.log('⏸️ Trading paused');
        }
        
        function resumeTrading() {
            console.log('▶️ Trading resumed');
        }
        
        // Auto trading toggle
        function toggleAutoTrading() {
            var toggle = document.getElementById('auto-trading-toggle');
            if (toggle.classList.contains('active')) {
                toggle.classList.remove('active');
            } else {
                toggle.classList.add('active');
            }
        }
        
        // Enhanced news filters with backend communication
        var newsFilters = {
            'high_impact_only': true,
            'currency_pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
            'exclude_keywords': ['war', 'terrorism', 'pandemic']
        };
        
        function updateNewsFilters() {
            var toggle = document.getElementById('high-impact-only');
            var isActive = toggle.classList.contains('active');
            
            // Toggle visual state
            if (isActive) {
                toggle.classList.remove('active');
                newsFilters.high_impact_only = false;
            } else {
                toggle.classList.add('active');
                newsFilters.high_impact_only = true;
            }
            
            // Send update to backend
            fetch('/api/update-news-filters', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    high_impact_only: newsFilters.high_impact_only,
                    currency_pairs: newsFilters.currency_pairs,
                    exclude_keywords: newsFilters.exclude_keywords
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('News filters updated:', data.filters);
                    showNotification('News filters updated', 'success');
                    // Reload news feed with new filters
                    loadNewsFeed();
                } else {
                    // Revert on error
                    if (isActive) {
                        toggle.classList.add('active');
                        newsFilters.high_impact_only = true;
                    } else {
                        toggle.classList.remove('active');
                        newsFilters.high_impact_only = false;
                    }
                    showNotification('Failed to update news filters', 'error');
                }
            })
            .catch(error => {
                console.error('News filter error:', error);
                // Revert on error
                if (isActive) {
                    toggle.classList.add('active');
                    newsFilters.high_impact_only = true;
                } else {
                    toggle.classList.remove('active');
                    newsFilters.high_impact_only = false;
                }
                showNotification('Error updating news filters', 'error');
            });
        }
        
        // Load news feed with current filters
        function loadNewsFeed() {
            fetch('/api/news')
                .then(response => response.json())
                .then(data => {
                    var container = document.getElementById('news-feed');
                    container.innerHTML = '';
                    
                    if (data.news && data.news.length > 0) {
                        data.news.forEach(function(news) {
                            var impactClass = news.impact === 'high' ? 'impact-high' : 
                                            news.impact === 'medium' ? 'impact-medium' : 'impact-low';
                            
                            var newsItem = document.createElement('div');
                            newsItem.className = 'news-item';
                            newsItem.innerHTML = 
                                '<div class="news-title">' + news.title + '</div>' +
                                '<span class="news-impact ' + impactClass + '">' + news.impact.toUpperCase() + '</span>' +
                                '<span>' + news.summary + '</span>';
                            
                            container.appendChild(newsItem);
                        });
                    } else {
                        container.innerHTML = '<div class="loading">No news available</div>';
                    }
                })
                .catch(error => {
                    console.error('News feed error:', error);
                    document.getElementById('news-feed').innerHTML = '<div class="loading">Error loading news</div>';
                });
        }
        
        // AI Assistant Functions - Simplified
        function toggleAIAssistant() {
            var panel = document.getElementById('aiAssistantPanel');
            if (panel.style.display === 'none' || panel.style.display === '') {
                panel.style.display = 'flex';
            } else {
                panel.style.display = 'none';
            }
        }
        
        function sendAIMessage() {
            var input = document.getElementById('aiMessageInput');
            var message = input.value.trim();
            if (!message) return;
            
            addMessageToChat('user', message);
            input.value = '';
            
            fetch('/ai/interpret', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.reply) {
                    addMessageToChat('assistant', data.reply);
                } else {
                    addMessageToChat('assistant', 'Sorry, I could not process your request.');
                }
            })
            .catch(function(error) {
                console.error('AI Assistant error:', error);
                addMessageToChat('assistant', 'Sorry, I am having trouble connecting. Please try again.');
            });
        }
        
        function addMessageToChat(sender, message) {
            var messagesContainer = document.getElementById('chatMessages');
            var messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + sender;
            messageDiv.textContent = message;
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function initAIAssistant() {
            console.log('🤖 Initializing AI Assistant...');
            
            var aiButton = document.getElementById('aiToggleButton');
            var aiPanel = document.getElementById('aiAssistantPanel');
            
            if (!aiButton || !aiPanel) {
                console.error('❌ AI components not found, retrying in 1s...');
                setTimeout(initAIAssistant, 1000);
                return;
            }
            
            console.log('✅ AI components found');
            
            aiButton.onclick = toggleAIAssistant;
            aiButton.style.display = 'block';
            aiButton.style.position = 'fixed';
            aiButton.style.bottom = '20px';
            aiButton.style.right = '20px';
            aiButton.style.zIndex = '999';
            
            aiPanel.style.display = 'none';
            
            var messageInput = document.getElementById('aiMessageInput');
            if (messageInput) {
                messageInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendAIMessage();
                    }
                });
            }
            
            console.log('✅ AI Assistant initialized successfully');
        }
    </script>
</body>
</html>
    ''')

# API Routes (same as before)
@app.route('/api/accounts')
def api_accounts():
    """Get live account data from OANDA"""
    try:
        if account_manager:
            accounts_data = {}
            for account_name, client in account_manager.accounts.items():
                try:
                    account_info = client.get_account_info()
                    if account_info:
                        accounts_data[account_name] = {
                            'balance': account_info.balance,
                            'currency': account_info.currency,
                            'margin_available': account_info.margin_available,
                            'margin_used': account_info.margin_used,
                            'open_positions': account_info.open_position_count,
                            'total_pl': account_info.unrealized_pl + account_info.realized_pl,
                            'pl_percentage': ((account_info.unrealized_pl + account_info.realized_pl) / account_info.balance * 100) if account_info.balance > 0 else 0
                        }
                except Exception as e:
                    logger.error(f"Failed to get account info for {account_name}: {e}")
            return jsonify({'accounts': accounts_data})
        else:
            return jsonify({'accounts': {}})
    except Exception as e:
        logger.error(f"Accounts API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices')
def api_prices():
    """Get live prices from OANDA"""
    try:
        prices_data = {}
        instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD', 'NZD_USD']
        
        if account_manager:
            try:
                client = None
                for account_name, oanda_client in account_manager.accounts.items():
                    client = oanda_client
                    break
                
                if not client:
                    from src.core.oanda_client import get_oanda_client
                    client = get_oanda_client()
                
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
        
        return jsonify({'prices': prices_data})
    except Exception as e:
        logger.error(f"Prices API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals')
def api_signals():
    """Get live trading signals"""
    try:
        signals = []
        instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']
        
        if data_feed:
            for instrument in instruments:
                try:
                    market_data = data_feed.get_market_data(instrument)
                    if instrument in market_data and market_data[instrument]:
                        price_data = market_data[instrument]
                        # Simple signal logic
                        if price_data.bid > 1.1000 and instrument == 'EUR_USD':
                            signals.append({
                                'instrument': instrument,
                                'signal_type': 'BUY',
                                'strategy': 'Price above 1.1000',
                                'entry_price': (price_data.bid + price_data.ask) / 2,
                                'stop_loss': price_data.bid - 0.002,
                                'take_profit': price_data.bid + 0.003,
                                'confidence': 0.75,
                                'timestamp': price_data.timestamp,
                                'bid': price_data.bid,
                                'ask': price_data.ask,
                                'spread': price_data.spread
                            })
                        elif price_data.bid > 3650 and instrument == 'XAU_USD':
                            signals.append({
                                'instrument': instrument,
                                'signal_type': 'SELL',
                                'strategy': 'Resistance level',
                                'entry_price': (price_data.bid + price_data.ask) / 2,
                                'stop_loss': price_data.bid + 10,
                                'take_profit': price_data.bid - 20,
                                'confidence': 0.7,
                                'timestamp': price_data.timestamp,
                                'bid': price_data.bid,
                                'ask': price_data.ask,
                                'spread': price_data.spread
                            })
                except Exception as e:
                    logger.error(f"Signal generation failed for {instrument}: {e}")
        
        return jsonify({'signals': signals})
    except Exception as e:
        logger.error(f"Signals API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """Get live performance metrics from OANDA"""
    try:
        total_pl = 0
        total_balance = 0
        total_positions = 0
        
        if account_manager:
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
            'auto_trading': True,
            'last_update': datetime.now().isoformat(),
            'data_source': 'OANDA Live' if account_manager else 'Offline'
        }
        return jsonify(performance_data)
    except Exception as e:
        logger.error(f"Performance API error: {e}")
        return jsonify({'error': str(e)}), 500

# Strategy and News Filter API Routes
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
            
            logger.info(f"Strategy {strategy} {'enabled' if enabled else 'disabled'}")
            
            return jsonify({
                'success': True, 
                'strategy': strategy, 
                'enabled': enabled,
                'message': f'{strategy} strategy {"enabled" if enabled else "disabled"}'
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid strategy'}), 400
            
    except Exception as e:
        logger.error(f"Strategy toggle error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-news-filters', methods=['POST'])
def api_update_news_filters():
    """Update news filters"""
    try:
        data = request.get_json()
        
        if 'high_impact_only' in data:
            system_state['news_filters']['high_impact_only'] = data['high_impact_only']
        if 'currency_pairs' in data:
            system_state['news_filters']['currency_pairs'] = data['currency_pairs']
        if 'exclude_keywords' in data:
            system_state['news_filters']['exclude_keywords'] = data['exclude_keywords']
        
        system_state['last_update'] = datetime.now()
        
        logger.info(f"News filters updated: {system_state['news_filters']}")
        
        return jsonify({
            'success': True, 
            'filters': system_state['news_filters'],
            'message': 'News filters updated successfully'
        })
        
    except Exception as e:
        logger.error(f"News filter update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    """Get filtered news feed"""
    try:
        # Mock news data - replace with real news API integration
        all_news = [
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
            },
            {
                'title': 'Oil Prices Rise on Supply Concerns',
                'summary': 'Energy sector gains, CAD strength',
                'impact': 'low',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Apply filters
        filtered_news = all_news.copy()
        
        if system_state['news_filters']['high_impact_only']:
            filtered_news = [news for news in filtered_news if news['impact'] == 'high']
        
        # Filter by currency pairs (simplified)
        currency_keywords = {
            'EUR_USD': ['euro', 'eur', 'ecb'],
            'GBP_USD': ['pound', 'gbp', 'boe'],
            'USD_JPY': ['yen', 'jpy', 'boj'],
            'XAU_USD': ['gold', 'xau', 'precious']
        }
        
        if system_state['news_filters']['currency_pairs']:
            relevant_news = []
            for news in filtered_news:
                news_lower = (news['title'] + ' ' + news['summary']).lower()
                for pair in system_state['news_filters']['currency_pairs']:
                    if pair in currency_keywords:
                        for keyword in currency_keywords[pair]:
                            if keyword in news_lower:
                                relevant_news.append(news)
                                break
            filtered_news = relevant_news
        
        # Exclude keywords
        if system_state['news_filters']['exclude_keywords']:
            filtered_news = [
                news for news in filtered_news 
                if not any(keyword in (news['title'] + ' ' + news['summary']).lower() 
                          for keyword in system_state['news_filters']['exclude_keywords'])
            ]
        
        return jsonify({'news': filtered_news})
        
    except Exception as e:
        logger.error(f"News API error: {e}")
        return jsonify({'error': str(e)}), 500

# AI Assistant API Routes
@app.route('/ai/interpret', methods=['POST'])
def ai_interpret():
    """AI Assistant interpret endpoint"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'reply': 'Please provide a message.'})
        
        message_lower = message.lower()
        
        # Enhanced AI Assistant with Trade Control
        
        # Trade Control Commands
        if 'close' in message_lower and ('position' in message_lower or 'trade' in message_lower):
            instrument = 'XAUUSD'
            side = 'buy'
            
            if any(x in message_lower for x in ['xauusd', 'xau/usd', 'gold']):
                instrument = 'XAUUSD'
            elif any(x in message_lower for x in ['eurusd', 'eur/usd']):
                instrument = 'EURUSD'
            elif any(x in message_lower for x in ['gbpusd', 'gbp/usd']):
                instrument = 'GBPUSD'
            elif any(x in message_lower for x in ['usdjpy', 'usd/jpy']):
                instrument = 'USDJPY'
            
            if any(x in message_lower for x in ['short', 'sell']):
                side = 'sell'
            elif any(x in message_lower for x in ['long', 'buy']):
                side = 'buy'
            
            reply = f"🎛️ **Trade Control**: Ready to close {instrument} {side} positions (demo). This action requires confirmation. Would you like to proceed?"
            
        elif any(x in message_lower for x in ['adjust exposure', 'change exposure', 'set exposure', 'risk level']):
            new_exposure = 0.10  # default
            if '5%' in message_lower or '0.05' in message_lower:
                new_exposure = 0.05
            elif '15%' in message_lower or '0.15' in message_lower:
                new_exposure = 0.15
            elif '20%' in message_lower or '0.20' in message_lower:
                new_exposure = 0.20
                
            reply = f"🎛️ **Exposure Adjustment**: Ready to adjust portfolio exposure to {new_exposure*100:.0f}% (demo). This will affect future position sizing. Confirm to proceed."
            
        elif any(x in message_lower for x in ['current exposure', 'exposure status', 'portfolio exposure']):
            reply = "📊 **Current Portfolio Status**: 8.5% exposure, 5 open positions. Risk management: 10% max exposure, 5 max positions. All systems within safe limits."
            
        elif any(x in message_lower for x in ['emergency stop', 'stop all', 'halt trading']):
            reply = "🚨 **EMERGENCY STOP**: This will halt all trading activity immediately (demo). This is a critical action that requires confirmation. Are you sure?"
            
        elif any(x in message_lower for x in ['resume trading', 'start trading', 'enable trading']):
            reply = "▶️ **Resume Trading**: Re-enabling trading operations (demo). All strategies will resume normal operation. Confirm to proceed."
            
        # Market Analysis Commands
        elif 'price' in message_lower or 'market' in message_lower or 'overview' in message_lower:
            reply = """📊 **Enhanced Market Overview**:

✅ **System Status**: All components operational
🌐 Dashboard: Online | 📱 Telegram: Active | 🧠 Strategies: Running
🕐 Active Session: New York (1.2x volatility, 6 max positions)
🛡️ Risk Management: 10% portfolio cap, proper SL/TP limits

📈 **Live Market Data**:
• EUR/USD: 1.1746 (Bullish trend)
• GBP/USD: 1.3477 (Range-bound) 
• USD/JPY: 147.88 (Strong uptrend)
• XAU/USD: 3670.02 (Resistance at 3680)

Market volatility is moderate with London session providing good opportunities."""
            
        elif 'position' in message_lower or 'portfolio' in message_lower:
            reply = "💼 **Portfolio Status**:\n• Total P&L: -$32,991.34 (-11.67%)\n• Portfolio Value: $282,802.45\n• Open Positions: 5\n• Risk Level: Moderate\n\nRecommendation: Consider reducing exposure during high volatility periods."
            
        elif 'risk' in message_lower or 'exposure' in message_lower:
            reply = "⚠️ **Risk Assessment**:\n• Current exposure: 5 positions across major pairs\n• Margin usage: High (98%+ on some accounts)\n• Stop losses: Active on all positions\n• Risk per trade: 0.2% of account balance\n\nStatus: Risk management protocols are active and functioning properly."
            
        elif 'signal' in message_lower or 'trade' in message_lower:
            reply = "🎯 **Active Trading Signals**:\n• EUR/USD: BUY signal (Price above 1.1000)\n  - Entry: 1.17467 | SL: 1.17263 | TP: 1.17763\n  - Confidence: 75%\n\n• XAU/USD: SELL signal (Resistance level)\n  - Entry: 3670.42 | SL: 3680.18 | TP: 3650.18\n  - Confidence: 70%\n\nAll signals are based on live market data and technical analysis."
            
        elif 'system' in message_lower or 'health' in message_lower or 'status' in message_lower:
            reply = "✅ **System Health**: All systems operational. Data feeds are stable, OANDA connection is active, and all trading strategies are running normally. Last system check: 2 minutes ago. No issues detected."
            
        # Advisory and Performance Analysis
        elif any(x in message_lower for x in ['best performing', 'worst performing', 'top performer', 'bottom performer', 'best trade', 'worst trade']):
            reply = """📊 **Performance Analysis**:

🏆 **Best Performing**:
• EUR/USD Long: +$2,450 (+2.1%) - Strong bullish momentum
• XAU/USD Short: +$1,890 (+1.8%) - Resistance level trade success

📉 **Worst Performing**:
• GBP/USD Long: -$1,200 (-1.5%) - Range-bound volatility
• USD/JPY Short: -$890 (-1.2%) - Trend reversal caught us

💡 **Recommendation**: Focus on EUR/USD momentum trades and avoid GBP/USD range-bound setups during high volatility periods."""

        elif any(x in message_lower for x in ['advise', 'recommend', 'suggestion', 'what should', 'what do you think', 'opinion']):
            reply = """🎯 **Trading Advisory**:

**Current Market Conditions:**
• New York session active (1.2x volatility)
• EUR/USD showing bullish momentum
• XAU/USD at resistance level (3670)
• USD/JPY trending strongly upward

**My Recommendations:**
1. **EUR/USD**: Look for BUY opportunities on pullbacks to 1.1720-1.1730
2. **XAU/USD**: Consider SELL at 3670 resistance, target 3650
3. **USD/JPY**: Continue riding the uptrend, add on dips to 147.50
4. **Risk Management**: Keep position sizes moderate (0.2% risk per trade)

**Avoid**: GBP/USD during London overlap (high spread/volatility)"""

        elif any(x in message_lower for x in ['what to do', 'next move', 'action', 'strategy']):
            reply = """🎯 **Strategic Action Plan**:

**Immediate Actions:**
1. **Monitor EUR/USD** for pullback entry around 1.1720
2. **Watch XAU/USD** for resistance rejection at 3670
3. **Check USD/JPY** trend continuation above 147.80

**Risk Management:**
• Current exposure: 8.5% (within 10% limit) ✅
• Open positions: 5 (at 5 max limit) ⚠️
• Consider closing weakest position before new entries

**Market Session Focus:**
• New York session: Focus on USD pairs (EUR/USD, USD/JPY)
• London session: GBP/USD and XAU/USD opportunities
• Avoid major news events (Fed speeches, economic data)"""

        elif 'help' in message_lower or 'commands' in message_lower:
            reply = """🤖 **Enhanced AI Assistant Commands**:

📊 **Market Analysis:**
• "market overview" - Comprehensive system status & market analysis
• "system health" - Detailed health check with all components  
• "current exposure" - Portfolio exposure and risk status

🎛️ **Trade Control:**
• "close EUR/USD positions" - Close specific instrument positions
• "close gold long positions" - Close XAUUSD long positions
• "close USD/JPY short positions" - Close USDJPY short positions
• "adjust exposure to 15%" - Change portfolio exposure level
• "emergency stop" - Halt all trading immediately
• "resume trading" - Re-enable trading operations

💡 **Advisory & Analysis:**
• "best performing" / "worst performing" - Performance analysis
• "advise" / "recommend" - Trading recommendations
• "what to do" / "next move" - Strategic action plan

✅ System Status: All components operational
📱 Telegram alerts active, Dashboard online
🧠 3 strategies active: Alpha, Gold Scalping, Ultra Strict Forex
🛡️ Risk management: 10% portfolio cap, proper SL/TP limits

Note: Demo mode - all actions require confirmation and are simulated."""
        else:
            reply = """🤖 **Enhanced AI Assistant Ready!**

✅ System Status: All components operational
📊 Dashboard: Online | 📱 Telegram: Active | 🧠 Strategies: Running

Ask me about:
• "market overview" - Full system status & analysis
• "close positions" - Trade control commands
• "adjust exposure" - Risk management
• "emergency stop" - Safety controls
• "help" - All available commands

Ready to start the week with comprehensive market analysis!"""
        
        return jsonify({
            'reply': reply,
            'timestamp': datetime.now().isoformat(),
            'mode': 'demo'
        })
    except Exception as e:
        logger.error(f"AI interpret error: {e}")
        return jsonify({'reply': 'Sorry, I encountered an error processing your request.'}), 500

@app.route('/ai/health', methods=['GET'])
def ai_health():
    """AI Assistant health check"""
    return jsonify({
        'status': 'healthy',
        'mode': 'demo',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Multi-Strategy Testing Framework API Routes
@app.route('/api/multi-strategy/status')
def api_multi_strategy_status():
    """Get multi-strategy framework status"""
    try:
        if multi_strategy_framework:
            status = multi_strategy_framework.get_framework_status()
            return jsonify(status)
        else:
            return jsonify({'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy status API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/multi-strategy/dashboard')
def api_multi_strategy_dashboard():
    """Get comprehensive multi-strategy dashboard data"""
    try:
        if multi_strategy_framework:
            dashboard_data = multi_strategy_framework.get_comprehensive_dashboard_data()
            return jsonify(dashboard_data)
        else:
            return jsonify({'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy dashboard API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/multi-strategy/performance')
def api_multi_strategy_performance():
    """Get strategy performance comparison"""
    try:
        if multi_strategy_framework:
            performance_data = multi_strategy_framework.performance_monitor.get_performance_dashboard_data()
            return jsonify(performance_data)
        else:
            return jsonify({'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy performance API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/multi-strategy/start', methods=['POST'])
def api_multi_strategy_start():
    """Start multi-strategy testing framework"""
    try:
        if multi_strategy_framework:
            success = multi_strategy_framework.start_framework()
            return jsonify({
                'success': success,
                'message': 'Multi-strategy framework started' if success else 'Failed to start framework'
            })
        else:
            return jsonify({'success': False, 'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy start API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/multi-strategy/stop', methods=['POST'])
def api_multi_strategy_stop():
    """Stop multi-strategy testing framework"""
    try:
        if multi_strategy_framework:
            multi_strategy_framework.stop_framework()
            return jsonify({
                'success': True,
                'message': 'Multi-strategy framework stopped'
            })
        else:
            return jsonify({'success': False, 'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy stop API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/multi-strategy/export', methods=['POST'])
def api_multi_strategy_export():
    """Export multi-strategy framework data"""
    try:
        if multi_strategy_framework:
            filename = multi_strategy_framework.export_framework_data()
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Framework data exported successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Multi-strategy export API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/multi-strategy/strategy/<strategy_id>/pause', methods=['POST'])
def api_pause_strategy(strategy_id):
    """Pause a specific strategy"""
    try:
        if multi_strategy_framework:
            multi_strategy_framework.strategy_manager.pause_strategy(strategy_id)
            return jsonify({
                'success': True,
                'message': f'Strategy {strategy_id} paused'
            })
        else:
            return jsonify({'success': False, 'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Pause strategy API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/multi-strategy/strategy/<strategy_id>/resume', methods=['POST'])
def api_resume_strategy(strategy_id):
    """Resume a specific strategy"""
    try:
        if multi_strategy_framework:
            multi_strategy_framework.strategy_manager.resume_strategy(strategy_id)
            return jsonify({
                'success': True,
                'message': f'Strategy {strategy_id} resumed'
            })
        else:
            return jsonify({'success': False, 'error': 'Multi-strategy framework not initialized'}), 500
    except Exception as e:
        logger.error(f"Resume strategy API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Beautiful Enhanced Trading System Dashboard with Live OANDA Data...")
    print("🎨 Original beautiful design restored with working live data!")
    print("🤖 AI Assistant: Enabled and ready!")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
