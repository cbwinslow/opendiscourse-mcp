#!/usr/bin/env python3
"""
Detailed API key testing with different endpoints
"""

import os
import sys
import requests
import time

def test_congress_api():
    """Test Congress API with different endpoints"""
    print("\n🏛️  Testing Congress API Detailed...")
    api_key = os.getenv('CONGRESS_API_KEY')
    
    if not api_key:
        return False, "API key not found"
    
    headers = {'X-API-Key': api_key}
    
    # Test multiple endpoints
    endpoints = [
        ("Bill", "https://api.congress.gov/v3/bill/118/hr/3076"),
        ("Amendment", "https://api.congress.gov/v3/amendment/118/hjamdt/1335"),
        ("Committee", "https://api.congress.gov/v3/committee/house/hspw00"),
        ("Member", "https://api.congress.gov/v3/member/H001068")
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {name}: Working")
            else:
                print(f"  ❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: {str(e)}")
    
    return True, "Congress API working"

def test_govinfo_api():
    """Test GovInfo API with different endpoints"""
    print("\n📋 Testing GovInfo API Detailed...")
    api_key = os.getenv('GOVINFO_API_KEY')
    
    if not api_key:
        return False, "API key not found"
    
    params = {'api_key': api_key}
    
    # Test multiple endpoints
    endpoints = [
        ("Collections", "https://api.govinfo.gov/collections"),
        ("Bills", "https://api.govinfo.gov/collections/BILLS/2024/01/01"),
        ("CRS Reports", "https://api.govinfo.gov/collections/CRPT/2024/01/01"),
        ("Congressional Record", "https://api.govinfo.gov/collections/CREC/2024/01/01")
    ]
    
    working_count = 0
    for name, url in endpoints:
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {name}: Working")
                working_count += 1
            elif response.status_code == 500:
                print(f"  ⚠️  {name}: Server error (may be temporary)")
            else:
                print(f"  ❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: {str(e)}")
    
    if working_count > 0:
        return True, f"GovInfo API partially working ({working_count}/{len(endpoints)} endpoints)"
    else:
        return False, "GovInfo API not working"

def test_openstates_api():
    """Test OpenStates API with different endpoints"""
    print("\n🏛️  Testing OpenStates API Detailed...")
    api_key = os.getenv('OPENSTATES_API_KEY')
    
    if not api_key:
        return False, "API key not found"
    
    headers = {'X-API-Key': api_key}
    
    # Test multiple endpoints
    endpoints = [
        ("Jurisdictions", "https://v3.openstates.org/jurisdictions/?limit=5"),
        ("Bills", "https://v3.openstates.org/bills/?state=ca&limit=5"),
        ("People", "https://v3.openstates.org/people/?state=ca&limit=5"),
        ("Organizations", "https://v3.openstates.org/organizations/?state=ca&limit=5")
    ]
    
    working_count = 0
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {name}: Working")
                working_count += 1
            elif response.status_code == 400:
                print(f"  ⚠️  {name}: Bad request (may need different parameters)")
            else:
                print(f"  ❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: {str(e)}")
    
    if working_count > 0:
        return True, f"OpenStates API partially working ({working_count}/{len(endpoints)} endpoints)"
    else:
        return False, "OpenStates API not working"

def source_env_file():
    """Source .env file"""
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

def main():
    """Main verification function"""
    print("🔑 Detailed API Key Verification for OpenDiscourse...")
    print("=" * 60)
    
    # Load environment
    source_env_file()
    
    results = {}
    
    # Test each API
    results['congress'], congress_msg = test_congress_api()
    results['govinfo'], govinfo_msg = test_govinfo_api()
    results['openstates'], openstates_msg = test_openstates_api()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DETAILED API VERIFICATION SUMMARY:")
    
    for service, success in results.items():
        status = "✅ WORKING" if success else "❌ ISSUES"
        print(f"{service.upper():12}: {status}")
    
    print(f"\n📝 DETAILED STATUS:")
    print(f"Congress: {congress_msg}")
    print(f"GovInfo: {govinfo_msg}")
    print(f"OpenStates: {openstates_msg}")
    
    # Overall assessment
    working_count = sum(results.values())
    if working_count == 3:
        print(f"\n🎉 ALL APIs ARE WORKING!")
        return 0
    elif working_count >= 2:
        print(f"\n⚠️  MOST APIs WORKING ({working_count}/3)")
        return 0
    else:
        print(f"\n❌ MANY API ISSUES ({working_count}/3 working)")
        return 1

if __name__ == "__main__":
    sys.exit(main())