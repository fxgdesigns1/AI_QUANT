#!/usr/bin/env python3
"""
Find Gemini API Key - Search all possible locations
"""
import os
import sys
import json

def check_env_vars():
    """Check environment variables"""
    print("\n🔍 Checking Environment Variables...")
    key = os.getenv('GEMINI_API_KEY')
    if key:
        print(f"✅ Found in environment: {key[:10]}...{key[-10:]}")
        return key
    else:
        print("❌ Not found in environment variables")
        return None

def check_env_files():
    """Check .env files"""
    print("\n🔍 Checking .env files...")
    env_files = [
        '.env',
        '.env.production',
        'oanda_config.env',
        'news_api_config.env',
        '../.env',
        '../.env.production'
    ]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'GEMINI' in content.upper():
                        print(f"✅ Found GEMINI reference in {env_file}")
                        for line in content.split('\n'):
                            if 'GEMINI' in line.upper() and '=' in line:
                                key_part = line.split('=')[1].strip()
                                if key_part and len(key_part) > 10:
                                    print(f"   Key found: {key_part[:10]}...{key_part[-10:]}")
                                    return key_part
            except Exception as e:
                print(f"   ⚠️ Error reading {env_file}: {e}")
    
    print("❌ Not found in .env files")
    return None

def check_secret_manager():
    """Check Google Cloud Secret Manager"""
    print("\n🔍 Checking Google Cloud Secret Manager...")
    try:
        from google.cloud import secretmanager
        from google.api_core import exceptions
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT') or 'ai-quant-trading'
        print(f"   Project ID: {project_id}")
        
        client = secretmanager.SecretManagerServiceClient()
        
        # Try different secret name variations
        secret_names = ['gemini-api-key', 'GEMINI_API_KEY', 'gemini_api_key', 'GEMINI-KEY']
        
        for secret_name in secret_names:
            try:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                key = response.payload.data.decode('UTF-8')
                print(f"✅ Found in Secret Manager: {secret_name}")
                print(f"   Key: {key[:10]}...{key[-10:]}")
                return key
            except exceptions.NotFound:
                continue
            except Exception as e:
                print(f"   ⚠️ Error checking {secret_name}: {e}")
        
        print("❌ Not found in Secret Manager")
        return None
        
    except ImportError:
        print("⚠️ google-cloud-secret-manager not installed")
        print("   Install with: pip install google-cloud-secret-manager")
        return None
    except Exception as e:
        print(f"❌ Error accessing Secret Manager: {e}")
        return None

def check_config_files():
    """Check configuration files"""
    print("\n🔍 Checking configuration files...")
    config_files = [
        'app.yaml',
        'app.yaml.backup',
        'ALL_CREDENTIALS_FOR_SECRET_MANAGER.json',
        '../ALL_CREDENTIALS_FOR_SECRET_MANAGER.json'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'GEMINI' in content.upper():
                        print(f"✅ Found GEMINI reference in {config_file}")
                        # Try to extract key
                        if config_file.endswith('.json'):
                            data = json.loads(content)
                            # Search recursively
                            def find_key(obj, path=""):
                                if isinstance(obj, dict):
                                    for k, v in obj.items():
                                        if 'gemini' in k.lower() and 'key' in k.lower():
                                            if isinstance(v, str) and len(v) > 10:
                                                print(f"   Found: {k} = {v[:10]}...{v[-10:]}")
                                                return v
                                        elif isinstance(v, (dict, list)):
                                            result = find_key(v, f"{path}.{k}")
                                            if result:
                                                return result
                                elif isinstance(obj, list):
                                    for item in obj:
                                        result = find_key(item, path)
                                        if result:
                                            return result
                                return None
                            
                            key = find_key(data)
                            if key:
                                return key
            except Exception as e:
                print(f"   ⚠️ Error reading {config_file}: {e}")
    
    print("❌ Not found in configuration files")
    return None

def main():
    print("=" * 60)
    print("🔍 GEMINI API KEY SEARCH")
    print("=" * 60)
    
    found_key = None
    
    # Check all locations
    found_key = check_env_vars() or found_key
    found_key = check_env_files() or found_key
    found_key = check_config_files() or found_key
    found_key = check_secret_manager() or found_key
    
    print("\n" + "=" * 60)
    if found_key:
        print("✅ GEMINI API KEY FOUND!")
        print(f"   Key: {found_key[:15]}...{found_key[-15:]}")
        print("\n💡 To configure it:")
        print("   1. Add to app.yaml environment variables:")
        print(f"      GEMINI_API_KEY: \"{found_key}\"")
        print("   2. Or upload to Secret Manager:")
        print("      Secret name: gemini-api-key")
    else:
        print("❌ GEMINI API KEY NOT FOUND")
        print("\n💡 To get a Gemini API key:")
        print("   1. Go to https://makersuite.google.com/app/apikey")
        print("   2. Create a new API key")
        print("   3. Add it to Google Cloud Secret Manager:")
        print("      gcloud secrets create gemini-api-key --data-file=-")
        print("   4. Or add to app.yaml:")
        print("      GEMINI_API_KEY: \"your-key-here\"")
    print("=" * 60)

if __name__ == '__main__':
    main()



