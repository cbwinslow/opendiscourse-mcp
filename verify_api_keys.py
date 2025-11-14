#!/usr/bin/env python3
"""
Verify API keys for Congress, OpenStates, and GovInfo
"""

import os
import sys
import requests
import time

def test_api_key(api_key, base_url, service_name, test_endpoint=""):
    """Test an API key with a simple request"""
    if not api_key:
        return False, "API key not found"
    
    headers = {}
    params = {}
    
    # Configure authentication based on service
    if service_name.lower() == 'congress':
        headers['X-API-Key'] = api_key
        test_url = f"{base_url}/bill/118/hr/3076"  # Test with known bill
    elif service_name.lower() == 'govinfo':
        params['api_key'] = api_key
        test_url = f"{base_url}/collections/BILLS"  # Test bills collection
    elif service_name.lower() == 'openstates':
        headers['X-API-Key'] = api_key
        test_url = f"{base_url}/bills/?state=ca&limit=1"  # Test California bills
    else:
        return False, "Unknown service"
    
    try:
        print(f"  🔄 Testing {service_name} API...")
        response = requests.get(test_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return True, f"✅ Working (Status: {response.status_code})"
        elif response.status_code == 401:
            return False, f"❌ Invalid API key (Status: {response.status_code})"
        elif response.status_code == 403:
            return False, f"❌ Access forbidden (Status: {response.status_code})"
        elif response.status_code == 429:
            return False, f"⚠️ Rate limited (Status: {response.status_code})"
        else:
            return False, f"❌ HTTP Error (Status: {response.status_code})"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timeout"
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection error"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def verify_api_keys():
    """Verify all API keys"""
    print("🔑 Verifying API Keys for OpenDiscourse Services...")
    print("=" * 60)
    
    # Load environment variables
    source_env_file()
    
    results = {}
    
    # Test Congress API
    print("\n🏛️  Testing Congress API...")
    congress_key = os.getenv('CONGRESS_API_KEY')
    congress_url = "https://api.congress.gov/v3"
    success, message = test_api_key(congress_key, congress_url, "Congress")
    results['congress'] = {'success': success, 'message': message}
    print(f"  {message}")
    
    # Test GovInfo API
    print("\n📋 Testing GovInfo API...")
    govinfo_key = os.getenv('GOVINFO_API_KEY')
    govinfo_url = "https://api.govinfo.gov"
    success, message = test_api_key(govinfo_key, govinfo_url, "GovInfo")
    results['govinfo'] = {'success': success, 'message': message}
    print(f"  {message}")
    
    # Test OpenStates API
    print("\n🏛️  Testing OpenStates API...")
    openstates_key = os.getenv('OPENSTATES_API_KEY')
    openstates_url = "https://v3.openstates.org"
    success, message = test_api_key(openstates_key, openstates_url, "OpenStates")
    results['openstates'] = {'success': success, 'message': message}
    print(f"  {message}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 API KEY VERIFICATION SUMMARY:")
    
    all_success = True
    for service, result in results.items():
        status = "✅ WORKING" if result['success'] else "❌ ISSUES"
        print(f"{service.upper():12}: {status}")
        if not result['success']:
            all_success = False
    
    # Show API key status (masked)
    print(f"\n🔑 API KEY STATUS:")
    for service in ['congress', 'govinfo', 'openstates']:
        key_var = f"{service.upper()}_API_KEY"
        key_value = os.getenv(key_var)
        if key_value:
            masked = key_value[:8] + "..." + key_value[-4:] if len(key_value) > 12 else "***"
            print(f"  {key_var:20}: {masked}")
        else:
            print(f"  {key_var:20}: ❌ NOT SET")
    
    if all_success:
        print(f"\n🎉 ALL API KEYS ARE WORKING!")
        return 0
    else:
        print(f"\n❌ SOME API KEYS HAVE ISSUES")
        return 1

def source_env_file():
    """Source the .env file"""
    env_file = "/home/cbwinslow/opendiscourse/mcp_server/.env"
    if os.path.exists(env_file):
        print(f"📁 Loading environment from: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove export prefix if present
                    if key.startswith('export '):
                        key = key[7:]
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
    else:
        print(f"⚠️  Environment file not found: {env_file}")

if __name__ == "__main__":
    sys.exit(verify_api_keys())