"""
Google Cloud Secret Manager Integration
Securely manages sensitive credentials for mobile and cloud access
"""
import os
import json
from typing import Optional, Dict, Any
from google.cloud import secretmanager
from google.api_core import exceptions

class SecretManager:
    """Manages credentials via Google Cloud Secret Manager"""
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Secret Manager
        
        Args:
            project_id: Google Cloud project ID. If None, will try to get from environment
        """
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

