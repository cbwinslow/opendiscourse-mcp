"""
Tests for database utilities.
"""
import pytest
from unittest.mock import Mock, patch
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection


class TestDatabaseEngine:
    """Test database engine creation and management."""

    @patch('mcp_server.db.create_engine')
    def test_get_sqlalchemy_engine_new(self, mock_create_engine):
        """Test creating a new SQLAlchemy engine."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Clear any cached engine
        import mcp_server.db
        mcp_server.db._engine = None

        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            engine = get_sqlalchemy_engine()

        assert engine == mock_engine
        mock_create_engine.assert_called_once_with('postgresql://test:test@localhost/testdb', future=True)

    @patch('mcp_server.db.create_engine')
    def test_get_sqlalchemy_engine_cached(self, mock_create_engine):
        """Test returning cached SQLAlchemy engine."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Set cached engine
        import mcp_server.db
        mcp_server.db._engine = mock_engine

        engine = get_sqlalchemy_engine()
        assert engine == mock_engine
        # Should not create new engine when cached
        mock_create_engine.assert_not_called()

    def test_get_sqlalchemy_engine_no_url(self):
        """Test engine creation without DATABASE_URL."""
        import mcp_server.db
        mcp_server.db._engine = None

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="DATABASE_URL not set"):
                get_sqlalchemy_engine()

    @patch('mcp_server.db.get_sqlalchemy_engine')
    def test_get_raw_connection(self, mock_get_engine):
        """Test getting raw database connection."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.raw_connection.return_value = mock_connection
        mock_get_engine.return_value = mock_engine

        conn = get_raw_connection()

        assert conn == mock_connection
        mock_engine.raw_connection.assert_called_once()

    @patch('mcp_server.db.get_sqlalchemy_engine')
    def test_get_raw_connection_with_url(self, mock_get_engine):
        """Test getting raw connection with specific URL."""
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.raw_connection.return_value = mock_connection
        mock_get_engine.return_value = mock_engine

        conn = get_raw_connection('sqlite:///test.db')

        assert conn == mock_connection
        mock_get_engine.assert_called_once_with(database_url='sqlite:///test.db')
