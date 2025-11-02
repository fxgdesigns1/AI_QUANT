#!/usr/bin/env python3
"""
Configuration API Manager
Provides REST endpoints for managing API credentials from the dashboard
Centralized API configuration management with test and validation capabilities
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import Blueprint, jsonify, request
from functools import wraps

from .secret_manager import get_credentials_manager, CredentialsManager

logger = logging.getLogger(__name__)

# Create blueprint for configuration API endpoints
config_api_blueprint = Blueprint('config_api', __name__)

def mask_credential(value: Optional[str], show_last: int = 4) -> str:
    """
    Mask a credential value for safe display
    
    Args:
        value: The credential value
        show_last: Number of characters to show at the end
        
    Returns:
        Masked credential string
    """
    if not value:
        return "Not Set"
    
    if len(value) <= show_last:
        return "*" * len(value)
    
    return "*" * (len(value) - show_last) + value[-show_last:]

def validate_api_key(key: str, value: str) -> Dict[str, Any]:
    """
    Validate API key format
    
    Args:
        key: The credential key name
        value: The credential value to validate
        
    Returns:
        Dictionary with 'valid' boolean and 'message' string
    """
    if not value or not value.strip():
        return {'valid': False, 'message': 'API key cannot be empty'}
    
    value = value.strip()
    
    # Service-specific validation
    if 'OANDA_API_KEY' in key:
        # OANDA keys are typically long alphanumeric
        if len(value) < 50:
            return {'valid': False, 'message': 'OANDA API key seems too short'}
    
    elif 'ALPHA_VANTAGE' in key:
        # Alpha Vantage keys are typically short alphanumeric
        if len(value) < 10:
            return {'valid': False, 'message': 'Alpha Vantage API key seems too short'}
    
    elif 'MARKETAUX' in key:
        # Marketaux keys are typically medium length
        if len(value) < 20:
            return {'valid': False, 'message': 'Marketaux API key seems too short'}
    
    elif 'TELEGRAM' in key:
        # Telegram tokens follow pattern: NUMBER:STRING
        if ':' not in value:
            return {'valid': False, 'message': 'Telegram token should contain a colon'}
    
    elif 'GEMINI' in key:
        # Gemini keys are typically long alphanumeric
        if len(value) < 30:
            return {'valid': False, 'message': 'Gemini API key seems too short'}
    
    return {'valid': True, 'message': 'API key format looks valid'}

@config_api_blueprint.route('/api/config/credentials', methods=['GET'])
def get_credentials():
    """
    Get all API credentials (masked for security)
    
    Returns:
        JSON response with all credentials masked
    """
    try:
        credentials_mgr = get_credentials_manager()
        
        # Get all credentials
        all_creds = credentials_mgr.get_all_trading_credentials()
        
        # Organize by category
        response = {
            'oanda': {
                'api_key': mask_credential(all_creds.get('OANDA_API_KEY')),
                'environment': all_creds.get('OANDA_ENVIRONMENT', 'practice'),
                'base_url': all_creds.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com'),
                'is_set': bool(all_creds.get('OANDA_API_KEY'))
            },
            'news_apis': {
                'alpha_vantage': {
                    'api_key': mask_credential(all_creds.get('ALPHA_VANTAGE_API_KEY')),
                    'is_set': bool(all_creds.get('ALPHA_VANTAGE_API_KEY'))
                },
                'marketaux': {
                    'api_key': mask_credential(all_creds.get('MARKETAUX_API_KEY')),
                    'is_set': bool(all_creds.get('MARKETAUX_API_KEY'))
                },
                'newsdata': {
                    'api_key': mask_credential(all_creds.get('NEWSDATA_API_KEY')),
                    'is_set': bool(all_creds.get('NEWSDATA_API_KEY'))
                },
                'fmp': {
                    'api_key': mask_credential(all_creds.get('FMP_API_KEY')),
                    'is_set': bool(all_creds.get('FMP_API_KEY'))
                },
                'polygon': {
                    'api_key': mask_credential(all_creds.get('POLYGON_API_KEY')),
                    'is_set': bool(all_creds.get('POLYGON_API_KEY'))
                },
                'twelve_data': {
                    'api_key': mask_credential(all_creds.get('TWELVE_DATA_API_KEY')),
                    'is_set': bool(all_creds.get('TWELVE_DATA_API_KEY'))
                },
                'newsapi': {
                    'api_key': mask_credential(all_creds.get('NEWSAPI_KEY')),
                    'is_set': bool(all_creds.get('NEWSAPI_KEY'))
                }
            },
            'telegram': {
                'token': mask_credential(all_creds.get('TELEGRAM_TOKEN')),
                'chat_id': mask_credential(all_creds.get('TELEGRAM_CHAT_ID'), show_last=6),
                'is_set': bool(all_creds.get('TELEGRAM_TOKEN'))
            },
            'gemini': {
                'api_key': mask_credential(all_creds.get('GEMINI_API_KEY')),
                'is_set': bool(all_creds.get('GEMINI_API_KEY'))
            },
            'cloud': {
                'project_id': all_creds.get('GOOGLE_CLOUD_PROJECT', 'Not Set'),
                'is_set': bool(all_creds.get('GOOGLE_CLOUD_PROJECT'))
            }
        }
        
        return jsonify({
            'success': True,
            'credentials': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting credentials: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/credentials/<key>', methods=['GET'])
def get_credential(key: str):
    """
    Get a specific credential (masked)
    
    Args:
        key: The credential key name
        
    Returns:
        JSON response with the credential value (masked)
    """
    try:
        credentials_mgr = get_credentials_manager()
        value = credentials_mgr.get(key)
        
        return jsonify({
            'success': True,
            'key': key,
            'value': mask_credential(value),
            'is_set': bool(value),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting credential {key}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/credentials/<key>', methods=['PUT'])
def update_credential(key: str):
    """
    Update a credential
    
    Args:
        key: The credential key name
        
    Request body:
        {
            'value': 'new_credential_value',
            'validate': true  # optional, default true
        }
        
    Returns:
        JSON response with success status
    """
    try:
        data = request.json
        if not data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: value'
            }), 400
        
        new_value = data['value']
        validate = data.get('validate', True)
        
        # Validate the credential
        if validate:
            validation_result = validate_api_key(key, new_value)
            if not validation_result['valid']:
                return jsonify({
                    'success': False,
                    'error': validation_result['message']
                }), 400
        
        # Update the credential
        credentials_mgr = get_credentials_manager()
        force_overwrite = data.get('force_overwrite', False)
        success = credentials_mgr.set(key, new_value, force_overwrite=force_overwrite)
        
        if success:
            logger.info(f"Credential {key} updated successfully")
            return jsonify({
                'success': True,
                'message': f'Credential {key} updated successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to update credential {key}. It may already exist.'
            }), 400
    
    except Exception as e:
        logger.error(f"Error updating credential {key}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/test/<service>', methods=['POST'])
def test_credential(service: str):
    """
    Test a service credential
    
    Args:
        service: Service name (oanda, alpha_vantage, marketaux, telegram, gemini)
        
    Request body (optional):
        {
            'api_key': 'test_api_key'  # if not provided, uses stored credential
        }
        
    Returns:
        JSON response with test results
    """
    try:
        data = request.json or {}
        test_key = data.get('api_key')
        
        credentials_mgr = get_credentials_manager()
        result = credentials_mgr.test_credential(service, api_key=test_key)
        
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Test completed'),
            'data': result.get('data'),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error testing service {service}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/usage', methods=['GET'])
def get_usage():
    """
    Get API usage statistics
    
    Returns:
        JSON response with usage stats for all APIs
    """
    try:
        credentials_mgr = get_credentials_manager()
        stats = credentials_mgr.get_usage_stats()
        
        return jsonify({
            'success': True,
            'usage': stats,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/test-multiple', methods=['POST'])
def test_multiple_credentials():
    """
    Test multiple services at once
    
    Request body:
        {
            'services': ['oanda', 'alpha_vantage', 'marketaux', 'telegram', 'gemini']
        }
        
    Returns:
        JSON response with test results for all requested services
    """
    try:
        data = request.json or {}
        services = data.get('services', ['oanda', 'alpha_vantage', 'marketaux', 'telegram', 'gemini'])
        
        credentials_mgr = get_credentials_manager()
        results = {}
        
        for service in services:
            results[service] = credentials_mgr.test_credential(service)
        
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error testing multiple credentials: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_api_blueprint.route('/api/config/validate', methods=['POST'])
def validate_credential():
    """
    Validate a credential format without setting it
    
    Request body:
        {
            'key': 'OANDA_API_KEY',
            'value': 'credential_value'
        }
        
    Returns:
        JSON response with validation result
    """
    try:
        data = request.json
        if not data or 'key' not in data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: key, value'
            }), 400
        
        key = data['key']
        value = data['value']
        
        validation_result = validate_api_key(key, value)
        
        return jsonify({
            'success': True,
            'valid': validation_result['valid'],
            'message': validation_result['message'],
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error validating credential: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_config_api(app):
    """
    Register the config API blueprint with a Flask app
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(config_api_blueprint)
    logger.info("✅ Configuration API registered")


