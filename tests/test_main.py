"""
Tests for the main MCP Server FastAPI application.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from mcp_server.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


class TestTokenRegistration:
    """Test API token registration endpoints."""

    def test_register_token_success(self, client):
        """Test successful token registration."""
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

    def test_register_token_unknown_site(self, client):
        """Test registration with unknown site."""
        response = client.post("/mcp/register_token", json={
            "site": "unknown",
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 400
        assert "Unknown site" in response.json()["detail"]

    def test_register_token_missing_fields(self, client):
        """Test registration with missing required fields."""
        # Missing api_key
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user"
        })
        assert response.status_code == 422  # Pydantic validation error

        # Missing site
        response = client.post("/mcp/register_token", json={
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 422

    def test_register_token_empty_api_key(self, client):
        """Test registration with empty API key."""
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": ""
        })
        assert response.status_code == 200  # Should still work, empty keys allowed

    def test_register_token_case_insensitive_site(self, client):
        """Test registration with case-insensitive site names."""
        response = client.post("/mcp/register_token", json={
            "site": "CONGRESS",  # Uppercase
            "user_id": "test_user",
            "api_key": "test_key"
        })
        assert response.status_code == 200
        assert response.json()["site"] == "congress"  # Should be lowercased

    def test_register_token_duplicate_registration(self, client):
        """Test registering the same site twice for same user."""
        # First registration
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        # Second registration should overwrite
        response = client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "new_test_key"
        })
        assert response.status_code == 200


class TestFunctionExecution:
    """Test function execution endpoints."""

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_execute_function_success(self, mock_client_class, client):
        """Test successful function execution."""
        # Register token first
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        # Mock client
        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": []}
        mock_client_class.return_value = mock_client

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "search_bills",
            "args": {"congress": 118}
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_client.search_bills.assert_called_once_with(congress=118)

    def test_execute_function_no_token(self, client):
        """Test function execution without registered token."""
        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "search_bills",
            "args": {}
        })

        assert response.status_code == 401
        assert "No API key registered" in response.json()["detail"]

    def test_execute_function_unknown_site(self, client):
        """Test function execution with unknown site."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "unknown",
            "function": "search_bills",
            "args": {}
        })

        assert response.status_code == 400
        assert "Unknown site" in response.json()["detail"]

    def test_execute_function_unknown_function(self, client):
        """Test function execution with unknown function."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "unknown_function",
            "args": {}
        })

        assert response.status_code == 400
        assert "Unknown function" in response.json()["detail"]

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_execute_function_with_exception(self, mock_client_class, client):
        """Test function execution that raises an exception."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        mock_client = Mock()
        mock_client.search_bills.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "search_bills",
            "args": {}
        })

        assert response.status_code == 500
        assert "Function execution failed" in response.json()["detail"]

    def test_execute_function_missing_args(self, client):
        """Test function execution with missing required arguments."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress"
            # Missing function and args
        })

        assert response.status_code == 422  # Pydantic validation error

    def test_execute_function_empty_args(self, client):
        """Test function execution with empty args dict."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "congress",
            "function": "search_bills",
            "args": None  # Should handle None args
        })

        assert response.status_code == 422  # Should still validate

    @patch('mcp_server.clients.congress_client.CongressClient')
    def test_execute_function_different_sites(self, mock_client_class, client):
        """Test function execution with different API sites."""
        # Test with OpenStates
        client.post("/mcp/register_token", json={
            "site": "openstates",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        mock_client = Mock()
        mock_client.search_bills.return_value = {"results": []}
        mock_client_class.return_value = mock_client

        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "openstates",
            "function": "search_bills",
            "args": {"jurisdiction": "us"}
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_execute_function_wrong_site_token(self, client):
        """Test function execution with token registered for different site."""
        # Register for congress
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        # Try to execute with openstates
        response = client.post("/mcp/execute", json={
            "user_id": "test_user",
            "site": "openstates",
            "function": "search_bills",
            "args": {}
        })

        assert response.status_code == 401
        assert "No API key registered" in response.json()["detail"]


class TestDataIngestion:
    """Test data ingestion endpoints."""

    @patch('subprocess.run')
    def test_ingest_data_success(self, mock_subprocess, client):
        """Test successful data ingestion."""
        # Register token
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "Ingestion completed"
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
        assert "Ingestion completed" in response.json()["message"]

    @patch('subprocess.run')
    def test_ingest_data_failure(self, mock_subprocess, client):
        """Test failed data ingestion."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Ingestion failed"
        mock_subprocess.return_value = mock_process

        response = client.post("/mcp/ingest_data", json={
            "user_id": "test_user",
            "site": "congress",
            "database_url": "postgresql://test:test@localhost/testdb"
        })

        assert response.status_code == 500
        assert "Ingestion failed" in response.json()["detail"]

    def test_ingest_data_unknown_site(self, client):
        """Test ingestion with unknown site."""
        client.post("/mcp/register_token", json={
            "site": "congress",
            "user_id": "test_user",
            "api_key": "test_key"
        })

        response = client.post("/mcp/ingest_data", json={
            "user_id": "test_user",
            "site": "unknown",
            "database_url": "postgresql://test:test@localhost/testdb"
        })

        assert response.status_code == 400
        assert "No ingestion script" in response.json()["detail"]


class TestDataQuery:
    """Test data query endpoints."""

    @patch('psycopg2.connect')
    def test_query_data_success(self, mock_connect, client, sample_dataframe):
        """Test successful data query."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",), ("date",)]
        mock_cursor.fetchall.return_value = [
            ("doc1", "Doc 1", "2025-01-01"),
            ("doc2", "Doc 2", "2025-01-02")
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "limit": 100
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 2

    @patch('psycopg2.connect')
    def test_query_data_with_where(self, mock_connect, client):
        """Test data query with WHERE clause."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("doc1", "Doc 1")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "where_clause": "id = 'doc1'",
            "limit": 10
        })

        assert response.status_code == 200
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "WHERE id = 'doc1'" in call_args

    @patch('psycopg2.connect')
    def test_query_data_with_order_by(self, mock_connect, client):
        """Test data query with ORDER BY clause."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("doc1", "Doc 1")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "order_by": "id DESC",
            "limit": 10
        })

        assert response.status_code == 200
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY id DESC" in call_args

    @patch('psycopg2.connect')
    def test_query_data_database_error(self, mock_connect, client):
        """Test data query with database connection error."""
        mock_connect.side_effect = Exception("Database connection failed")

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "limit": 100
        })

        assert response.status_code == 500
        assert "Query failed" in response.json()["detail"]

    def test_query_data_missing_fields(self, client):
        """Test data query with missing required fields."""
        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb"
            # Missing table
        })

        assert response.status_code == 422  # Pydantic validation error

    @patch('psycopg2.connect')
    def test_query_data_empty_result(self, mock_connect, client):
        """Test data query that returns no results."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = []  # Empty result
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/query_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "limit": 100
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 0


class TestDataExport:
    """Test data export endpoints."""

    @patch('psycopg2.connect')
    @patch('mcp_server.utils.ingest.save_dataframe')
    def test_export_data_success(self, mock_save, mock_connect, client, sample_dataframe):
        """Test successful data export."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("doc1", "Doc 1")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "format": "csv"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_save.assert_called_once()

    @patch('psycopg2.connect')
    @patch('mcp_server.utils.ingest.save_dataframe')
    def test_export_data_with_where_clause(self, mock_save, mock_connect, client):
        """Test data export with WHERE clause."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("doc1", "Doc 1")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "where_clause": "status = 'active'",
            "format": "json"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_save.assert_called_once()

    @patch('psycopg2.connect')
    @patch('mcp_server.utils.ingest.save_dataframe')
    def test_export_data_custom_output_path(self, mock_save, mock_connect, client):
        """Test data export with custom output path."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = [("doc1", "Doc 1")]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "format": "xlsx",
            "output_path": "/custom/path/export.xlsx"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["file"] == "/custom/path/export.xlsx"
        mock_save.assert_called_once()

    @patch('psycopg2.connect')
    def test_export_data_database_error(self, mock_connect, client):
        """Test data export with database connection error."""
        mock_connect.side_effect = Exception("Database connection failed")

        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "format": "csv"
        })

        assert response.status_code == 500
        assert "Export failed" in response.json()["detail"]

    def test_export_data_missing_fields(self, client):
        """Test data export with missing required fields."""
        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb"
            # Missing table
        })

        assert response.status_code == 422  # Pydantic validation error

    @patch('psycopg2.connect')
    @patch('mcp_server.utils.ingest.save_dataframe')
    def test_export_data_empty_result(self, mock_save, mock_connect, client):
        """Test data export with no data."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("title",)]
        mock_cursor.fetchall.return_value = []  # Empty result
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.post("/mcp/export_data", json={
            "user_id": "test_user",
            "database_url": "postgresql://test:test@localhost/testdb",
            "table": "test_table",
            "format": "csv"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["records"] == 0
        mock_save.assert_called_once()


class TestListFunctions:
    """Test function listing endpoints."""

    def test_list_functions(self, client):
        """Test listing available functions."""
        response = client.get("/mcp/functions")

        assert response.status_code == 200
        data = response.json()
        assert "congress" in data
        assert "openstates" in data
        assert "govinfo" in data
        assert isinstance(data["congress"], list)


class TestDataModel:
    """Test data model endpoints."""

    def test_get_data_model(self, client):
        """Test getting data model schema."""
        response = client.get("/mcp/data_model")

        assert response.status_code == 200
        data = response.json()
        assert "congress_bills" in data
        assert "openstates_bills" in data
        assert "govinfo_documents" in data

        # Check schema structure
        bills_schema = data["congress_bills"]
        assert "id" in bills_schema
        assert "congress" in bills_schema


class TestMonitoringEndpoints:
    """Test monitoring and health check endpoints."""

    @patch('mcp_server.main.monitor')
    def test_get_ingestion_jobs(self, mock_monitor, client):
        """Test getting all ingestion jobs."""
        mock_monitor.get_all_jobs.return_value = [
            {"job_id": "job1", "status": "completed"},
            {"job_id": "job2", "status": "running"}
        ]

        response = client.get("/mcp/ingestion/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["job_id"] == "job1"
        mock_monitor.get_all_jobs.assert_called_once_with(None)

    @patch('mcp_server.main.monitor')
    def test_get_ingestion_jobs_with_status_filter(self, mock_monitor, client):
        """Test getting ingestion jobs filtered by status."""
        mock_monitor.get_all_jobs.return_value = [
            {"job_id": "job1", "status": "completed"}
        ]

        response = client.get("/mcp/ingestion/jobs?status=completed")

        assert response.status_code == 200
        mock_monitor.get_all_jobs.assert_called_once_with("completed")

    @patch('mcp_server.main.monitor')
    def test_get_ingestion_job(self, mock_monitor, client):
        """Test getting a specific ingestion job."""
        mock_monitor.get_job_status.return_value = {
            "job_id": "job1",
            "status": "completed",
            "progress": 100
        }

        response = client.get("/mcp/ingestion/jobs/job1")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job1"
        assert data["status"] == "completed"
        mock_monitor.get_job_status.assert_called_once_with("job1")

    @patch('mcp_server.main.monitor')
    def test_get_ingestion_job_not_found(self, mock_monitor, client):
        """Test getting a non-existent ingestion job."""
        mock_monitor.get_job_status.return_value = None

        response = client.get("/mcp/ingestion/jobs/nonexistent")

        assert response.status_code == 404
        assert "Job nonexistent not found" in response.json()["detail"]

    @patch('mcp_server.main.monitor')
    def test_start_ingestion_job(self, mock_monitor, client):
        """Test starting a new ingestion job."""
        mock_monitor.create_job.return_value = "job123"

        response = client.post("/mcp/ingestion/start", json={
            "source": "congress",
            "collection": "bills",
            "api_key": "test_key"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job123"
        assert data["status"] == "created"
        mock_monitor.create_job.assert_called_once_with(
            "congress", "bills", api_key="test_key"
        )

    @patch('mcp_server.main.monitor')
    def test_start_ingestion_job_failure(self, mock_monitor, client):
        """Test starting ingestion job with failure."""
        mock_monitor.create_job.side_effect = Exception("Creation failed")

        response = client.post("/mcp/ingestion/start", json={
            "source": "congress",
            "collection": "bills"
        })

        assert response.status_code == 500
        assert "Failed to create job" in response.json()["detail"]

    @patch('mcp_server.main.deduplicator')
    def test_cleanup_old_data(self, mock_deduplicator, client):
        """Test cleanup of old ingestion data."""
        response = client.delete("/mcp/ingestion/cleanup?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Cleaned up data older than 30 days" in data["message"]
        mock_deduplicator.cleanup_old_hashes.assert_called_once_with(30)

    @patch('mcp_server.main.deduplicator')
    def test_cleanup_old_data_failure(self, mock_deduplicator, client):
        """Test cleanup failure."""
        mock_deduplicator.cleanup_old_hashes.side_effect = Exception("Cleanup failed")

        response = client.delete("/mcp/ingestion/cleanup")

        assert response.status_code == 500
        assert "Cleanup failed" in response.json()["detail"]

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/mcp/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
