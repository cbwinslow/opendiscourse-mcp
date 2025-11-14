#!/usr/bin/env python3
"""
Final comprehensive API key verification
"""

import os
import sys
import requests

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

def verify_all_apis():
    """Final comprehensive API verification"""
    print("🔑 FINAL API KEY VERIFICATION")
    print("=" * 50)
    
    source_env_file()
    
    results = {}
    
    # Test Congress API
    print("\n🏛️  CONGRESS API")
    congress_key = os.getenv('CONGRESS_API_KEY')
    if congress_key:
        try:
            headers = {'X-API-Key': congress_key}
            response = requests.get("https://api.congress.gov/v3/bill/118/hr/3076", 
                                   headers=headers, timeout=10)
            if response.status_code == 200:
                print("  ✅ Working - Bill data accessible")
                results['congress'] = True
            else:
                print(f"  ❌ Error - Status {response.status_code}")
                results['congress'] = False
        except Exception as e:
            print(f"  ❌ Error - {str(e)}")
            results['congress'] = False
    else:
        print("  ❌ API key not found")
        results['congress'] = False
    
    # Test GovInfo API
    print("\n📋 GOVINFO API")
    govinfo_key = os.getenv('GOVINFO_API_KEY')
    if govinfo_key:
        try:
            params = {'api_key': govinfo_key}
            response = requests.get("https://api.govinfo.gov/collections", 
                                   params=params, timeout=10)
            if response.status_code == 200:
                print("  ✅ Working - Collections accessible")
                results['govinfo'] = True
            else:
                print(f"  ❌ Error - Status {response.status_code}")
                results['govinfo'] = False
        except Exception as e:
            print(f"  ❌ Error - {str(e)}")
            results['govinfo'] = False
    else:
        print("  ❌ API key not found")
        results['govinfo'] = False
    
    # Test OpenStates API
    print("\n🏛️  OPENSTATES API")
    openstates_key = os.getenv('OPENSTATES_API_KEY')
    if openstates_key:
        try:
            headers = {'X-API-Key': openstates_key}
            response = requests.get("https://v3.openstates.org/jurisdictions", 
                                   headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"  ✅ Working - {count} jurisdictions accessible")
                results['openstates'] = True
            else:
                print(f"  ❌ Error - Status {response.status_code}")
                results['openstates'] = False
        except Exception as e:
            print(f"  ❌ Error - {str(e)}")
            results['openstates'] = False
    else:
        print("  ❌ API key not found")
        results['openstates'] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL VERIFICATION SUMMARY:")
    
    working_count = 0
    for service, status in results.items():
        status_text = "✅ WORKING" if status else "❌ FAILED"
        print(f"{service.upper():12}: {status_text}")
        if status:
            working_count += 1
    
    print(f"\n🎯 OVERALL STATUS: {working_count}/3 APIs working")
    
    # API Key Security Check
    print(f"\n🔑 API KEY SECURITY STATUS:")
    for service in ['CONGRESS', 'GOVINFO', 'OPENSTATES']:
        key_var = f"{service}_API_KEY"
        key_value = os.getenv(key_var)
        if key_value:
            if len(key_value) >= 12:
                masked = key_value[:4] + "*" * (len(key_value) - 8) + key_value[-4:]
                print(f"  {key_var:20}: ✅ Present and masked ({len(key_value)} chars)")
            else:
                print(f"  {key_var:20}: ⚠️  Too short ({len(key_value)} chars)")
        else:
            print(f"  {key_var:20}: ❌ Missing")
    
    if working_count == 3:
        print(f"\n🎉 ALL API KEYS VERIFIED AND WORKING!")
        print("✅ Ready for data ingestion")
        return 0
    elif working_count >= 2:
        print(f"\n⚠️  {working_count}/3 APIs working - Partial functionality available")
        return 0
    else:
        print(f"\n❌ Only {working_count}/3 APIs working - Major issues")
        return 1

if __name__ == "__main__":
    sys.exit(verify_all_apis())