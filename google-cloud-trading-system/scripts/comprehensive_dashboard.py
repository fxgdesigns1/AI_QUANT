#!/usr/bin/env python3
"""
Comprehensive Trading Dashboard with Full Trade Tracking
Shows live trades, pips, drawdown, profit, and complete trade history
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.trade_tracker import TradeTracker

app = Flask(__name__)

# Initialize trade tracker
trade_tracker = TradeTracker()

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
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
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; padding: 20px; 
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .card h3 { margin-bottom: 15px; color: #64B5F6; }
        
        .trade-card { 
            background: rgba(0,0,0,0.2); 
            border-radius: 10px; padding: 15px; 
            margin-bottom: 15px; border-left: 4px solid #2196F3;
        }
        .trade-buy { border-left-color: #4CAF50; }
        .trade-sell { border-left-color: #f44336; }
        .trade-pending { border-left-color: #ff9800; }
        .trade-filled { border-left-color: #4CAF50; }
        
        .trade-header { 
            display: flex; justify-content: space-between; 
            align-items: center; margin-bottom: 10px;
        }
        .trade-instrument { font-weight: bold; font-size: 1.1em; }
        .trade-side { 
            padding: 4px 8px; border-radius: 4px; 
            font-size: 0.9em; font-weight: bold;
        }
        .side-buy { background: #4CAF50; color: white; }
        .side-sell { background: #f44336; color: white; }
        
        .trade-details { 
            display: grid; grid-template-columns: 1fr 1fr; 
            gap: 10px; margin-bottom: 10px;
        }
        .detail-item { 
            background: rgba(255,255,255,0.1); 
            padding: 8px; border-radius: 5px;
        }
        .detail-label { font-size: 0.8em; color: #ccc; }
        .detail-value { font-weight: bold; }
        
        .pips-display { 
            text-align: center; padding: 10px; 
            border-radius: 8px; margin: 10px 0;
        }
        .pips-positive { background: rgba(76, 175, 80, 0.3); }
        .pips-negative { background: rgba(244, 67, 54, 0.3); }
        .pips-neutral { background: rgba(255, 255, 255, 0.1); }
        
        .performance-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
            gap: 15px; margin-bottom: 20px;
        }
        .performance-item { 
            background: rgba(0,0,0,0.2); 
            padding: 15px; border-radius: 8px; text-align: center;
        }
        .performance-value { 
            font-size: 1.5em; font-weight: bold; 
            margin-bottom: 5px;
        }
        .performance-label { 
            font-size: 0.9em; color: #ccc;
        }
        
        .trade-history { 
            max-height: 400px; overflow-y: auto; 
            background: rgba(0,0,0,0.2); 
            border-radius: 10px; padding: 15px;
        }
        .history-item { 
            display: flex; justify-content: space-between; 
            align-items: center; padding: 10px; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .history-item:last-child { border-bottom: none; }
        
        .btn { 
            padding: 8px 16px; border: none; border-radius: 5px; 
            cursor: pointer; font-weight: bold; margin: 5px; transition: all 0.3s;
        }
        .btn-primary { background: #2196F3; color: white; }
        .btn-success { background: #4CAF50; color: white; }
        .btn-warning { background: #ff9800; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        
        .london-countdown { 
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            padding: 20px; border-radius: 10px; text-align: center;
            margin-bottom: 20px; font-size: 1.2em; font-weight: bold;
        }
        
        .alert-box { 
            background: rgba(255, 193, 7, 0.2); 
            border: 1px solid #ffc107; 
            border-radius: 8px; padding: 15px; 
            margin-bottom: 20px;
        }
        .alert-title { 
            font-weight: bold; color: #ffc107; 
            margin-bottom: 10px;
        }
        
        .footer { 
            text-align: center; margin-top: 30px; 
            padding: 20px; background: rgba(0,0,0,0.3); 
            border-radius: 10px;
        }
        
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .pulse { animation: pulse 2s infinite; }
        
        .loading { 
            text-align: center; padding: 20px; 
            color: #ccc;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Comprehensive Trading Dashboard</h1>
            <p>Live Trade Tracking • Pips • Drawdown • Profit Analysis</p>
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
                <strong>Active Trades:</strong> <span id="active-trades-count">0</span>
            </div>
            <div class="status-item">
                <strong>Today's P&L:</strong> <span id="today-pl">$0.00</span>
            </div>
            <div class="status-item">
                <strong>Last Update:</strong> <span id="last-update">Loading...</span>
            </div>
        </div>
        
        <!-- Alert Box -->
        <div class="alert-box" id="alert-box" style="display: none;">
            <div class="alert-title">🚨 System Alert</div>
            <div id="alert-message"></div>
        </div>
        
        <div class="grid">
            <!-- Active Trades -->
            <div class="card">
                <h3>💰 Active Trades</h3>
                <div id="active-trades">
                    <div class="loading">Loading active trades...</div>
                </div>
            </div>
            
            <!-- Performance Metrics -->
            <div class="card">
                <h3>📈 Performance Metrics</h3>
                <div class="performance-grid" id="performance-metrics">
                    <div class="performance-item">
                        <div class="performance-value" id="total-trades">0</div>
                        <div class="performance-label">Total Trades</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="win-rate">0%</div>
                        <div class="performance-label">Win Rate</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="total-pips">0</div>
                        <div class="performance-label">Total Pips</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="avg-pips">0</div>
                        <div class="performance-label">Avg Pips</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="max-drawdown">0</div>
                        <div class="performance-label">Max Drawdown</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="avg-duration">0m</div>
                        <div class="performance-label">Avg Duration</div>
                    </div>
                </div>
            </div>
            
            <!-- Trade History -->
            <div class="card">
                <h3>📋 Recent Trade History</h3>
                <div class="trade-history" id="trade-history">
                    <div class="loading">Loading trade history...</div>
                </div>
            </div>
            
            <!-- System Logs -->
            <div class="card">
                <h3>📝 System Logs</h3>
                <div class="trade-history" id="system-logs">
                    <div class="loading">Loading system logs...</div>
                </div>
            </div>
            
            <!-- Backtesting Export -->
            <div class="card">
                <h3>🔬 Backtesting Integration</h3>
                <div style="text-align: center;">
                    <p style="margin-bottom: 15px;">Export real trading data for backtesting analysis</p>
                    <button class="btn btn-primary" onclick="exportBacktestingData()">📊 Export Data</button>
                    <button class="btn btn-success" onclick="analyzePerformance()">📈 Analyze Performance</button>
                    <div id="export-status" style="margin-top: 15px; font-size: 0.9em;"></div>
                </div>
            </div>
            
            <!-- Account Summary -->
            <div class="card">
                <h3>💼 Account Summary</h3>
                <div id="account-summary">
                    <div class="performance-item">
                        <div class="performance-value" id="total-balance">$0.00</div>
                        <div class="performance-label">Total Balance</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="total-pl">$0.00</div>
                        <div class="performance-label">Total P&L</div>
                    </div>
                    <div class="performance-item">
                        <div class="performance-value" id="pl-percentage">0%</div>
                        <div class="performance-label">P&L %</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>📊 Comprehensive Trading System | Real-time Tracking | Full Analytics</p>
            <p>Last Updated: <span id="footer-time">Loading...</span></p>
        </div>
    </div>

    <script>
        // Global state
        let lastUpdateTime = null;
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            updateDashboard();
            updateLondonCountdown();
            startRealTimeUpdates();
        });
        
        // Real-time updates
        function startRealTimeUpdates() {
            setInterval(() => {
                updateDashboard();
                updateLondonCountdown();
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                document.getElementById('footer-time').textContent = new Date().toLocaleString();
            }, 5000);
        }
        
        // London session countdown
        function updateLondonCountdown() {
            const now = new Date();
            const utcHour = now.getUTCHours();
            
            let londonStatus, nextSession;
            
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
                    const hoursUntil = 8 - utcHour;
                    nextSession = `LONDON in ${hoursUntil} hours`;
                } else {
                    const hoursUntil = 24 - utcHour + 8;
                    nextSession = `LONDON in ${hoursUntil} hours`;
                }
                document.getElementById('london-countdown').style.background = 'linear-gradient(45deg, #ff6b6b, #4ecdc4)';
            }
            
            document.getElementById('london-status').textContent = londonStatus;
            document.getElementById('next-session').textContent = nextSession;
        }
        
        // Update dashboard data
        function updateDashboard() {
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => {
                    updateActiveTrades(data.active_trades || []);
                    updatePerformanceMetrics(data.performance || {});
                    updateTradeHistory(data.recent_trades || []);
                    updateAccountSummary(data.account_summary || {});
                    updateSystemLogs(data.system_logs || []);
                    
                    // Update status bar
                    document.getElementById('active-trades-count').textContent = data.active_trades?.length || 0;
                    document.getElementById('today-pl').textContent = `$${(data.performance?.total_profit_loss || 0).toFixed(2)}`;
                    
                    lastUpdateTime = data.last_update;
                })
                .catch(error => {
                    console.error('Dashboard update error:', error);
                    showAlert('Error updating dashboard data', 'error');
                });
        }
        
        // Update active trades
        function updateActiveTrades(trades) {
            const container = document.getElementById('active-trades');
            
            if (trades.length === 0) {
                container.innerHTML = '<div class="loading">No active trades</div>';
                return;
            }
            
            container.innerHTML = '';
            
            trades.forEach(trade => {
                const tradeCard = document.createElement('div');
                tradeCard.className = `trade-card trade-${trade.side.toLowerCase()} trade-${trade.status}`;
                
                const pipsClass = (trade.current_pips || 0) >= 0 ? 'pips-positive' : 'pips-negative';
                const pipsValue = trade.current_pips || 0;
                const drawdownValue = trade.current_drawdown || 0;
                
                tradeCard.innerHTML = `
                    <div class="trade-header">
                        <span class="trade-instrument">${trade.instrument}</span>
                        <span class="trade-side side-${trade.side.toLowerCase()}">${trade.side}</span>
                    </div>
                    <div class="trade-details">
                        <div class="detail-item">
                            <div class="detail-label">Entry Price</div>
                            <div class="detail-value">${trade.entry_price}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Units</div>
                            <div class="detail-value">${trade.units}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Stop Loss</div>
                            <div class="detail-value">${trade.stop_loss}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Take Profit</div>
                            <div class="detail-value">${trade.take_profit}</div>
                        </div>
                    </div>
                    <div class="pips-display ${pipsClass}">
                        <div style="font-size: 1.2em; font-weight: bold;">
                            ${pipsValue >= 0 ? '+' : ''}${pipsValue.toFixed(1)} pips
                        </div>
                        <div style="font-size: 0.9em;">
                            Max Drawdown: ${drawdownValue.toFixed(1)} pips
                        </div>
                    </div>
                    <div style="font-size: 0.8em; color: #ccc; margin-top: 10px;">
                        Strategy: ${trade.strategy} | Session: ${trade.session} | 
                        Entered: ${new Date(trade.timestamp).toLocaleTimeString()}
                    </div>
                `;
                
                container.appendChild(tradeCard);
            });
        }
        
        // Update performance metrics
        function updatePerformanceMetrics(performance) {
            document.getElementById('total-trades').textContent = performance.total_trades || 0;
            document.getElementById('win-rate').textContent = `${(performance.win_rate || 0).toFixed(1)}%`;
            document.getElementById('total-pips').textContent = (performance.total_pips || 0).toFixed(1);
            document.getElementById('avg-pips').textContent = (performance.avg_pips || 0).toFixed(1);
            document.getElementById('max-drawdown').textContent = `$${(performance.max_drawdown || 0).toFixed(2)}`;
            document.getElementById('avg-duration').textContent = `${Math.round(performance.avg_duration_minutes || 0)}m`;
        }
        
        // Update trade history
        function updateTradeHistory(trades) {
            const container = document.getElementById('trade-history');
            
            if (trades.length === 0) {
                container.innerHTML = '<div class="loading">No trade history</div>';
                return;
            }
            
            container.innerHTML = '';
            
            trades.slice(0, 20).forEach(trade => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                
                const plClass = (trade.profit_loss || 0) >= 0 ? 'color: #4CAF50' : 'color: #f44336';
                const plSign = (trade.profit_loss || 0) >= 0 ? '+' : '';
                
                historyItem.innerHTML = `
                    <div>
                        <div style="font-weight: bold;">${trade.instrument} ${trade.side}</div>
                        <div style="font-size: 0.8em; color: #ccc;">
                            ${trade.strategy} | ${new Date(trade.timestamp).toLocaleString()}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: bold; ${plClass}">
                            ${plSign}$${(trade.profit_loss || 0).toFixed(2)}
                        </div>
                        <div style="font-size: 0.8em; color: #ccc;">
                            ${(trade.pips_profit || 0).toFixed(1)} pips
                        </div>
                    </div>
                `;
                
                container.appendChild(historyItem);
            });
        }
        
        // Update account summary
        function updateAccountSummary(summary) {
            document.getElementById('total-balance').textContent = `$${(summary.total_balance || 0).toLocaleString()}`;
            document.getElementById('total-pl').textContent = `$${(summary.total_pl || 0).toFixed(2)}`;
            document.getElementById('pl-percentage').textContent = `${(summary.pl_percentage || 0).toFixed(2)}%`;
        }
        
        // Update system logs
        function updateSystemLogs(logs) {
            const container = document.getElementById('system-logs');
            
            if (logs.length === 0) {
                container.innerHTML = '<div class="loading">No system logs</div>';
                return;
            }
            
            container.innerHTML = '';
            
            logs.slice(0, 10).forEach(log => {
                const logItem = document.createElement('div');
                logItem.className = 'history-item';
                
                const levelColor = {
                    'INFO': '#4CAF50',
                    'WARNING': '#ff9800',
                    'ERROR': '#f44336',
                    'CRITICAL': '#e91e63'
                }[log.level] || '#ccc';
                
                logItem.innerHTML = `
                    <div>
                        <div style="font-weight: bold; color: ${levelColor};">[${log.level}]</div>
                        <div style="font-size: 0.8em; color: #ccc;">
                            ${new Date(log.timestamp).toLocaleString()}
                        </div>
                    </div>
                    <div style="text-align: right; max-width: 60%;">
                        <div style="font-size: 0.9em;">${log.message}</div>
                    </div>
                `;
                
                container.appendChild(logItem);
            });
        }
        
        // Export backtesting data
        function exportBacktestingData() {
            const statusDiv = document.getElementById('export-status');
            statusDiv.innerHTML = 'Exporting data...';
            
            fetch('/api/export-backtesting', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusDiv.innerHTML = `✅ Data exported: ${data.filename}`;
                        showAlert('Backtesting data exported successfully', 'success');
                    } else {
                        statusDiv.innerHTML = '❌ Export failed';
                        showAlert('Failed to export backtesting data', 'error');
                    }
                })
                .catch(error => {
                    statusDiv.innerHTML = '❌ Export failed';
                    showAlert('Error exporting data', 'error');
                });
        }
        
        // Analyze performance
        function analyzePerformance() {
            const statusDiv = document.getElementById('export-status');
            statusDiv.innerHTML = 'Analyzing performance...';
            
            fetch('/api/analyze-performance', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusDiv.innerHTML = '✅ Analysis complete';
                        showAlert('Performance analysis completed', 'success');
                    } else {
                        statusDiv.innerHTML = '❌ Analysis failed';
                        showAlert('Failed to analyze performance', 'error');
                    }
                })
                .catch(error => {
                    statusDiv.innerHTML = '❌ Analysis failed';
                    showAlert('Error analyzing performance', 'error');
                });
        }
        
        // Show alert
        function showAlert(message, type) {
            const alertBox = document.getElementById('alert-box');
            const alertMessage = document.getElementById('alert-message');
            
            alertMessage.textContent = message;
            alertBox.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                alertBox.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
    ''')

# API Endpoints
@app.route('/api/dashboard-data')
def api_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        dashboard_data = trade_tracker.get_dashboard_data()
        
        # Add account summary (mock data - replace with real data)
        dashboard_data['account_summary'] = {
            'total_balance': 300160.35,
            'total_pl': -12553.56,
            'pl_percentage': -4.18
        }
        
        # Add system logs (mock data - replace with real logs)
        dashboard_data['system_logs'] = [
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'System monitoring active'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'level': 'INFO',
                'message': 'London session countdown: 6 hours'
            }
        ]
        
        return jsonify(dashboard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-backtesting', methods=['POST'])
def api_export_backtesting():
    """Export data for backtesting"""
    try:
        export_data = trade_tracker.export_for_backtesting(days=30)
        
        if export_data:
            return jsonify({
                'success': True,
                'filename': f"backtesting_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                'data': export_data
            })
        else:
            return jsonify({'success': False, 'error': 'Export failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-performance', methods=['POST'])
def api_analyze_performance():
    """Analyze trading performance"""
    try:
        # Get performance metrics
        performance = trade_tracker.get_performance_metrics()
        
        # Log analysis
        trade_tracker.log_system_event(
            'performance_analysis',
            'INFO',
            f'Performance analysis completed: {performance.get("total_trades", 0)} trades analyzed'
        )
        
        return jsonify({
            'success': True,
            'analysis': performance
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Comprehensive Trading Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5002")
    print("💰 Live Trade Tracking: Enabled")
    print("📈 Performance Analytics: Active")
    print("🔬 Backtesting Integration: Ready")
    print("📝 System Logging: Active")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5002, debug=False)

