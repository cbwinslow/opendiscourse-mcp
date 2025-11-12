"""
Shared test fixtures and configuration for MCP Server tests.
"""
import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Generator
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def sample_xml_data():
    """Sample XML data for testing."""
    return '''<?xml version="1.0"?>
<root>
  <record>
    <id>doc1</id>
    <title>Test Document</title>
    <date>2025-11-12</date>
    <content>Sample content</content>
  </record>
  <record>
    <id>doc2</id>
    <title>Second Document</title>
    <date>2025-11-11</date>
    <content>More content</content>
  </record>
</root>
'''


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "bills": [
            {
                "billType": "hr",
                "billNumber": "1",
                "title": "Test Bill",
                "latestAction": {
                    "actionCode": "1000",
                    "description": "Introduced"
                }
            }
        ]
    }


@pytest.fixture
def mock_http_session():
    """Mock HTTP session for API testing."""
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "success"}
    response.text = "mock response"
    response.status_code = 200
    session.get.return_value = response
    session.post.return_value = response
    return session


@pytest.fixture
def mock_congress_api_response():
    """Mock Congress.gov API response."""
    return {
        "bills": [
            {
                "billType": "hr",
                "billNumber": "1234",
                "title": "Test Bill Title",
                "latestAction": {
                    "actionCode": "1000",
                    "description": "Introduced in House"
                },
                "sponsors": [{"bioguideId": "T000001"}]
            }
        ]
    }


@pytest.fixture
def mock_openstates_api_response():
    """Mock OpenStates API response."""
    return {
        "results": [
            {
                "id": "ocd-bill/test-123",
                "identifier": "HB 123",
                "title": "Test Bill",
                "classification": ["bill"],
                "subject": ["Test Subject"],
                "latest_action_date": "2025-01-01",
                "latest_action_description": "Introduced"
            }
        ]
    }


@pytest.fixture
def mock_govinfo_api_response():
    """Mock GovInfo API response."""
    return {
        "collections": [
            {
                "collectionCode": "BILLS",
                "collectionName": "Congressional Bills",
                "packageCount": 1000
            }
        ]
    }


@pytest.fixture
def sqlite_db():
    """Create a temporary SQLite database for testing."""
    db_fd, db_path = tempfile.mkstemp()
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def postgres_db_url():
    """Mock PostgreSQL database URL."""
    return "postgresql://test:test@localhost:5432/test_db"


@pytest.fixture
def mock_postgres_connection(postgres_db_url):
    """Mock PostgreSQL connection."""
    conn = Mock()
    conn.cursor.return_value.__enter__ = Mock()
    conn.cursor.return_value.__exit__ = Mock()
    conn.cursor.return_value.execute = Mock()
    conn.cursor.return_value.fetchall.return_value = [("test", "data")]
    conn.cursor.return_value.description = [("column1",), ("column2",)]
    return conn


@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame for testing."""
    return pd.DataFrame({
        "id": ["doc1", "doc2", "doc3"],
        "title": ["Doc 1", "Doc 2", "Doc 3"],
        "date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "content": ["Content 1", "Content 2", "Content 3"]
    })


@pytest.fixture
def api_keys():
    """Sample API keys for testing."""
    return {
        "congress": "test_congress_key",
        "openstates": "test_openstates_key",
        "govinfo": "test_govinfo_key"
    }


@pytest.fixture
def mock_env_vars(api_keys):
    """Set up mock environment variables."""
    original_env = dict(os.environ)
    os.environ.update({
        "CONGRESS_API_KEY": api_keys["congress"],
        "OPENSTATES_API_KEY": api_keys["openstates"],
        "GOVINFO_API_KEY": api_keys["govinfo"],
        "DATABASE_URL": "sqlite:///test.db"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing CLI commands."""
    with pytest.mock.patch('subprocess.run') as mock_run:
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "Command executed successfully"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        yield mock_run


@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings."""
    return {
        "timeout": 30,
        "max_retries": 3,
        "batch_size": 100,
        "parallel_workers": 2
    }


@pytest.fixture
def mock_gpu_processor():
    """Mock GPU processor for testing."""
    processor = Mock()
    processor.process_dataframe = Mock(return_value=pd.DataFrame({"processed": [True]}))
    processor.is_available = Mock(return_value=False)
    return processor


@pytest.fixture
def mock_scheduler():
    """Mock task scheduler."""
    scheduler = Mock()
    scheduler.add_scheduled_job = Mock(return_value="job_123")
    scheduler.get_scheduled_jobs = Mock(return_value=[])
    scheduler.remove_scheduled_job = Mock(return_value=True)
    return scheduler


@pytest.fixture
def mock_remote_executor():
    """Mock remote executor for distributed testing."""
    executor = Mock()
    executor.execute_remote = Mock(return_value={"status": "success"})
    executor.sync_files = Mock(return_value=True)
    return executor


@pytest.fixture
def ingestion_config():
    """Sample ingestion configuration."""
    return {
        "use_gpu": False,
        "use_parallel": False,
        "enable_deduplication": False,
        "batch_size": 100,
        "max_workers": 4
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger
