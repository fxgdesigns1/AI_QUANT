#!/usr/bin/env python3
"""
📱 Mobile Credential Uploader for AI Quant Trading System
========================================================

This script allows you to upload credentials from mobile devices or any device
where you can't directly access Google Drive files.

Usage:
    python mobile_credential_uploader.py --start-server
    # Then visit http://localhost:8080 in your mobile browser
"""

import os
import json
import yaml
import base64
import hashlib
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML template for mobile interface
MOBILE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Quant - Mobile Credential Upload</title>
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
            max-width: 500px;
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
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .form-container {
            padding: 30px;
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
        }
        
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group textarea {
            min-height: 100px;
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
            width: 100%;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:active {
            transform: translateY(0);
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
        
        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        
        .file-upload {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            background: #f8f9ff;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .file-upload:hover {
            background: #f0f2ff;
        }
        
        .file-upload input[type="file"] {
            display: none;
        }
        
        .file-upload-label {
            display: block;
            cursor: pointer;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 2px solid #e1e5e9;
        }
        
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AI Quant Trading</h1>
            <p>Mobile Credential Upload</p>
        </div>
        
        <div class="form-container">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('manual')">📝 Manual</div>
                <div class="tab" onclick="switchTab('file')">📁 File Upload</div>
                <div class="tab" onclick="switchTab('qr')">📱 QR Code</div>
            </div>
            
            {% if status %}
            <div class="status {{ status.type }}">
                {{ status.message }}
            </div>
            {% endif %}
            
            <!-- Manual Entry Tab -->
            <div id="manual" class="tab-content active">
                <form method="POST" action="/upload_manual">
                    <div class="section">
                        <h3>🔑 OANDA API Credentials</h3>
                        <div class="form-group">
                            <label for="oanda_api_key">OANDA API Key</label>
                            <input type="password" id="oanda_api_key" name="oanda_api_key" required>
                            <div class="help-text">Get this from your OANDA account settings</div>
                        </div>
                        <div class="form-group">
                            <label for="oanda_account_id">Account ID</label>
                            <input type="text" id="oanda_account_id" name="oanda_account_id" required>
                        </div>
                        <div class="form-group">
                            <label for="oanda_environment">Environment</label>
                            <select id="oanda_environment" name="oanda_environment">
                                <option value="practice">Practice (Demo)</option>
                                <option value="live">Live Trading</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>☁️ Google Cloud Credentials</h3>
                        <div class="form-group">
                            <label for="gcp_project_id">Project ID</label>
                            <input type="text" id="gcp_project_id" name="gcp_project_id" required>
                        </div>
                        <div class="form-group">
                            <label for="gcp_credentials">Service Account JSON</label>
                            <textarea id="gcp_credentials" name="gcp_credentials" placeholder="Paste your Google Cloud service account JSON here..." required></textarea>
                            <div class="help-text">Get this from Google Cloud Console > IAM & Admin > Service Accounts</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📰 Optional APIs</h3>
                        <div class="form-group">
                            <label for="news_api_key">News API Key</label>
                            <input type="password" id="news_api_key" name="news_api_key">
                        </div>
                        <div class="form-group">
                            <label for="telegram_bot_token">Telegram Bot Token</label>
                            <input type="password" id="telegram_bot_token" name="telegram_bot_token">
                        </div>
                        <div class="form-group">
                            <label for="telegram_chat_id">Telegram Chat ID</label>
                            <input type="text" id="telegram_chat_id" name="telegram_chat_id">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">💾 Save Credentials</button>
                </form>
            </div>
            
            <!-- File Upload Tab -->
            <div id="file" class="tab-content">
                <form method="POST" action="/upload_file" enctype="multipart/form-data">
                    <div class="section">
                        <h3>📁 Upload Credential Files</h3>
                        <div class="file-upload">
                            <label for="accounts_file" class="file-upload-label">
                                <div>📄 Upload accounts.yaml</div>
                                <div style="font-size: 12px; margin-top: 5px; color: #666;">
                                    Click to select accounts.yaml file
                                </div>
                            </label>
                            <input type="file" id="accounts_file" name="accounts_file" accept=".yaml,.yml">
                        </div>
                        
                        <div class="file-upload" style="margin-top: 15px;">
                            <label for="gcp_file" class="file-upload-label">
                                <div>🔑 Upload Google Cloud JSON</div>
                                <div style="font-size: 12px; margin-top: 5px; color: #666;">
                                    Click to select service account JSON file
                                </div>
                            </label>
                            <input type="file" id="gcp_file" name="gcp_file" accept=".json">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">📤 Upload Files</button>
                </form>
            </div>
            
            <!-- QR Code Tab -->
            <div id="qr" class="tab-content">
                <div class="section">
                    <h3>📱 QR Code Method</h3>
                    <p>Generate a QR code with your credentials that you can scan from another device.</p>
                    
                    <form method="POST" action="/generate_qr">
                        <div class="form-group">
                            <label for="qr_data">Credential Data</label>
                            <textarea id="qr_data" name="qr_data" placeholder="Paste your credential data here (JSON format)..." required></textarea>
                        </div>
                        <button type="submit" class="btn">🔗 Generate QR Code</button>
                    </form>
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

class MobileCredentialUploader:
    """Handles mobile credential uploads."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
    
    def save_manual_credentials(self, form_data: dict) -> bool:
        """Save credentials from manual form input."""
        try:
            # Create accounts.yaml
            accounts_config = {
                'accounts': [
                    {
                        'id': form_data['oanda_account_id'],
                        'name': 'Primary Trading Account',
                        'display_name': '🚀 AI Quant Trader',
                        'strategy': 'adaptive_momentum',
                        'description': 'AI-powered automated trading',
                        'instruments': ['EUR_USD', 'GBP_USD', 'XAU_USD'],
                        'risk_settings': {
                            'max_risk_per_trade': 0.02,
                            'max_portfolio_risk': 0.10,
                            'max_positions': 5,
                            'daily_trade_limit': 50
                        },
                        'active': True,
                        'priority': 1
                    }
                ],
                'api': {
                    'oanda': {
                        'practice_url': 'https://api-fxpractice.oanda.com',
                        'live_url': 'https://api-fxtrade.oanda.com',
                        'api_key': form_data['oanda_api_key'],
                        'account_id': form_data['oanda_account_id'],
                        'environment': form_data['oanda_environment']
                    }
                },
                'global_settings': {
                    'timezone': 'Europe/London',
                    'trading_hours': {
                        'start': '08:00',
                        'end': '17:00'
                    },
                    'max_total_exposure': 0.10,
                    'max_concurrent_positions': 5,
                    'telegram': {
                        'enabled': bool(form_data.get('telegram_bot_token')),
                        'bot_token': form_data.get('telegram_bot_token', ''),
                        'chat_id': form_data.get('telegram_chat_id', '')
                    }
                }
            }
            
            # Save accounts.yaml
            accounts_file = self.credentials_dir / "accounts.yaml"
            with open(accounts_file, 'w') as f:
                yaml.dump(accounts_config, f, default_flow_style=False, sort_keys=False)
            
            # Save Google Cloud credentials
            if form_data.get('gcp_credentials'):
                try:
                    gcp_data = json.loads(form_data['gcp_credentials'])
                    gcp_file = self.credentials_dir / "google_cloud_credentials.json"
                    with open(gcp_file, 'w') as f:
                        json.dump(gcp_data, f, indent=2)
                except json.JSONDecodeError:
                    return False, "Invalid JSON format for Google Cloud credentials"
            
            # Create environment file
            env_content = f"""# AI Quant Trading System - Environment Credentials
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OANDA_API_KEY={form_data['oanda_api_key']}
OANDA_ACCOUNT_ID={form_data['oanda_account_id']}
OANDA_ENVIRONMENT={form_data['oanda_environment']}
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID={form_data['gcp_project_id']}
NEWS_API_KEY={form_data.get('news_api_key', '')}
TELEGRAM_BOT_TOKEN={form_data.get('telegram_bot_token', '')}
TELEGRAM_CHAT_ID={form_data.get('telegram_chat_id', '')}
DEFAULT_STRATEGY=adaptive_momentum
MAX_RISK_PER_TRADE=0.02
MAX_PORTFOLIO_RISK=0.10
"""
            
            env_file = self.credentials_dir / ".env"
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            # Create symbolic links
            self._create_symlinks()
            
            return True, "Credentials saved successfully!"
            
        except Exception as e:
            return False, f"Error saving credentials: {str(e)}"
    
    def save_uploaded_files(self, files: dict) -> bool:
        """Save uploaded credential files."""
        try:
            saved_files = []
            
            # Save accounts.yaml
            if 'accounts_file' in files and files['accounts_file'].filename:
                accounts_file = self.credentials_dir / "accounts.yaml"
                files['accounts_file'].save(str(accounts_file))
                saved_files.append("accounts.yaml")
            
            # Save Google Cloud credentials
            if 'gcp_file' in files and files['gcp_file'].filename:
                gcp_file = self.credentials_dir / "google_cloud_credentials.json"
                files['gcp_file'].save(str(gcp_file))
                saved_files.append("google_cloud_credentials.json")
            
            if saved_files:
                self._create_symlinks()
                return True, f"Files uploaded successfully: {', '.join(saved_files)}"
            else:
                return False, "No files were uploaded"
                
        except Exception as e:
            return False, f"Error uploading files: {str(e)}"
    
    def _create_symlinks(self):
        """Create symbolic links to make credentials accessible."""
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
                logger.info(f"✅ Linked accounts.yaml")
            
            # Link .env file
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
                logger.info(f"✅ Linked .env")
                
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")

# Initialize uploader
uploader = MobileCredentialUploader()

@app.route('/')
def index():
    """Main mobile interface."""
    return render_template_string(MOBILE_TEMPLATE)

@app.route('/upload_manual', methods=['POST'])
def upload_manual():
    """Handle manual credential upload."""
    success, message = uploader.save_manual_credentials(request.form.to_dict())
    
    status_type = 'success' if success else 'error'
    return render_template_string(MOBILE_TEMPLATE, status={'type': status_type, 'message': message})

@app.route('/upload_file', methods=['POST'])
def upload_file():
    """Handle file upload."""
    success, message = uploader.save_uploaded_files(request.files)
    
    status_type = 'success' if success else 'error'
    return render_template_string(MOBILE_TEMPLATE, status={'type': status_type, 'message': message})

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    """Generate QR code for credentials."""
    # This would implement QR code generation
    # For now, just show a success message
    return render_template_string(MOBILE_TEMPLATE, 
                                status={'type': 'success', 'message': 'QR code generation not yet implemented. Use manual or file upload methods.'})

def main():
    """Start the mobile credential upload server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Quant Mobile Credential Uploader')
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    print(f"\n🚀 AI Quant Mobile Credential Uploader")
    print(f"📱 Server starting on http://{args.host}:{args.port}")
    print(f"🌐 Open this URL in your mobile browser to upload credentials")
    print(f"🔧 Debug mode: {'ON' if args.debug else 'OFF'}")
    print(f"\nPress Ctrl+C to stop the server\n")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()