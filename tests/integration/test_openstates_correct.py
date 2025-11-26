#!/usr/bin/env python3
"""
Test OpenStates API with correct format
"""

import os
import requests

def test_openstates_correct():
    """Test OpenStates with correct API format"""
    print("🏛️  Testing OpenStates API with correct format...")
    api_key = os.getenv('OPENSTATES_API_KEY')
    
    if not api_key:
        print("❌ API key not found")
        return False
    
    headers = {
        'X-API-Key': api_key,
        'Accept': 'application/json'
    }
    
    # Test with correct OpenStates v3 endpoints
    endpoints = [
        ("Jurisdictions", "https://v3.openstates.org/jurisdictions"),
        ("California Bills", "https://v3.openstates.org/bills?jurisdiction=California&limit=5"),
        ("Recent Bills", "https://v3.openstates.org/bills?limit=5"),
        ("People", "https://v3.openstates.org/people?limit=5")
    ]
    
    working_count = 0
    for name, url in endpoints:
        try:
            print(f"  🔄 Testing {name}...")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"    Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'results' in data or 'pagination' in data:
                    print(f"  ✅ {name}: Working ({len(data.get('results', []))} results)")
                    working_count += 1
                else:
                    print(f"  ⚠️  {name}: Unexpected response format")
            else:
                print(f"  ❌ {name}: Failed - {response.text[:100]}")
                
        except Exception as e:
            print(f"  ❌ {name}: Error - {str(e)}")
    
    return working_count > 0

def source_env_file():
    """Source .env file"""
    env_file = "/home/cbwinslow/opendiscourse/mcp_server/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

if __name__ == "__main__":
    source_env_file()
    success = test_openstates_correct()
    print(f"\nOpenStates API: {'✅ Working' if success else '❌ Issues'}")