#!/usr/bin/env python3
"""Test Congress API client"""

import os
from dotenv import load_dotenv
from mcp_server.clients.congress_client import CongressClient

# Load environment variables
load_dotenv(dotenv_path='mcp_server/.env')

def test_api():
    api_key = os.getenv('CONGRESS_API_KEY')
    if not api_key:
        print("No CONGRESS_API_KEY found")
        return

    client = CongressClient(api_key=api_key)

    try:
        # Test basic API call
        print("Testing Congress API...")

        # Test committees endpoint
        print("Testing committees endpoint...")
        result = client.list_committees(congress=118, chamber='house')
        print(f"Committees API response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        if 'committees' in result:
            print(f"Found {len(result['committees'])} committees")
            if result['committees']:
                print(f"Sample committee: {result['committees'][0].get('name', 'Unknown')}")

    except Exception as e:
        print(f"API test failed: {e}")

if __name__ == "__main__":
    test_api()
