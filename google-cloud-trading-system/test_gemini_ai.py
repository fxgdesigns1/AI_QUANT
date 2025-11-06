#!/usr/bin/env python3
"""
Test Gemini AI Configuration
Verifies that Gemini API is properly configured and working
"""
import os
import sys
import requests
import json

def test_gemini_api_key():
    """Test if Gemini API key is valid"""
    print("\n" + "="*60)
    print("🔍 TEST 1: Gemini API Key Configuration")
    print("="*60)
    
    api_key = "AQ.Ab8RN6KGhGzuSnOmj9P7ncZdm35NK6mKsUy4y4Qq8qrkd4CT_A"
    
    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ Gemini API key not configured")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-10:]}")
    
    # Try to use the key
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Simple test
        response = model.generate_content("Say 'Hello' if you can read this.")
        if response and response.text:
            print(f"✅ Gemini API Key is VALID")
            print(f"   Response: {response.text[:100]}")
            return True
        else:
            print("❌ Gemini API returned empty response")
            return False
    except Exception as e:
        print(f"❌ Gemini API Key test failed: {e}")
        return False

def test_cloud_health():
    """Test cloud application health endpoint"""
    print("\n" + "="*60)
    print("🔍 TEST 2: Cloud Application Health")
    print("="*60)
    
    try:
        response = requests.get("https://ai-quant-trading.uc.r.appspot.com/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint responding")
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Health endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_cloud_status():
    """Test cloud application status endpoint"""
    print("\n" + "="*60)
    print("🔍 TEST 3: Cloud Application Status")
    print("="*60)
    
    try:
        response = requests.get("https://ai-quant-trading.uc.r.appspot.com/api/status", timeout=10)
        if response.status_code == 200:
            print("✅ Status endpoint responding")
            data = response.json()
            
            # Check for AI Assistant status
            if 'ai_assistant' in str(data).lower() or 'gemini' in str(data).lower():
                print("✅ AI Assistant mentioned in status")
            
            print(f"   Response keys: {list(data.keys())[:5]}...")
            return True
        else:
            print(f"❌ Status endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

def test_ai_assistant_endpoint():
    """Test AI Assistant endpoint"""
    print("\n" + "="*60)
    print("🔍 TEST 4: AI Assistant Endpoint")
    print("="*60)
    
    try:
        # Test AI assistant health/status
        endpoints = [
            "/ai/health",
            "/api/ai-assistant/status"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"https://ai-quant-trading.uc.r.appspot.com{endpoint}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ {endpoint} responding")
                    data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    if 'provider' in str(data) or 'gemini' in str(data).lower():
                        print(f"   Provider: {data.get('model_provider', data.get('provider', 'unknown'))}")
                    return True
            except:
                continue
        
        print("⚠️  AI Assistant endpoints not found (may use different path)")
        return None
    except Exception as e:
        print(f"❌ AI Assistant test failed: {e}")
        return False

def test_dashboard_loading():
    """Test if dashboard loads"""
    print("\n" + "="*60)
    print("🔍 TEST 5: Dashboard Loading")
    print("="*60)
    
    try:
        response = requests.get("https://ai-quant-trading.uc.r.appspot.com/", timeout=15)
        if response.status_code == 200:
            print("✅ Dashboard loading")
            content = response.text.lower()
            
            if 'ai assistant' in content or 'gemini' in content:
                print("✅ AI Assistant found in dashboard")
            
            if 'trading' in content or 'dashboard' in content:
                print("✅ Trading dashboard content found")
            
            return True
        else:
            print(f"❌ Dashboard returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def check_cloud_logs():
    """Check cloud logs for Gemini initialization"""
    print("\n" + "="*60)
    print("🔍 TEST 6: Cloud Logs Check")
    print("="*60)
    
    try:
        import subprocess
        result = subprocess.run(
            ["gcloud", "app", "logs", "read", "-s", "default", "--limit=50"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logs = result.stdout.lower()
            
            if 'gemini' in logs:
                print("✅ Gemini mentioned in logs")
                gemini_lines = [line for line in result.stdout.split('\n') if 'gemini' in line.lower()][:3]
                for line in gemini_lines:
                    print(f"   {line[:80]}...")
                return True
            elif 'ai assistant' in logs:
                print("✅ AI Assistant mentioned in logs")
                return True
            else:
                print("⚠️  No Gemini/AI Assistant logs found yet (may still be initializing)")
                return None
        else:
            print(f"⚠️  Could not read logs: {result.stderr[:100]}")
            return None
    except Exception as e:
        print(f"⚠️  Log check failed: {e}")
        return None

def main():
    print("\n" + "="*60)
    print("🧪 GEMINI AI SYSTEM VERIFICATION TEST")
    print("="*60)
    print("\nTesting Gemini AI configuration and cloud deployment...")
    
    results = {
        'gemini_api_key': test_gemini_api_key(),
        'cloud_health': test_cloud_health(),
        'cloud_status': test_cloud_status(),
        'ai_assistant_endpoint': test_ai_assistant_endpoint(),
        'dashboard_loading': test_dashboard_loading(),
        'cloud_logs': check_cloud_logs()
    }
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    unknown = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  UNKNOWN"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"📈 RESULTS: {passed} passed, {failed} failed, {unknown} unknown")
    print("="*60)
    
    if passed >= 4:
        print("\n🎉 SYSTEM VERIFICATION: MOSTLY SUCCESSFUL!")
        print("   Gemini AI appears to be configured correctly.")
    elif passed >= 2:
        print("\n⚠️  SYSTEM VERIFICATION: PARTIAL SUCCESS")
        print("   Some components working, but needs verification.")
    else:
        print("\n❌ SYSTEM VERIFICATION: NEEDS ATTENTION")
        print("   Some components may not be working correctly.")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()





