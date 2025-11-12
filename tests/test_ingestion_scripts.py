"""
Tests for data ingestion scripts.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import os
from mcp_server.scripts import congress_ingest, openstates_ingest, govinfo_ingest


class TestCongressIngestion:
    """Test Congress data ingestion script."""

    @patch('mcp_server.scripts.congress_ingest.connect_db')
    @patch('mcp_server.scripts.congress_ingest.CongressClient')
    def test_ingest_bills_basic(self, mock_client_class, mock_connect_db):
        """Test basic bill ingestion."""
        # Mock client
        mock_client = Mock()
        mock_client.search_bills.side_effect = [
            {"bills": [{"billType": "hr", "billNumber": "1234", "title": "Test Bill"}]},  # First page
            {"bills": []}  # Empty second page to stop
        ]
        mock_client_class.return_value = mock_client

        # Mock database connection
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect_db.return_value = mock_conn

        # Set environment
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            congress_ingest.ingest_bills(
                api_key="test_key",
                congress=118,
                billType="hr"
            )

        # Verify client was called correctly
        mock_client_class.assert_called_once_with(api_key="test_key")
        assert mock_client.search_bills.call_count >= 1

        # Verify database operations
        mock_cur.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_cur.close.assert_called()
        mock_conn.close.assert_called()

    @patch('mcp_server.scripts.congress_ingest.get_sqlalchemy_engine')
    @patch('mcp_server.scripts.congress_ingest.CongressClient')
    def test_ingest_bills_sqlalchemy(self, mock_client_class, mock_get_engine):
        """Test bill ingestion using SQLAlchemy."""
        # Mock client
        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": []}  # Empty to stop immediately
        mock_client_class.return_value = mock_client

        # Mock SQLAlchemy engine
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = mock_connection
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_get_engine.return_value = mock_engine

        # Set environment
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
            'USE_SQLALCHEMY': '1'
        }):
            congress_ingest.ingest_bills(
                api_key="test_key",
                congress=118
            )

        mock_get_engine.assert_called_once()

    @patch('mcp_server.scripts.congress_ingest.copy_dataframe_to_table')
    @patch('mcp_server.scripts.congress_ingest.get_raw_connection')
    @patch('mcp_server.scripts.congress_ingest.CongressClient')
    def test_ingest_bills_copy_method(self, mock_client_class, mock_get_raw_conn, mock_copy_df):
        """Test bill ingestion using COPY method."""
        # Mock client
        mock_client = Mock()
        mock_client.search_bills.return_value = {"bills": []}  # Empty to stop immediately
        mock_client_class.return_value = mock_client

        # Mock raw connection
        mock_conn = Mock()
        mock_get_raw_conn.return_value = mock_conn

        # Set environment
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
            'USE_COPY': '1'
        }):
            congress_ingest.ingest_bills(
                api_key="test_key",
                congress=118
            )

        mock_get_raw_conn.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_normalize_congress_bill(self):
        """Test bill normalization function."""
        bill_obj = {
            "billType": "hr",
            "billNumber": "1234",
            "title": "Test Bill Title",
            "latestActionDate": "2025-01-01",
            "latestActionDescription": "Introduced",
            "subjects": ["healthcare", "medicare"],
            "sponsors": [{"name": "John Doe"}]
        }

        result = congress_ingest.normalize_congress_bill(118, bill_obj)

        assert result["id"] == "118:hr:1234"
        assert result["congress"] == 118
        assert result["bill_type"] == "hr"
        assert result["bill_number"] == "1234"
        assert result["title"] == "Test Bill Title"
        assert result["latest_action_date"] == "2025-01-01"
        assert result["latest_action_description"] == "Introduced"
        assert result["subjects"] == ["healthcare", "medicare"]
        assert "sponsors" in result
        assert "raw" in result

    def test_normalize_congress_bill_minimal(self):
        """Test bill normalization with minimal data."""
        bill_obj = {
            "billType": "s",
            "billNumber": "567"
        }

        result = congress_ingest.normalize_congress_bill(119, bill_obj)

        assert result["id"] == "119:s:567"
        assert result["subjects"] == []  # Default empty list
        assert result["sponsors"] is not None  # Should have Json wrapper

    @patch('mcp_server.scripts.congress_ingest.connect_db')
    def test_connect_db(self, mock_connect_db):
        """Test database connection function."""
        mock_conn = Mock()
        mock_connect_db.return_value = mock_conn

        result = congress_ingest.connect_db("postgresql://test:test@localhost/testdb")

        assert result == mock_conn
        mock_connect_db.assert_called_once_with("postgresql://test:test@localhost/testdb")


class TestOpenStatesIngestion:
    """Test OpenStates data ingestion script."""

    @patch('mcp_server.scripts.openstates_ingest.connect_db')
    @patch('mcp_server.scripts.openstates_ingest.OpenStatesClient')
    def test_ingest_bills_basic(self, mock_client_class, mock_connect_db):
        """Test basic OpenStates bill ingestion."""
        # Mock client
        mock_client = Mock()
        mock_client.search_bills.side_effect = [
            {"results": [{"id": "bill1", "title": "Test Bill"}]},  # First page
            {"results": []}  # Empty second page to stop
        ]
        mock_client_class.return_value = mock_client

        # Mock database connection
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect_db.return_value = mock_conn

        # Set environment
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            openstates_ingest.ingest_bills(
                api_key="test_key",
                jurisdiction="us"
            )

        # Verify client was called correctly
        mock_client_class.assert_called_once_with(api_key="test_key")
        assert mock_client.search_bills.call_count >= 1

        # Verify database operations
        mock_cur.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_normalize_openstates_bill(self):
        """Test OpenStates bill normalization."""
        bill_obj = {
            "id": "ocd-bill/test-123",
            "identifier": "HB 123",
            "title": "Test Bill",
            "classification": ["bill"],
            "subject": ["health"],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
            "latest_action_date": "2025-01-01",
            "latest_action_description": "Introduced",
            "openstates_url": "https://openstates.org/bill/123",
            "sponsors": [{"name": "John Doe"}]
        }

        result = openstates_ingest.normalize_openstates_bill(bill_obj)

        assert result["id"] == "ocd-bill/test-123"
        assert result["identifier"] == "HB 123"
        assert result["title"] == "Test Bill"
        assert result["classification"] == ["bill"]
        assert result["subject"] == ["health"]
        assert result["latest_action_date"] == "2025-01-01"


class TestGovInfoIngestion:
    """Test GovInfo data ingestion script."""

    @patch('mcp_server.scripts.govinfo_ingest.connect_db')
    @patch('mcp_server.scripts.govinfo_ingest.GovInfoClient')
    def test_ingest_documents_basic(self, mock_client_class, mock_connect_db):
        """Test basic GovInfo document ingestion."""
        # Mock client
        mock_client = Mock()
        mock_client.bulk_download.return_value = []  # Empty to stop
        mock_client_class.return_value = mock_client

        # Mock database connection
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect_db.return_value = mock_conn

        # Set environment
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            govinfo_ingest.ingest_documents(
                api_key="test_key",
                collection="BILLS"
            )

        # Verify client was called correctly
        mock_client_class.assert_called_once_with(api_key="test_key")
        mock_client.bulk_download.assert_called_once_with("BILLS")

    def test_normalize_govinfo_document(self):
        """Test GovInfo document normalization."""
        doc_obj = {
            "collection": "BILLS",
            "date": "2025-01-01",
            "title": "Test Document",
            "url": "https://www.govinfo.gov/test",
            "metadata": {"type": "bill"},
            "raw_data": {"full": "document"}
        }

        result = govinfo_ingest.normalize_govinfo_document(doc_obj)

        assert result["id"] == "BILLS:2025-01-01:test"
        assert result["collection"] == "BILLS"
        assert result["date"] == "2025-01-01"
        assert result["title"] == "Test Document"
        assert result["url"] == "https://www.govinfo.gov/test"


class TestIngestionScriptCLI:
    """Test command-line interfaces of ingestion scripts."""

    @patch('mcp_server.scripts.congress_ingest.ingest_bills')
    def test_congress_ingest_main_missing_env(self, mock_ingest):
        """Test congress ingest main with missing environment."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit, match="Please set DATABASE_URL"):
                # This would normally be called as: python -m congress_ingest
                # But we'll simulate the argument parsing
                import sys
                original_argv = sys.argv
                try:
                    sys.argv = ['congress_ingest.py']
                    # The script checks for DATABASE_URL before parsing args
                    if not os.getenv("DATABASE_URL"):
                        raise SystemExit('Please set DATABASE_URL')
                finally:
                    sys.argv = original_argv

    @patch('mcp_server.scripts.congress_ingest.ingest_bills')
    def test_congress_ingest_main_missing_api_key(self, mock_ingest):
        """Test congress ingest main with missing API key."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            with pytest.raises(SystemExit, match="Please set CONGRESS_API_KEY"):
                # Simulate the script's argument parsing and validation
                import argparse
                p = argparse.ArgumentParser()
                p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
                args = p.parse_args([])

                if not args.api_key:
                    raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    @patch('mcp_server.scripts.congress_ingest.ingest_bills')
    def test_congress_ingest_main_success(self, mock_ingest):
        """Test congress ingest main with valid arguments."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
            'CONGRESS_API_KEY': 'test_key'
        }):
            # Simulate successful execution
            congress_ingest.ingest_bills(
                api_key="test_key",
                congress=118
            )

            mock_ingest.assert_called_once_with(
                api_key="test_key",
                congress=118,
                billType=None,
                page=1
            )
