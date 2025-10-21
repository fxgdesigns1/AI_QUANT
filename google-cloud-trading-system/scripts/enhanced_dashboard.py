#!/usr/bin/env python3
"""
Enhanced Trading System Dashboard with Full AI Agent Integration
Includes: Override controls, kill switches, strategy switching, mode switching, news filters
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.adaptive_integration import AdaptiveAccountManager
from src.core.telegram_notifier import TelegramNotifier
from src.dashboard.ai_assistant_api import register_ai_assistant

app = Flask(__name__)
app.config['SECRET_KEY'] = 'enhanced_trading_dashboard_2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Global system state
manager = None
system_state = {
    'auto_trading_enabled': True,
    'current_mode': 'balanced',  # aggressive, balanced, relaxed
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

# AI Assistant Integration
ai_enabled = True

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Trading System Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
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
        
        .ai-chat { 
            height: 400px; overflow-y: auto; 
            background: rgba(0,0,0,0.3); padding: 15px; 
            border-radius: 10px; margin-bottom: 15px;
        }
        .ai-message { 
            margin-bottom: 10px; padding: 10px; 
            border-radius: 5px; background: rgba(255,255,255,0.1);
        }
        .ai-user { background: rgba(33, 150, 243, 0.3); }
        .ai-assistant { background: rgba(76, 175, 80, 0.3); }
        
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Trading System Dashboard</h1>
            <p>AI-Powered Adaptive Trading with Full Control</p>
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
                <strong>Last Update:</strong> <span id="last-update">{{ moment().format('HH:mm:ss') }}</span>
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
                    <div class="account-card">
                        <div class="account-header">
                            <span class="account-name">PRIMARY</span>
                            <span class="account-balance">$99,639.15</span>
                        </div>
                        <div class="account-pl pl-negative">-$360.85 (-0.36%)</div>
                        <div>Positions: 9 | Margin: 2.1%</div>
                    </div>
                    <div class="account-card">
                        <div class="account-header">
                            <span class="account-name">GOLD</span>
                            <span class="account-balance">$100,381.59</span>
                        </div>
                        <div class="account-pl pl-positive">+$381.59 (+0.38%)</div>
                        <div>Positions: 1 | Margin: 0.8%</div>
                    </div>
                    <div class="account-card">
                        <div class="account-header">
                            <span class="account-name">ALPHA</span>
                            <span class="account-balance">$100,139.61</span>
                        </div>
                        <div class="account-pl pl-positive">+$139.61 (+0.14%)</div>
                        <div>Positions: 6 | Margin: 1.5%</div>
                    </div>
                </div>
            </div>
            
            <!-- AI Assistant -->
            <div class="card">
                <h3>🤖 AI Assistant</h3>
                <div class="ai-chat" id="ai-chat">
                    <div class="ai-message ai-assistant">
                        <strong>AI:</strong> System initialized. Ready to assist with trading decisions and market analysis.
                    </div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="ai-input" placeholder="Ask me anything about the market..." 
                           style="flex: 1; padding: 10px; border: none; border-radius: 5px; background: rgba(255,255,255,0.1); color: white;">
                    <button class="btn btn-primary" onclick="sendAIMessage()">Send</button>
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
                    <div class="signal-item signal-buy">
                        <strong>EUR_USD BUY</strong> - EMA Crossover<br>
                        <small>Entry: 1.10245 | SL: 1.10025 | TP: 1.10545</small>
                    </div>
                    <div class="signal-item signal-sell">
                        <strong>XAU_USD SELL</strong> - RSI Overbought<br>
                        <small>Entry: 2654.50 | SL: 2660.00 | TP: 2640.00</small>
                    </div>
                </div>
            </div>
            
            <!-- System Performance -->
            <div class="card">
                <h3>📈 Performance Metrics</h3>
                <div id="performance-metrics">
                    <div style="margin-bottom: 10px;">
                        <strong>Total P&L:</strong> <span class="pl-positive">+$160.35 (+0.16%)</span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Win Rate:</strong> 68.5% (24/35 trades)
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Avg Risk/Reward:</strong> 1:2.3
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Max Drawdown:</strong> -2.1%
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Sharpe Ratio:</strong> 1.42
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🚀 Enhanced Trading System | AI-Powered | Real-time Monitoring | Full Control</p>
            <p>Last Updated: <span id="footer-time">{{ moment().format('YYYY-MM-DD HH:mm:ss') }}</span></p>
        </div>
    </div>

    <script>
        // Socket.IO connection
        const socket = io();
        
        // Global state
        let currentMode = 'balanced';
        let autoTradingEnabled = true;
        let activeStrategies = {PRIMARY: true, GOLD: true, ALPHA: true};
        let killSwitches = {emergency_stop: false, pause_trading: false, disable_news: false};
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            updateStatus();
            loadAccountStatus();
            loadNewsFeed();
            loadSignals();
            startRealTimeUpdates();
        });
        
        // Real-time updates
        function startRealTimeUpdates() {
            setInterval(() => {
                updateStatus();
                loadAccountStatus();
                loadSignals();
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                document.getElementById('footer-time').textContent = new Date().toLocaleString();
            }, 5000);
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
                        
                        container.innerHTML += `
                            <div class="account-card">
                                <div class="account-header">
                                    <span class="account-name">${name}</span>
                                    <span class="account-balance">$${account.balance.toLocaleString()}</span>
                                </div>
                                <div class="account-pl ${plClass}">${plSign}$${account.total_pl.toFixed(2)} (${plSign}${account.pl_percentage.toFixed(2)}%)</div>
                                <div>Positions: ${account.open_positions} | Margin: ${account.margin_used.toFixed(1)}%</div>
                            </div>
                        `;
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
                        
                        container.innerHTML += `
                            <div class="news-item">
                                <div class="news-title">${news.title}</div>
                                <span class="news-impact ${impactClass}">${news.impact.toUpperCase()}</span>
                                <span>${news.summary}</span>
                            </div>
                        `;
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
                    
                    (data.signals || []).forEach(signal => {
                        const signalClass = signal.signal_type === 'BUY' ? 'signal-buy' : 'signal-sell';
                        
                        container.innerHTML += `
                            <div class="signal-item ${signalClass}">
                                <strong>${signal.instrument} ${signal.signal_type}</strong> - ${signal.strategy}<br>
                                <small>Entry: ${signal.entry_price} | SL: ${signal.stop_loss} | TP: ${signal.take_profit}</small>
                            </div>
                        `;
                    });
                })
                .catch(error => console.error('Signals error:', error));
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
                    addAIMessage(`Mode changed to ${mode.toUpperCase()}`);
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
                    addAIMessage(`${strategy} strategy ${activeStrategies[strategy] ? 'enabled' : 'disabled'}`);
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
                            addAIMessage('🚨 EMERGENCY STOP ACTIVATED - All trading halted');
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
                        addAIMessage('⏸️ Trading paused');
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
                        addAIMessage('▶️ Trading resumed');
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
                    addAIMessage(`Auto trading ${autoTradingEnabled ? 'enabled' : 'disabled'}`);
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
        
        // AI Assistant
        function sendAIMessage() {
            const input = document.getElementById('ai-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addAIMessage(message, 'user');
            input.value = '';
            
            // Send to AI
            fetch('/ai/interpret', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message, session_id: 'dashboard'})
            })
            .then(response => response.json())
            .then(data => {
                addAIMessage(data.reply, 'assistant');
                
                if (data.requires_confirmation) {
                    if (confirm(`AI wants to execute: ${data.preview.summary}\\n\\nConfirm?`)) {
                        confirmAIAction(data.confirmation_id);
                    }
                }
            })
            .catch(error => {
                addAIMessage('Error: ' + error.message, 'assistant');
            });
        }
        
        function addAIMessage(message, sender = 'assistant') {
            const chat = document.getElementById('ai-chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = `ai-message ai-${sender}`;
            messageDiv.innerHTML = `<strong>${sender === 'user' ? 'You' : 'AI'}:</strong> ${message}`;
            chat.appendChild(messageDiv);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function confirmAIAction(confirmationId) {
            fetch('/ai/confirm', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({confirmation_id: confirmationId, confirm: true})
            })
            .then(response => response.json())
            .then(data => {
                addAIMessage(`Action ${data.status}: ${data.result.note}`, 'assistant');
            })
            .catch(error => {
                addAIMessage('Confirmation error: ' + error.message, 'assistant');
            });
        }
        
        // Enter key for AI input
        document.getElementById('ai-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendAIMessage();
            }
        });
        
        // Socket.IO events
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('system_update', function(data) {
            console.log('System update:', data);
            updateStatus();
        });
        
        socket.on('new_signal', function(data) {
            console.log('New signal:', data);
            loadSignals();
            addAIMessage(`New ${data.signal_type} signal for ${data.instrument}`, 'assistant');
        });
        
        socket.on('trade_executed', function(data) {
            console.log('Trade executed:', data);
            addAIMessage(`Trade executed: ${data.instrument} ${data.side} ${data.units} units`, 'assistant');
        });
    </script>
</body>
</html>
    ''')

# API Endpoints
@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        if manager:
            system_status = manager.get_adaptive_system_status()
            return jsonify({
                'system_online': True,
                'current_mode': system_state['current_mode'],
                'auto_trading_enabled': system_state['auto_trading_enabled'],
                'kill_switches': system_state['kill_switches'],
                'active_strategies': system_state['active_strategies'],
                'last_update': system_state['last_update'].isoformat(),
                'adaptive_status': system_status
            })
        else:
            return jsonify({
                'system_online': False,
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
    """Get account status"""
    try:
        if manager:
            account_status = manager.get_account_status()
            return jsonify({'accounts': account_status})
        else:
            return jsonify({'accounts': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news')
def api_news():
    """Get filtered news feed"""
    try:
        # Mock news data - replace with real news API integration
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
    """Get current trading signals"""
    try:
        # Mock signals data - replace with real signal detection
        signals_data = [
            {
                'instrument': 'EUR_USD',
                'signal_type': 'BUY',
                'strategy': 'EMA Crossover',
                'entry_price': 1.10245,
                'stop_loss': 1.10025,
                'take_profit': 1.10545,
                'confidence': 0.85,
                'timestamp': datetime.now().isoformat()
            },
            {
                'instrument': 'XAU_USD',
                'signal_type': 'SELL',
                'strategy': 'RSI Overbought',
                'entry_price': 2654.50,
                'stop_loss': 2660.00,
                'take_profit': 2640.00,
                'confidence': 0.72,
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        return jsonify({'signals': signals_data})
    except Exception as e:
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
            
            # Update adaptive system if available
            if manager and hasattr(manager, 'set_trading_mode'):
                manager.set_trading_mode(mode)
            
            # Emit update
            socketio.emit('system_update', {'mode': mode})
            
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
            
            # Update adaptive system if available
            if manager and hasattr(manager, 'toggle_strategy'):
                manager.toggle_strategy(strategy, enabled)
            
            # Emit update
            socketio.emit('system_update', {'strategy': strategy, 'enabled': enabled})
            
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
        
        # Stop adaptive system if available
        if manager and hasattr(manager, 'emergency_stop'):
            manager.emergency_stop()
        
        # Emit update
        socketio.emit('system_update', {'emergency_stop': True})
        
        return jsonify({'success': True, 'message': 'Emergency stop activated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pause-trading', methods=['POST'])
def api_pause_trading():
    """Pause trading"""
    try:
        system_state['kill_switches']['pause_trading'] = True
        system_state['last_update'] = datetime.now()
        
        # Pause adaptive system if available
        if manager and hasattr(manager, 'pause_trading'):
            manager.pause_trading()
        
        # Emit update
        socketio.emit('system_update', {'pause_trading': True})
        
        return jsonify({'success': True, 'message': 'Trading paused'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/resume-trading', methods=['POST'])
def api_resume_trading():
    """Resume trading"""
    try:
        system_state['kill_switches']['pause_trading'] = False
        system_state['last_update'] = datetime.now()
        
        # Resume adaptive system if available
        if manager and hasattr(manager, 'resume_trading'):
            manager.resume_trading()
        
        # Emit update
        socketio.emit('system_update', {'resume_trading': True})
        
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
        
        # Update adaptive system if available
        if manager and hasattr(manager, 'toggle_auto_trading'):
            manager.toggle_auto_trading(enabled)
        
        # Emit update
        socketio.emit('system_update', {'auto_trading_enabled': enabled})
        
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

def initialize_system():
    """Initialize the trading system"""
    global manager
    
    try:
        print("🔧 Initializing Enhanced Trading System...")
        manager = AdaptiveAccountManager()
        print("✅ Enhanced Trading System initialized")
        
        # Configure AI Assistant
        if ai_enabled:
            app.config['ACCOUNT_MANAGER'] = manager
            app.config['DATA_FEED'] = getattr(manager, 'data_feed', None)
            app.config['ORDER_MANAGER'] = getattr(manager, 'order_manager', None)
            app.config['ACTIVE_ACCOUNTS'] = ['PRIMARY', 'GOLD', 'ALPHA']
            app.config['TELEGRAM_NOTIFIER'] = getattr(manager, 'telegram_notifier', None)
            
            register_ai_assistant(app, socketio)
            print("✅ AI Assistant integrated")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting Enhanced Trading System Dashboard...")
    print("=" * 60)
    
    # Initialize system
    if initialize_system():
        print("📊 Dashboard will be available at: http://localhost:5001")
        print("🤖 AI Assistant: Enabled")
        print("🎛️ Full Control Panel: Available")
        print("📰 News Filters: Active")
        print("🛑 Kill Switches: Ready")
        print("🎯 Strategy Switching: Enabled")
        print("📊 Mode Switching: Available")
        print("=" * 60)
        
        # Start the enhanced dashboard
        socketio.run(app, host='0.0.0.0', port=5001, debug=False)
    else:
        print("❌ Failed to start enhanced dashboard")
        sys.exit(1)

