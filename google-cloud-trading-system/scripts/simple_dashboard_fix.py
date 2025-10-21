#!/usr/bin/env python3
"""
Simple Dashboard Fix - Minimal JavaScript that will definitely work
"""

from flask import Flask, render_template_string, jsonify, request
import logging
import os
from datetime import datetime

# Import OANDA components
from src.core.oanda_client import OandaClient
from src.core.account_manager import AccountManager
from src.core.data_feed import LiveDataFeed

app = Flask(__name__)

# Initialize OANDA components
account_manager = None
data_feed = None

def initialize_oanda_components():
    """Initialize OANDA components for live data"""
    global account_manager, data_feed
    try:
        account_manager = AccountManager()
        data_feed = LiveDataFeed()
        logging.info("✅ OANDA components initialized for live data")
        data_feed.start()
    except Exception as e:
        logging.error(f"❌ Failed to initialize OANDA components: {e}")
        account_manager = None
        data_feed = None

initialize_oanda_components()

# Simple HTML template with minimal JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Trading System Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a1a; color: white; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; color: #64B5F6; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #2d2d2d; padding: 20px; border-radius: 10px; border: 1px solid #444; }
        .card h3 { margin-top: 0; color: #64B5F6; }
        .account-card { background: #333; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .account-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .account-name { font-weight: bold; color: #64B5F6; }
        .account-balance { color: #4CAF50; font-weight: bold; }
        .pl-positive { color: #4CAF50; }
        .pl-negative { color: #f44336; }
        .signal-item { background: #333; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #64B5F6; }
        .signal-buy { border-left-color: #4CAF50; }
        .signal-sell { border-left-color: #f44336; }
        .loading { text-align: center; padding: 20px; color: #64B5F6; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Enhanced Trading System Dashboard</h1>
        
        <div class="grid">
            <!-- Account Status -->
            <div class="card">
                <h3>💰 Account Status</h3>
                <div id="account-status">
                    <div class="loading">
                        <div class="pulse">🔄 Loading live account data...</div>
                    </div>
                </div>
            </div>
            
            <!-- Live Prices -->
            <div class="card">
                <h3>💱 Live Prices</h3>
                <div id="live-prices">
                    <div class="loading">
                        <div class="pulse">🔄 Loading live market prices...</div>
                    </div>
                </div>
            </div>
            
            <!-- Trading Signals -->
            <div class="card">
                <h3>📊 Live Signals</h3>
                <div id="signals-feed">
                    <div class="loading">
                        <div class="pulse">🔄 Loading live trading signals...</div>
                    </div>
                </div>
            </div>
            
            <!-- Performance Metrics -->
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
        
        // Load data when page loads
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
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Main dashboard route"""
    return render_template_string(HTML_TEMPLATE)

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
                    logging.error(f"Failed to get account info for {account_name}: {e}")
            return jsonify({'accounts': accounts_data})
        else:
            return jsonify({'accounts': {}})
    except Exception as e:
        logging.error(f"Accounts API error: {e}")
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
                logging.error(f"Direct OANDA price fetch failed: {e}")
        
        return jsonify({'prices': prices_data})
    except Exception as e:
        logging.error(f"Prices API error: {e}")
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
                    logging.error(f"Signal generation failed for {instrument}: {e}")
        
        return jsonify({'signals': signals})
    except Exception as e:
        logging.error(f"Signals API error: {e}")
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
                    logging.error(f"Failed to get performance for {account_name}: {e}")
        
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
        logging.error(f"Performance API error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("🚀 Starting Simple Trading System Dashboard with Live OANDA Data...")
    print("🤖 AI Assistant: Disabled (focusing on data display)")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)

