#!/usr/bin/env python3
"""Manual test runner to check test functionality."""

import sys
import traceback
from fastapi.testclient import TestClient
from mcp_server.main import app

def run_token_registration_tests():
    """Run token registration tests manually."""
    print("Running token registration tests...")

    client = TestClient(app)

    # Test successful registration
    try:
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "site": "congress",
            "user_id": "test_user"
        }
        print("✓ test_register_token_success passed")
    except Exception as e:
        print(f"✗ test_register_token_success failed: {e}")
        traceback.print_exc()

    # Test unknown site
    try:
        response = client.post("/mcp/register_token", json={
            "site": "unknown",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 400
        assert "Unknown site" in response.json()["detail"]
        print("✓ test_register_token_unknown_site passed")
    except Exception as e:
        print(f"✗ test_register_token_unknown_site failed: {e}")
        traceback.print_exc()

    # Test missing fields
    try:
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user"
        })
        assert response.status_code == 422  # Pydantic validation error
        print("✓ test_register_token_missing_fields passed")
    except Exception as e:
        print(f"✗ test_register_token_missing_fields failed: {e}")
        traceback.print_exc()

def run_function_execution_tests():
    """Run function execution tests manually."""
    print("\nRunning function execution tests...")

    client = TestClient(app)

    # Register token first
    client.post("/mcp/register_token", json={
        "site": "congress",
        "user_id": "test_user",
        "api_key": "test_key"
    })

    # Test no token
    try:
        response = client.post("/mcp/execute", json={
            "user_id": "no_token_user",
            "site": "congress",
            "function": "search_bills",
            "args": {}
        })
        assert response.status_code == 401
        assert "No API key registered" in response.json()["detail"]
        print("✓ test_execute_function_no_token passed")
    except Exception as e:
        print(f"✗ test_execute_function_no_token failed: {e}")
        traceback.print_exc()

    # Test unknown function
    try:
        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "unknown_function",
            "args": {}
        })
        assert response.status_code == 400
        assert "Unknown function" in response.json()["detail"]
        print("✓ test_execute_function_unknown_function passed")
    except Exception as e:
        print(f"✗ test_execute_function_unknown_function failed: {e}")
        traceback.print_exc()

def run_list_functions_test():
    """Run list functions test."""
    print("\nRunning list functions test...")

    client = TestClient(app)

    try:
        response = client.get("/mcp/functions")
        assert response.status_code == 200
        data = response.json()
        assert "congress" in data
        assert "openstates" in data
        assert "govinfo" in data
        assert isinstance(data["congress"], list)
        print("✓ test_list_functions passed")
    except Exception as e:
        print(f"✗ test_list_functions failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting manual test run...")
    run_token_registration_tests()
    run_function_execution_tests()
    run_list_functions_test()
    print("\nManual test run completed.")
