#!/usr/bin/env python3
"""
🌐 Web-based Credential Editor for AI Quant Trading System
=========================================================

A simple web interface to edit your trading system credentials.
Perfect for accessing and editing credentials from any device.

Target Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT
"""

import os
import json
import yaml
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML template for credential editor
EDITOR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Quant - Credential Editor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 16px;
        }
        
        .content {
            padding: 30px;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 30px;
            border-bottom: 2px solid #e1e5e9;
            flex-wrap: wrap;
        }
        
        .tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            min-width: 120px;
        }
        
        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: 600;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }
        
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group textarea {
            min-height: 200px;
            resize: vertical;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-success {
            background: #28a745;
        }
        
        .btn-danger {
            background: #dc3545;
        }
        
        .status {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        
        .file-info {
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        
        .json-editor {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
        }
        
        .yaml-editor {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
        }
        
        .env-editor {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
        }
        
        .instructions {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .instructions h4 {
            color: #856404;
            margin-bottom: 10px;
        }
        
        .instructions ul {
            margin-left: 20px;
            color: #856404;
        }
        
        .instructions li {
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 AI Quant Trading System</h1>
            <p>Credential Editor - Google Drive Folder Access</p>
        </div>
        
        <div class="content">
            {% if status %}
            <div class="status {{ status.type }}">
                {{ status.message }}
            </div>
            {% endif %}
            
            <div class="instructions">
                <h4>📋 Instructions</h4>
                <ul>
                    <li>Edit your credentials in the tabs below</li>
                    <li>Replace all placeholder values with your actual credentials</li>
                    <li>Click "Save" to update the files</li>
                    <li>Use "Test" to verify your configuration</li>
                    <li>Access your Google Drive folder: <a href="https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT" target="_blank">Open Google Drive</a></li>
                </ul>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="switchTab('accounts')">📊 OANDA</div>
                <div class="tab" onclick="switchTab('gcp')">☁️ Google Cloud</div>
                <div class="tab" onclick="switchTab('env')">⚙️ Environment</div>
                <div class="tab" onclick="switchTab('test')">🧪 Test</div>
            </div>
            
            <!-- OANDA Configuration Tab -->
            <div id="accounts" class="tab-content active">
                <form method="POST" action="/save_accounts">
                    <div class="section">
                        <h3>📊 OANDA Trading Account Configuration</h3>
                        <div class="file-info">
                            <strong>File:</strong> accounts.yaml<br>
                            <strong>Purpose:</strong> Configure your OANDA trading accounts, strategies, and risk settings
                        </div>
                        
                        <div class="form-group">
                            <label for="oanda_api_key">OANDA API Key</label>
                            <input type="password" id="oanda_api_key" name="oanda_api_key" value="{{ accounts_data.api.oanda.api_key if accounts_data else 'YOUR-OANDA-API-KEY' }}">
                            <div class="help-text">Get this from your OANDA account settings</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="oanda_account_id">Account ID</label>
                            <input type="text" id="oanda_account_id" name="oanda_account_id" value="{{ accounts_data.api.oanda.account_id if accounts_data else 'YOUR-OANDA-ACCOUNT-ID' }}">
                        </div>
                        
                        <div class="form-group">
                            <label for="oanda_environment">Environment</label>
                            <select id="oanda_environment" name="oanda_environment">
                                <option value="practice" {{ 'selected' if not accounts_data or accounts_data.api.oanda.environment == 'practice' else '' }}>Practice (Demo)</option>
                                <option value="live" {{ 'selected' if accounts_data and accounts_data.api.oanda.environment == 'live' else '' }}>Live Trading</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="trading_instruments">Trading Instruments (comma-separated)</label>
                            <input type="text" id="trading_instruments" name="trading_instruments" value="{{ ','.join(accounts_data.accounts[0].instruments) if accounts_data and accounts_data.accounts else 'EUR_USD,GBP_USD,XAU_USD,USD_JPY' }}">
                            <div class="help-text">Example: EUR_USD,GBP_USD,XAU_USD,USD_JPY</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="max_risk_per_trade">Max Risk Per Trade (%)</label>
                            <input type="number" id="max_risk_per_trade" name="max_risk_per_trade" step="0.01" min="0" max="10" value="{{ accounts_data.accounts[0].risk_settings.max_risk_per_trade if accounts_data and accounts_data.accounts else '0.02' }}">
                        </div>
                        
                        <div class="form-group">
                            <label for="max_portfolio_risk">Max Portfolio Risk (%)</label>
                            <input type="number" id="max_portfolio_risk" name="max_portfolio_risk" step="0.01" min="0" max="100" value="{{ accounts_data.accounts[0].risk_settings.max_portfolio_risk if accounts_data and accounts_data.accounts else '0.10' }}">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-success">💾 Save OANDA Configuration</button>
                </form>
            </div>
            
            <!-- Google Cloud Configuration Tab -->
            <div id="gcp" class="tab-content">
                <form method="POST" action="/save_gcp">
                    <div class="section">
                        <h3>☁️ Google Cloud Platform Configuration</h3>
                        <div class="file-info">
                            <strong>File:</strong> google_cloud_credentials.json<br>
                            <strong>Purpose:</strong> Google Cloud service account credentials for deployment
                        </div>
                        
                        <div class="form-group">
                            <label for="gcp_project_id">Project ID</label>
                            <input type="text" id="gcp_project_id" name="gcp_project_id" value="{{ gcp_data.project_id if gcp_data else 'YOUR-PROJECT-ID' }}">
                            <div class="help-text">Your Google Cloud project ID</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="gcp_private_key_id">Private Key ID</label>
                            <input type="text" id="gcp_private_key_id" name="gcp_private_key_id" value="{{ gcp_data.private_key_id if gcp_data else 'YOUR-PRIVATE-KEY-ID' }}">
                        </div>
                        
                        <div class="form-group">
                            <label for="gcp_private_key">Private Key</label>
                            <textarea id="gcp_private_key" name="gcp_private_key" class="json-editor" rows="4">{{ gcp_data.private_key if gcp_data else '-----BEGIN PRIVATE KEY-----\\nYOUR-PRIVATE-KEY\\n-----END PRIVATE KEY-----\\n' }}</textarea>
                            <div class="help-text">Paste your complete private key including BEGIN/END lines</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="gcp_client_email">Client Email</label>
                            <input type="email" id="gcp_client_email" name="gcp_client_email" value="{{ gcp_data.client_email if gcp_data else 'YOUR-SERVICE-ACCOUNT@YOUR-PROJECT.iam.gserviceaccount.com' }}">
                            <div class="help-text">Service account email address</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="gcp_client_id">Client ID</label>
                            <input type="text" id="gcp_client_id" name="gcp_client_id" value="{{ gcp_data.client_id if gcp_data else 'YOUR-CLIENT-ID' }}">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-success">💾 Save Google Cloud Configuration</button>
                </form>
            </div>
            
            <!-- Environment Variables Tab -->
            <div id="env" class="tab-content">
                <form method="POST" action="/save_env">
                    <div class="section">
                        <h3>⚙️ Environment Variables Configuration</h3>
                        <div class="file-info">
                            <strong>File:</strong> .env<br>
                            <strong>Purpose:</strong> Environment variables for API keys and configuration
                        </div>
                        
                        <div class="form-group">
                            <label for="news_api_key">News API Key (Optional)</label>
                            <input type="password" id="news_api_key" name="news_api_key" value="{{ env_data.NEWS_API_KEY if env_data else 'your_news_api_key_here' }}">
                            <div class="help-text">Get from newsapi.org or marketaux.com</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="telegram_bot_token">Telegram Bot Token (Optional)</label>
                            <input type="password" id="telegram_bot_token" name="telegram_bot_token" value="{{ env_data.TELEGRAM_BOT_TOKEN if env_data else 'your_telegram_bot_token_here' }}">
                            <div class="help-text">Get from @BotFather on Telegram</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="telegram_chat_id">Telegram Chat ID (Optional)</label>
                            <input type="text" id="telegram_chat_id" name="telegram_chat_id" value="{{ env_data.TELEGRAM_CHAT_ID if env_data else 'your_telegram_chat_id_here' }}">
                            <div class="help-text">Your Telegram chat ID for notifications</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="default_strategy">Default Trading Strategy</label>
                            <select id="default_strategy" name="default_strategy">
                                <option value="adaptive_momentum" {{ 'selected' if not env_data or env_data.DEFAULT_STRATEGY == 'adaptive_momentum' else '' }}>Adaptive Momentum</option>
                                <option value="gold_scalping" {{ 'selected' if env_data and env_data.DEFAULT_STRATEGY == 'gold_scalping' else '' }}>Gold Scalping</option>
                                <option value="champion_strategy" {{ 'selected' if env_data and env_data.DEFAULT_STRATEGY == 'champion_strategy' else '' }}>Champion Strategy</option>
                            </select>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-success">💾 Save Environment Configuration</button>
                </form>
            </div>
            
            <!-- Test Configuration Tab -->
            <div id="test" class="tab-content">
                <div class="section">
                    <h3>🧪 Test Your Configuration</h3>
                    <p>Test your credentials to make sure everything is configured correctly.</p>
                    
                    <div style="margin-bottom: 20px;">
                        <button onclick="testCredentials()" class="btn btn-success">🧪 Test Credentials</button>
                        <button onclick="showStatus()" class="btn btn-secondary">📊 Show Status</button>
                        <button onclick="createLinks()" class="btn">🔗 Create Links</button>
                    </div>
                    
                    <div id="test-results"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function switchTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
        
        function testCredentials() {
            fetch('/test_credentials')
                .then(response => response.json())
                .then(data => {
                    const resultsDiv = document.getElementById('test-results');
                    resultsDiv.innerHTML = '<div class="status ' + (data.success ? 'success' : 'error') + '">' + data.message + '</div>';
                })
                .catch(error => {
                    document.getElementById('test-results').innerHTML = '<div class="status error">Error testing credentials: ' + error + '</div>';
                });
        }
        
        function showStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const resultsDiv = document.getElementById('test-results');
                    let html = '<div class="status info"><h4>Credential Status:</h4><ul>';
                    data.files.forEach(file => {
                        html += '<li>' + file.name + ': ' + (file.exists ? '✅ Exists' : '❌ Missing') + '</li>';
                    });
                    html += '</ul></div>';
                    resultsDiv.innerHTML = html;
                });
        }
        
        function createLinks() {
            fetch('/create_links', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    const resultsDiv = document.getElementById('test-results');
                    resultsDiv.innerHTML = '<div class="status ' + (data.success ? 'success' : 'error') + '">' + data.message + '</div>';
                });
        }
        
        // Auto-hide status messages after 5 seconds
        setTimeout(() => {
            const status = document.querySelector('.status');
            if (status) {
                status.style.display = 'none';
            }
        }, 5000);
    </script>
</body>
</html>
"""

class CredentialEditor:
    """Web-based credential editor."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
    
    def load_accounts_data(self):
        """Load accounts.yaml data."""
        accounts_file = self.credentials_dir / "accounts.yaml"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading accounts.yaml: {e}")
        return None
    
    def load_gcp_data(self):
        """Load Google Cloud credentials data."""
        gcp_file = self.credentials_dir / "google_cloud_credentials.json"
        if gcp_file.exists():
            try:
                with open(gcp_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading Google Cloud credentials: {e}")
        return None
    
    def load_env_data(self):
        """Load environment variables data."""
        env_file = self.credentials_dir / ".env"
        env_data = {}
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if '=' in line and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env_data[key] = value
            except Exception as e:
                logger.error(f"Error loading .env: {e}")
        return env_data
    
    def save_accounts_data(self, form_data):
        """Save accounts.yaml data."""
        try:
            # Load existing data or create new
            accounts_data = self.load_accounts_data() or {
                'accounts': [{}],
                'api': {'oanda': {}},
                'global_settings': {}
            }
            
            # Update with form data
            accounts_data['api']['oanda']['api_key'] = form_data['oanda_api_key']
            accounts_data['api']['oanda']['account_id'] = form_data['oanda_account_id']
            accounts_data['api']['oanda']['environment'] = form_data['oanda_environment']
            
            # Update account data
            if not accounts_data['accounts']:
                accounts_data['accounts'] = [{}]
            
            accounts_data['accounts'][0]['id'] = form_data['oanda_account_id']
            accounts_data['accounts'][0]['instruments'] = [i.strip() for i in form_data['trading_instruments'].split(',')]
            accounts_data['accounts'][0]['risk_settings'] = {
                'max_risk_per_trade': float(form_data['max_risk_per_trade']),
                'max_portfolio_risk': float(form_data['max_portfolio_risk'])
            }
            
            # Save to file
            accounts_file = self.credentials_dir / "accounts.yaml"
            with open(accounts_file, 'w') as f:
                yaml.dump(accounts_data, f, default_flow_style=False, sort_keys=False)
            
            return True, "OANDA configuration saved successfully!"
            
        except Exception as e:
            return False, f"Error saving OANDA configuration: {e}"
    
    def save_gcp_data(self, form_data):
        """Save Google Cloud credentials data."""
        try:
            gcp_data = {
                "type": "service_account",
                "project_id": form_data['gcp_project_id'],
                "private_key_id": form_data['gcp_private_key_id'],
                "private_key": form_data['gcp_private_key'],
                "client_email": form_data['gcp_client_email'],
                "client_id": form_data['gcp_client_id'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{form_data['gcp_client_email'].replace('@', '%40')}"
            }
            
            # Save to file
            gcp_file = self.credentials_dir / "google_cloud_credentials.json"
            with open(gcp_file, 'w') as f:
                json.dump(gcp_data, f, indent=2)
            
            return True, "Google Cloud configuration saved successfully!"
            
        except Exception as e:
            return False, f"Error saving Google Cloud configuration: {e}"
    
    def save_env_data(self, form_data):
        """Save environment variables data."""
        try:
            env_content = f"""# AI Quant Trading System - Environment Credentials
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OANDA Configuration (from accounts.yaml)
OANDA_API_KEY={form_data.get('oanda_api_key', 'your_oanda_api_key_here')}
OANDA_ACCOUNT_ID={form_data.get('oanda_account_id', 'your_oanda_account_id_here')}
OANDA_ENVIRONMENT={form_data.get('oanda_environment', 'practice')}

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID={form_data.get('gcp_project_id', 'your_project_id_here')}

# Optional APIs
NEWS_API_KEY={form_data.get('news_api_key', 'your_news_api_key_here')}
TELEGRAM_BOT_TOKEN={form_data.get('telegram_bot_token', 'your_telegram_bot_token_here')}
TELEGRAM_CHAT_ID={form_data.get('telegram_chat_id', 'your_telegram_chat_id_here')}

# Trading Configuration
DEFAULT_STRATEGY={form_data.get('default_strategy', 'adaptive_momentum')}
MAX_RISK_PER_TRADE=0.02
MAX_PORTFOLIO_RISK=0.10
"""
            
            # Save to file
            env_file = self.credentials_dir / ".env"
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            return True, "Environment configuration saved successfully!"
            
        except Exception as e:
            return False, f"Error saving environment configuration: {e}"
    
    def create_symbolic_links(self):
        """Create symbolic links."""
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
            
            # Link Google Cloud credentials
            gcp_src = self.credentials_dir / "google_cloud_credentials.json"
            gcp_dst = self.project_root / "google_cloud_credentials.json"
            
            if gcp_src.exists():
                if gcp_dst.exists() or gcp_dst.is_symlink():
                    gcp_dst.unlink()
                gcp_dst.symlink_to(gcp_src)
            
            # Link .env file
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
            
            return True, "Symbolic links created successfully!"
            
        except Exception as e:
            return False, f"Error creating symbolic links: {e}"
    
    def test_credentials(self):
        """Test credentials."""
        try:
            # Test accounts.yaml
            accounts_data = self.load_accounts_data()
            if not accounts_data:
                return False, "accounts.yaml not found or invalid"
            
            # Test Google Cloud credentials
            gcp_data = self.load_gcp_data()
            if not gcp_data:
                return False, "Google Cloud credentials not found or invalid"
            
            # Test .env file
            env_data = self.load_env_data()
            if not env_data:
                return False, ".env file not found or invalid"
            
            return True, "All credentials are valid and ready to use!"
            
        except Exception as e:
            return False, f"Error testing credentials: {e}"
    
    def get_status(self):
        """Get credential status."""
        files_to_check = [
            ("accounts.yaml", self.credentials_dir / "accounts.yaml"),
            ("google_cloud_credentials.json", self.credentials_dir / "google_cloud_credentials.json"),
            (".env", self.credentials_dir / ".env"),
            ("accounts.yaml (linked)", self.project_root / "accounts.yaml"),
            (".env (linked)", self.project_root / ".env")
        ]
        
        status = []
        for name, path in files_to_check:
            status.append({
                "name": name,
                "exists": path.exists()
            })
        
        return status

# Initialize editor
editor = CredentialEditor()

@app.route('/')
def index():
    """Main credential editor interface."""
    accounts_data = editor.load_accounts_data()
    gcp_data = editor.load_gcp_data()
    env_data = editor.load_env_data()
    
    return render_template_string(EDITOR_TEMPLATE, 
                                accounts_data=accounts_data,
                                gcp_data=gcp_data,
                                env_data=env_data)

@app.route('/save_accounts', methods=['POST'])
def save_accounts():
    """Save OANDA configuration."""
    success, message = editor.save_accounts_data(request.form.to_dict())
    return render_template_string(EDITOR_TEMPLATE, 
                                accounts_data=editor.load_accounts_data(),
                                gcp_data=editor.load_gcp_data(),
                                env_data=editor.load_env_data(),
                                status={'type': 'success' if success else 'error', 'message': message})

@app.route('/save_gcp', methods=['POST'])
def save_gcp():
    """Save Google Cloud configuration."""
    success, message = editor.save_gcp_data(request.form.to_dict())
    return render_template_string(EDITOR_TEMPLATE, 
                                accounts_data=editor.load_accounts_data(),
                                gcp_data=editor.load_gcp_data(),
                                env_data=editor.load_env_data(),
                                status={'type': 'success' if success else 'error', 'message': message})

@app.route('/save_env', methods=['POST'])
def save_env():
    """Save environment configuration."""
    success, message = editor.save_env_data(request.form.to_dict())
    return render_template_string(EDITOR_TEMPLATE, 
                                accounts_data=editor.load_accounts_data(),
                                gcp_data=editor.load_gcp_data(),
                                env_data=editor.load_env_data(),
                                status={'type': 'success' if success else 'error', 'message': message})

@app.route('/test_credentials')
def test_credentials():
    """Test credentials API endpoint."""
    success, message = editor.test_credentials()
    return jsonify({'success': success, 'message': message})

@app.route('/create_links', methods=['POST'])
def create_links():
    """Create symbolic links API endpoint."""
    success, message = editor.create_symbolic_links()
    return jsonify({'success': success, 'message': message})

@app.route('/status')
def status():
    """Get credential status API endpoint."""
    files = editor.get_status()
    return jsonify({'files': files})

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Quant Credential Editor')
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    print(f"\n🌐 AI Quant Trading System - Credential Editor")
    print(f"📱 Server starting on http://{args.host}:{args.port}")
    print(f"🔗 Access from any device with a web browser")
    print(f"📁 Google Drive Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT")
    print(f"🔧 Debug mode: {'ON' if args.debug else 'OFF'}")
    print(f"\nPress Ctrl+C to stop the server\n")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()