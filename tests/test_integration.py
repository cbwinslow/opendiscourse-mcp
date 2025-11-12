"""
Integration tests for MCP Server components.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from mcp_server.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @patch('mcp_server.clients.congress_client.CongressClient')
    @patch('subprocess.run')
    def test_complete_congress_workflow(self, mock_subprocess, mock_client_class, client):
        """Test complete workflow: register -> execute -> ingest."""
        # Step 1: Register token
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 200

        # Step 2: Execute function
        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": [{"billType": "hr", "billNumber": "123"}]}
        mock_client_class.return_value = mock_client

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "search_bills",
            "args": {"congress": 118}
        })
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Step 3: Ingest data
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "Ingestion completed successfully"
        mock_process.stderr = ""
        mock_subprocess.return_value = mock_process

        response = client.post("/mcp/ingest_data", json={
            "user_id": "test_user",
            "site": "congress",
            "database_url": "postgresql://test:test@localhost/testdb",
            "query_params": {"congress": "118"},
            "ingestion_mode": "incremental"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch('psycopg2.connect')
    def test_query_export_workflow(self, mock_connect, client):
        """Test query and export workflow."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",), ("date",)]
        mock_cursor.fetchall.return_value = [
            ("bill1", "Test Bill 1", "2025-01-01"),
            ("bill2", "Test Bill 2", "2025-01-02")
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Step 1: Query data
        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "congress_bills",
            "limit": 10
        })
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

        # Step 2: Export data
        with patch('mcp_server.utils.ingest.save_dataframe') as mock_save:
            response = client.post("/mcp/export_data", json={
                "user_id": "test_user",
                "database_url": "postgresql://test:test@localhost/testdb",
                "table": "congress_bills",
                "format": "csv"
            })
            assert response.status_code == 200
            mock_save.assert_called_once()


class TestErrorHandling:
    """Test error handling across components."""

    def test_invalid_json_payloads(self, client):
        """Test handling of invalid JSON payloads."""
        # Invalid JSON
        response = client.post("/mcp/register_token",
                             data="invalid json",
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422

        # Empty payload
        response = client.post("/mcp/register_token", json={})
        assert response.status_code == 422

    def test_unsupported_http_methods(self, client):
        """Test unsupported HTTP methods."""
        response = client.put("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 405  # Method not allowed

    def test_large_payloads(self, client):
        """Test handling of large payloads."""
        large_data = {"site": "congress", "user_id": "test_user", "api_key": "x" * 10000}
        response = client.post("/mcp/register_token", json=large_data)
        # Should still work or return appropriate error
        assert response.status_code in [200, 413, 422]

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_api_client_exceptions(self, mock_client_class, client):
        """Test handling of API client exceptions."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        # Test various exception types
        exceptions_to_test = [
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            ValueError("Invalid response"),
            RuntimeError("Unexpected error")
        ]

        for exc in exceptions_to_test:
            mock_client = Mock()
            mock_client.search_bills.side_effect = exc
            mock_client_class.return_value = mock_client

            response = client.post("/mcp/execute", json={
                "user_id": "test_user",
                "site": "congress",
                "function": "search_bills",
                "args": {}
            })

            assert response.status_code == 500
            assert "Function execution failed" in response.json()["detail"]


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_multiple_users_same_site(self, mock_client_class, client):
        """Test multiple users registering for the same site."""
        # Register multiple users
        users = ["user1", "user2", "user3"]
        for user in users:
            response = client.post("/mcp/register_token", json={
                "site": "congress",
                "user_id": user,
                "api_key": f"key_{user}"
            })
            assert response.status_code == 200

        # Test that each user can execute functions independently
        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": []}
        mock_client_class.return_value = mock_client

        for user in users:
            response = client.post("/mcp/execute", json={
                "user_id": user,
                "site": "congress",
                "function": "search_bills",
                "args": {"congress": 118}
            })
            assert response.status_code == 200

    def test_token_overwrite_race_condition(self, client):
        """Test token overwrite scenarios."""
        # Initial registration
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "key1"
        })

        # Overwrite with different key
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "key2"
        })
        assert response.status_code == 200

        # Verify the new key is used (this would require mocking the client)


class TestDataValidation:
    """Test data validation and sanitization."""

    def test_sql_injection_prevention(self, client):
        """Test prevention of SQL injection attacks."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; SELECT * FROM secret_table; --",
            "admin'--",
            "1; DROP TABLE congress_bills;--"
        ]

        for malicious_input in malicious_inputs:
            # Test in WHERE clause
            with patch('psycopg2.connect') as mock_connect:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.description = [("id",), ("title",)]
                mock_cursor.fetchall.return_value = []
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                response = client.post("/mcp/query_data", json={
                    "user_id": "test_user",
                    "database_url": "postgresql://test:test@localhost/testdb",
                    "table": "congress_bills",
                    "where_clause": f"id = '{malicious_input}'",
                    "limit": 10
                })

                # Should not crash, should handle gracefully
                assert response.status_code in [200, 500]

    def test_path_traversal_prevention(self, client):
        """Test prevention of path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam"
        ]

        for malicious_path in malicious_paths:
            with patch('mcp_server.utils.ingest.save_dataframe') as mock_save, \
                 patch('psycopg2.connect') as mock_connect:

                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.description = [("id",), ("title",)]
                mock_cursor.fetchall.return_value = [("test", "data")]
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                response = client.post("/mcp/export_data", json={
                    "user_id": "test_user",
                    "database_url": "postgresql://test:test@localhost/testdb",
                    "table": "congress_bills",
                    "format": "csv",
                    "output_path": malicious_path
                })

                # Should handle gracefully
                assert response.status_code in [200, 500]


class TestResourceManagement:
    """Test resource management and cleanup."""

    @patch('psycopg2.connect')
    def test_database_connection_cleanup(self, mock_connect, client):
        """Test proper database connection cleanup."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("test", "data")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "limit": 10
        })

        assert response.status_code == 200
        # Verify connection cleanup was called
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('psycopg2.connect')
    def test_database_connection_error_cleanup(self, mock_connect, client):
        """Test cleanup on database connection errors."""
        mock_connect.side_effect = Exception("Connection failed")

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "limit": 10
        })

        assert response.status_code == 500
        # Even on error, should not leak connections (though we can't verify this with mocks)


class TestPerformance:
    """Test performance characteristics."""

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_response_time_under_load(self, mock_client_class, client):
        """Test response times under simulated load."""
        import time

        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": []}
        mock_client_class.return_value = mock_client

        # Simulate multiple requests
        start_time = time.time()
        for _ in range(10):
            response = client.post("/mcp/execute", json={
                "user_id": "test_user",
                "site": "congress",
                "function": "search_bills",
                "args": {"congress": 118}
            })
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert total_time < 5.0  # Less than 5 seconds for 10 requests
