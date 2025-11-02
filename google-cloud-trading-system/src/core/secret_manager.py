"""
Google Cloud Secret Manager Integration
Securely manages sensitive credentials for mobile and cloud access
"""
import os
import json
from typing import Optional, Dict, Any

# Try to import Secret Manager, but make it optional for local development
try:
    from google.cloud import secretmanager
    from google.api_core import exceptions
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    secretmanager = None
    exceptions = None

class SecretManager:
    """Manages credentials via Google Cloud Secret Manager"""
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Secret Manager
        
        Args:
            project_id: Google Cloud project ID. If None, will try to get from environment
        """
        if not SECRET_MANAGER_AVAILABLE:
            raise ImportError("google-cloud-secret-manager not installed. Install with: pip install google-cloud-secret-manager")
        
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
        if not self.project_id:
            raise ValueError(
                "No Google Cloud project ID found. Set GOOGLE_CLOUD_PROJECT or GCP_PROJECT environment variable"
            )
        
        self.client = secretmanager.SecretManagerServiceClient()
        self._cache = {}  # In-memory cache to reduce API calls
    
    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Get a secret value from Google Cloud Secret Manager
        
        Args:
            secret_name: Name of the secret
            version: Version of the secret (default: "latest")
            
        Returns:
            The secret value as a string
        """
        # Check cache first
        cache_key = f"{secret_name}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Build the resource name
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            
            # Access the secret version
            response = self.client.access_secret_version(request={"name": name})
            
            # Decode the secret payload
            secret_value = response.payload.data.decode('UTF-8')
            
            # Cache the value
            self._cache[cache_key] = secret_value
            
            return secret_value
            
        except exceptions.NotFound:
            raise ValueError(f"Secret '{secret_name}' not found in project '{self.project_id}'")
        except Exception as e:
            raise Exception(f"Error accessing secret '{secret_name}': {str(e)}")
    
    def get_secret_json(self, secret_name: str, version: str = "latest") -> Dict[str, Any]:
        """
        Get a secret that contains JSON data
        
        Args:
            secret_name: Name of the secret
            version: Version of the secret (default: "latest")
            
        Returns:
            The secret value as a dictionary
        """
        secret_value = self.get_secret(secret_name, version)
        try:
            return json.loads(secret_value)
        except json.JSONDecodeError:
            raise ValueError(f"Secret '{secret_name}' does not contain valid JSON")
    
    def create_secret(self, secret_name: str, secret_value: str, labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a new secret in Google Cloud Secret Manager
        
        Args:
            secret_name: Name for the secret
            secret_value: Value to store
            labels: Optional labels for the secret
            
        Returns:
            True if successful
        """
        try:
            parent = f"projects/{self.project_id}"
            
            # Create the secret
            secret = self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": labels or {}
                    }
                }
            )
            
            # Add the secret version with the actual data
            self.client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode('UTF-8')}
                }
            )
            
            print(f"✓ Created secret: {secret_name}")
            return True
            
        except exceptions.AlreadyExists:
            print(f"⚠ Secret '{secret_name}' already exists. Use update_secret() to change it.")
            return False
        except Exception as e:
            print(f"✗ Error creating secret '{secret_name}': {str(e)}")
            return False
    
    def update_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Update an existing secret with a new version
        
        Args:
            secret_name: Name of the secret to update
            secret_value: New value
            
        Returns:
            True if successful
        """
        try:
            parent = f"projects/{self.project_id}/secrets/{secret_name}"
            
            # Add a new version
            self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode('UTF-8')}
                }
            )
            
            # Clear cache
            cache_keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{secret_name}:")]
            for key in cache_keys_to_remove:
                del self._cache[key]
            
            print(f"✓ Updated secret: {secret_name}")
            return True
            
        except exceptions.NotFound:
            print(f"✗ Secret '{secret_name}' not found. Use create_secret() first.")
            return False
        except Exception as e:
            print(f"✗ Error updating secret '{secret_name}': {str(e)}")
            return False
    
    def delete_secret(self, secret_name: str) -> bool:
        """
        Delete a secret permanently
        
        Args:
            secret_name: Name of the secret to delete
            
        Returns:
            True if successful
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}"
            self.client.delete_secret(request={"name": name})
            
            # Clear from cache
            cache_keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{secret_name}:")]
            for key in cache_keys_to_remove:
                del self._cache[key]
            
            print(f"✓ Deleted secret: {secret_name}")
            return True
            
        except exceptions.NotFound:
            print(f"⚠ Secret '{secret_name}' not found.")
            return False
        except Exception as e:
            print(f"✗ Error deleting secret '{secret_name}': {str(e)}")
            return False
    
    def list_secrets(self) -> list:
        """
        List all secrets in the project
        
        Returns:
            List of secret names
        """
        try:
            parent = f"projects/{self.project_id}"
            secrets = []
            
            for secret in self.client.list_secrets(request={"parent": parent}):
                secret_name = secret.name.split('/')[-1]
                secrets.append(secret_name)
            
            return secrets
            
        except Exception as e:
            print(f"✗ Error listing secrets: {str(e)}")
            return []
    
    def clear_cache(self):
        """Clear the in-memory cache"""
        self._cache = {}


class CredentialsManager:
    """High-level credentials manager that works with both Secret Manager and .env fallback"""
    
    def __init__(self, use_secret_manager: bool = True, project_id: Optional[str] = None):
        """
        Initialize credentials manager
        
        Args:
            use_secret_manager: If True, use Google Cloud Secret Manager. If False, use .env files
            project_id: Google Cloud project ID (only needed if use_secret_manager=True)
        """
        self.use_secret_manager = use_secret_manager
        self.secret_manager = None
        
        if use_secret_manager:
            try:
                self.secret_manager = SecretManager(project_id)
                print("✓ Connected to Google Cloud Secret Manager")
            except Exception as e:
                print(f"⚠ Could not connect to Secret Manager: {e}")
                print("  Falling back to .env files")
                self.use_secret_manager = False
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a credential value
        
        Args:
            key: Credential key (e.g., 'OANDA_API_KEY')
            default: Default value if not found
            
        Returns:
            The credential value or default
        """
        if self.use_secret_manager and self.secret_manager:
            try:
                # Convert env var name to secret name (lowercase with hyphens)
                secret_name = key.lower().replace('_', '-')
                return self.secret_manager.get_secret(secret_name)
            except Exception as e:
                print(f"⚠ Could not get secret '{key}': {e}")
                print(f"  Falling back to environment variable")
        
        # Fallback to environment variable (from .env file)
        return os.getenv(key, default)
    
    def get_all_trading_credentials(self) -> Dict[str, str]:
        """
        Get all trading system credentials
        
        Returns:
            Dictionary of all credentials
        """
        credentials = {
            # OANDA
            'OANDA_API_KEY': self.get('OANDA_API_KEY'),
            'OANDA_ENVIRONMENT': self.get('OANDA_ENVIRONMENT', 'practice'),
            'OANDA_BASE_URL': self.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com'),
            
            # Telegram
            'TELEGRAM_TOKEN': self.get('TELEGRAM_TOKEN'),
            'TELEGRAM_CHAT_ID': self.get('TELEGRAM_CHAT_ID'),
            
            # News APIs
            'ALPHA_VANTAGE_API_KEY': self.get('ALPHA_VANTAGE_API_KEY'),
            'MARKETAUX_API_KEY': self.get('MARKETAUX_API_KEY'),
            'NEWSDATA_API_KEY': self.get('NEWSDATA_API_KEY'),
            'FMP_API_KEY': self.get('FMP_API_KEY'),
            'POLYGON_API_KEY': self.get('POLYGON_API_KEY'),
            'TWELVE_DATA_API_KEY': self.get('TWELVE_DATA_API_KEY'),
            'NEWSAPI_KEY': self.get('NEWSAPI_KEY'),
            'GEMINI_API_KEY': self.get('GEMINI_API_KEY'),
            
            # Flask
            'FLASK_SECRET_KEY': self.get('FLASK_SECRET_KEY'),
            
            # Google Cloud
            'GOOGLE_CLOUD_PROJECT': self.get('GOOGLE_CLOUD_PROJECT'),
        }
        
        # Remove None values
        return {k: v for k, v in credentials.items() if v is not None}
    
    def set(self, key: str, value: str, force_overwrite: bool = False) -> bool:
        """
        Set a credential value
        
        Args:
            key: Credential key (e.g., 'OANDA_API_KEY')
            value: Credential value
            force_overwrite: If True, overwrite existing value
            
        Returns:
            True if successful, False otherwise
        """
        if self.use_secret_manager and self.secret_manager:
            try:
                # Convert env var name to secret name (lowercase with hyphens)
                secret_name = key.lower().replace('_', '-')
                
                # Check if secret exists
                try:
                    existing_value = self.secret_manager.get_secret(secret_name)
                    if existing_value and not force_overwrite:
                        print(f"⚠ Secret '{key}' already exists. Use force_overwrite=True to replace.")
                        return False
                except (ValueError, Exception):
                    # Secret doesn't exist, create it
                    pass
                
                # Update or create secret
                return self.secret_manager.update_secret(secret_name, value) or \
                       self.secret_manager.create_secret(secret_name, value)
            except Exception as e:
                print(f"⚠ Could not set secret '{key}' in Secret Manager: {e}")
                print(f"  Falling back to environment variable")
                # Fall through to environment variable handling
        
        # Fallback: Set environment variable
        os.environ[key] = value
        print(f"✓ Set credential '{key}' in environment")
        return True
    
    def test_credential(self, service: str, api_key: str = None) -> Dict[str, Any]:
        """
        Test a credential by making a test API call
        
        Args:
            service: Service name ('oanda', 'alpha_vantage', 'marketaux', 'telegram', 'gemini')
            api_key: API key to test (if None, uses stored credential)
            
        Returns:
            Dictionary with 'success', 'message', and optional 'data'
        """
        if not api_key:
            # Get the appropriate API key for the service
            key_map = {
                'oanda': 'OANDA_API_KEY',
                'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
                'marketaux': 'MARKETAUX_API_KEY',
                'newsdata': 'NEWSDATA_API_KEY',
                'fmp': 'FMP_API_KEY',
                'polygon': 'POLYGON_API_KEY',
                'twelve_data': 'TWELVE_DATA_API_KEY',
                'newsapi': 'NEWSAPI_KEY',
                'gemini': 'GEMINI_API_KEY',
                'telegram': 'TELEGRAM_TOKEN'
            }
            
            env_key = key_map.get(service.lower())
            if not env_key:
                return {'success': False, 'message': f'Unknown service: {service}'}
            
            api_key = self.get(env_key)
            if not api_key:
                return {'success': False, 'message': f'No API key found for {service}'}
        
        # Test the credential based on service
        try:
            if service.lower() == 'oanda':
                return self._test_oanda(api_key)
            elif service.lower() == 'alpha_vantage':
                return self._test_alpha_vantage(api_key)
            elif service.lower() == 'marketaux':
                return self._test_marketaux(api_key)
            elif service.lower() == 'telegram':
                token = api_key
                chat_id = self.get('TELEGRAM_CHAT_ID')
                return self._test_telegram(token, chat_id)
            elif service.lower() == 'gemini':
                return self._test_gemini(api_key)
            else:
                return {'success': False, 'message': f'Service {service} not yet implemented'}
        except Exception as e:
            return {'success': False, 'message': f'Test failed: {str(e)}'}
    
    def _test_oanda(self, api_key: str) -> Dict[str, Any]:
        """Test OANDA API connection"""
        import requests
        
        try:
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            account_id = os.getenv('PRIMARY_ACCOUNT', '101-004-30719775-008')
            
            # Use practice URL for testing
            base_url = os.getenv('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            url = f'{base_url}/v3/accounts/{account_id}'
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': f'OANDA connection successful',
                    'data': {
                        'account_id': data.get('account', {}).get('id'),
                        'balance': data.get('account', {}).get('balance'),
                        'currency': data.get('account', {}).get('currency')
                    }
                }
            else:
                return {
                    'success': False,
                    'message': f'OANDA returned status {response.status_code}: {response.text[:100]}'
                }
        except Exception as e:
            return {'success': False, 'message': f'OANDA test failed: {str(e)}'}
    
    def _test_alpha_vantage(self, api_key: str) -> Dict[str, Any]:
        """Test Alpha Vantage API connection"""
        import requests
        
        try:
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': 'EURUSD',
                'apikey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'Error Message' in data:
                    return {'success': False, 'message': f'Alpha Vantage error: {data["Error Message"]}'}
                elif 'Note' in data and 'API call frequency' in data['Note']:
                    return {'success': False, 'message': 'Alpha Vantage rate limit hit'}
                else:
                    return {'success': True, 'message': 'Alpha Vantage connection successful'}
            else:
                return {'success': False, 'message': f'Alpha Vantage returned status {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Alpha Vantage test failed: {str(e)}'}
    
    def _test_marketaux(self, api_key: str) -> Dict[str, Any]:
        """Test Marketaux API connection"""
        import requests
        
        try:
            url = 'https://api.marketaux.com/v1/news/all'
            params = {'api_token': api_key, 'markets': 'forex', 'limit': 1}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {'success': True, 'message': 'Marketaux connection successful'}
                else:
                    return {'success': False, 'message': f'Marketaux returned: {data.get("error", "unknown error")}'}
            else:
                return {'success': False, 'message': f'Marketaux returned status {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Marketaux test failed: {str(e)}'}
    
    def _test_telegram(self, token: str, chat_id: str) -> Dict[str, Any]:
        """Test Telegram bot"""
        import requests
        
        try:
            url = f'https://api.telegram.org/bot{token}/getMe'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    return {
                        'success': True,
                        'message': 'Telegram bot connection successful',
                        'data': {
                            'bot_name': bot_info.get('first_name'),
                            'username': bot_info.get('username'),
                            'chat_id': chat_id
                        }
                    }
                else:
                    return {'success': False, 'message': f'Telegram error: {data.get("description")}'}
            else:
                return {'success': False, 'message': f'Telegram returned status {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Telegram test failed: {str(e)}'}
    
    def _test_gemini(self, api_key: str) -> Dict[str, Any]:
        """Test Gemini AI API connection"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            response = model.generate_content('test')
            
            return {'success': True, 'message': 'Gemini AI connection successful'}
        except Exception as e:
            return {'success': False, 'message': f'Gemini test failed: {str(e)}'}
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics
        
        Returns:
            Dictionary with usage statistics for each API
        """
        stats = {
            'oanda': {
                'calls_today': 0,
                'daily_limit': 10000,
                'remaining': 10000,
                'percentage_used': 0.0,
                'status': 'green'
            },
            'alpha_vantage': {
                'calls_today': 0,
                'daily_limit': 500,
                'remaining': 500,
                'percentage_used': 0.0,
                'status': 'green'
            },
            'marketaux': {
                'calls_today': 0,
                'daily_limit': 1000,
                'remaining': 1000,
                'percentage_used': 0.0,
                'status': 'green'
            },
            'telegram': {
                'calls_today': 0,
                'daily_limit': 1000,
                'remaining': 1000,
                'percentage_used': 0.0,
                'status': 'green'
            },
            'gemini': {
                'calls_today': 0,
                'daily_limit': 1500,
                'remaining': 1500,
                'percentage_used': 0.0,
                'status': 'green'
            }
        }
        
        # TODO: Integrate with API usage tracker when available
        # This is a placeholder that returns default values
        # In production, this should pull real stats from the usage tracker
        
        return stats


# Singleton instance for easy import
_default_credentials_manager = None

def get_credentials_manager(use_secret_manager: bool = True, project_id: Optional[str] = None) -> CredentialsManager:
    """
    Get the default credentials manager instance
    
    Args:
        use_secret_manager: If True, use Google Cloud Secret Manager
        project_id: Google Cloud project ID
        
    Returns:
        CredentialsManager instance
    """
    global _default_credentials_manager
    if _default_credentials_manager is None:
        _default_credentials_manager = CredentialsManager(use_secret_manager, project_id)
    return _default_credentials_manager


