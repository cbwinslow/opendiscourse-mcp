#!/usr/bin/env python3
"""Basic test to check if the MCP server works."""

from fastapi.testclient import TestClient
from mcp_server.main import app

def test_basic():
    try:
        client = TestClient(app)
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        print("Basic test passed!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic()
