#!/usr/bin/env python3
"""
Test API endpoints directly
"""

import os
import requests

def test_api_endpoints():
    """Test API endpoints directly"""
    print("🌐 Testing API Endpoints Directly...")
    
    source_env_file()
    
    # Test Congress API
    print("\n🏛️  Testing Congress API Endpoints...")
    api_key = os.getenv('CONGRESS_API_KEY')
    headers = {'X-API-Key': api_key}
    
    endpoints = [
        ("Bill v3", "https://api.congress.gov/v3/bill/118/hr/3076"),
        ("Bill v2", "https://api.congress.gov/v3/bill"),
        ("Search", "https://api.congress.gov/v3/bill?congress=118&limit=1")
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  {name:15}: Status {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if 'bill' in data:
                    print(f"                  ✅ Bill data found")
                elif 'bills' in data:
                    print(f"                  ✅ Bills list found ({len(data['bills'])} items)")
                else:
                    print(f"                  ⚠️  Unexpected format")
        except Exception as e:
            print(f"  {name:15}: Error - {str(e)}")

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
    test_api_endpoints()