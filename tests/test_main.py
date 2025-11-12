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
