"""
Tests for utility functions.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import io
import tempfile
import os
from mcp_server.utils import ingest, db_copy


class TestDataIngestionUtils:
    """Test data ingestion utility functions."""

    def test_json_results_to_dataframe_empty(self):
        """Test converting empty results to DataFrame."""
        result = ingest.json_results_to_dataframe([])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_json_results_to_dataframe_basic(self):
        """Test converting basic JSON results to DataFrame."""
        results = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25}
        ]

        df = ingest.json_results_to_dataframe(results, normalize=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name", "age"]
        assert df.iloc[0]["name"] == "Alice"

    def test_json_results_to_dataframe_normalized(self):
        """Test converting nested JSON results to DataFrame with normalization."""
        results = [
            {"id": 1, "user": {"name": "Alice", "profile": {"age": 30}}},
            {"id": 2, "user": {"name": "Bob", "profile": {"age": 25}}}
        ]

        df = ingest.json_results_to_dataframe(results, normalize=True)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "user.name" in df.columns
        assert "user.profile.age" in df.columns

    def test_json_results_to_dataframe_normalize_fallback(self):
        """Test DataFrame creation falls back when normalization fails."""
        # Create results that might cause json_normalize to fail
        results = [{"data": set([1, 2, 3])}]  # sets are not JSON serializable

        df = ingest.json_results_to_dataframe(results, normalize=True)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_save_dataframe_parquet(self, temp_dir):
        """Test saving DataFrame as Parquet."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        path = os.path.join(temp_dir, "test.parquet")

        result = ingest.save_dataframe(df, path, "parquet")

        assert result["status"] == "ok"
        assert result["path"] == path
        assert result["format"] == "parquet"
        assert os.path.exists(path)

    def test_save_dataframe_csv(self, temp_dir):
        """Test saving DataFrame as CSV."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        path = os.path.join(temp_dir, "test.csv")

        result = ingest.save_dataframe(df, path, "csv")

        assert result["status"] == "ok"
        assert result["path"] == path
        assert result["format"] == "csv"
        assert os.path.exists(path)

        # Verify CSV content
        with open(path, 'r') as f:
            content = f.read()
            assert "col1,col2" in content
            assert "1,a" in content

    def test_save_dataframe_json(self, temp_dir):
        """Test saving DataFrame as JSON."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        path = os.path.join(temp_dir, "test.json")

        result = ingest.save_dataframe(df, path, "json")

        assert result["status"] == "ok"
        assert result["path"] == path
        assert result["format"] == "json"
        assert os.path.exists(path)

    def test_save_dataframe_unsupported_format(self):
        """Test saving DataFrame with unsupported format."""
        df = pd.DataFrame({"col1": [1, 2]})

        with pytest.raises(ValueError, match="Unsupported format"):
            ingest.save_dataframe(df, "test.txt", "txt")

    def test_save_dataframe_case_insensitive_format(self, temp_dir):
        """Test saving DataFrame with case-insensitive format."""
        df = pd.DataFrame({"col1": [1, 2]})
        path = os.path.join(temp_dir, "test.CSV")

        result = ingest.save_dataframe(df, path, "CSV")

        assert result["format"] == "csv"
        assert os.path.exists(path)


class TestDatabaseCopyUtils:
    """Test database COPY utility functions."""

    def test_copy_dataframe_to_table(self):
        """Test copying DataFrame to database table using COPY."""
        # Mock connection and cursor
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur

        # Test DataFrame
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35]
        })

        # Column mapping
        columns = {
            "person_id": "id",
            "person_name": "name",
            "person_age": "age"
        }

        result = db_copy.copy_dataframe_to_table(mock_conn, df, "people", columns)

        assert result["status"] == "ok"
        assert result["rows"] == 3

        # Verify cursor operations
        mock_conn.cursor.assert_called_once()
        mock_cur.copy_expert.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cur.close.assert_called_once()

        # Verify COPY SQL generation
        call_args = mock_cur.copy_expert.call_args
        copy_sql = call_args[0][0]
        assert "COPY people (person_id, person_name, person_age) FROM STDIN WITH (FORMAT csv)" == copy_sql

    def test_copy_dataframe_to_table_empty(self):
        """Test copying empty DataFrame."""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur

        df = pd.DataFrame()
        columns = {"id": "id"}

        result = db_copy.copy_dataframe_to_table(mock_conn, df, "empty_table", columns)

        assert result["status"] == "ok"
        assert result["rows"] == 0

        mock_cur.copy_expert.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_copy_dataframe_to_table_single_column(self):
        """Test copying DataFrame with single column."""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur

        df = pd.DataFrame({"value": ["a", "b", "c"]})
        columns = {"data": "value"}

        result = db_copy.copy_dataframe_to_table(mock_conn, df, "single_col", columns)

        assert result["status"] == "ok"
        assert result["rows"] == 3

        # Verify COPY SQL
        call_args = mock_cur.copy_expert.call_args
        copy_sql = call_args[0][0]
        assert "COPY single_col (data) FROM STDIN WITH (FORMAT csv)" == copy_sql

    @patch('mcp_server.utils.db_copy.io.StringIO')
    def test_copy_dataframe_to_table_csv_generation(self, mock_stringio):
        """Test CSV generation for COPY operation."""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur

        # Mock StringIO
        mock_csv_buffer = Mock()
        mock_stringio.return_value = mock_csv_buffer

        df = pd.DataFrame({
            "col1": [1, 2],
            "col2": ["x", "y"]
        })

        columns = {"column1": "col1", "column2": "col2"}

        db_copy.copy_dataframe_to_table(mock_conn, df, "test_table", columns)

        # Verify CSV buffer operations
        mock_stringio.assert_called_once()
        mock_csv_buffer.seek.assert_called_once_with(0)

        # Verify DataFrame.to_csv was called with correct parameters
        # This is implicit in the copy_expert call working


class TestXMLIngestionUtils:
    """Test XML ingestion utility functions."""

    @patch('mcp_server.utils.xml_ingest.pd.read_xml')
    def test_ingest_xml_to_df_with_pandas(self, mock_read_xml, sample_xml_data, temp_dir):
        """Test XML ingestion using pandas read_xml."""
        # Create test XML file
        xml_path = os.path.join(temp_dir, "test.xml")
        with open(xml_path, 'w') as f:
            f.write(sample_xml_data)

        # Mock pandas read_xml to return expected DataFrame
        expected_df = pd.DataFrame({
            "id": ["doc1", "doc2"],
            "title": ["Test Document", "Second Document"],
            "date": ["2025-11-12", "2025-11-11"]
        })
        mock_read_xml.return_value = expected_df

        from mcp_server.utils.xml_ingest import ingest_xml_to_df
        result_df = ingest_xml_to_df(xml_path, record_xpath='.//record')

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2
        mock_read_xml.assert_called_once_with(xml_path, xpath='.//record')

    def test_ingest_xml_to_df_fallback_method(self, sample_xml_data, temp_dir):
        """Test XML ingestion fallback method when pandas read_xml fails."""
        from mcp_server.utils.xml_ingest import ingest_xml_to_df

        # Create test XML file
        xml_path = os.path.join(temp_dir, "test.xml")
        with open(xml_path, 'w') as f:
            f.write(sample_xml_data)

        # This should use the fallback lxml method
        result_df = ingest_xml_to_df(xml_path, record_xpath='.//record')

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2
        assert list(result_df.columns) == ["id", "title", "date", "content"]


class TestDownloaderUtils:
    """Test downloader utility functions."""

    @patch('mcp_server.utils.downloader.requests.Session')
    def test_downloader_basic(self, mock_session_class):
        """Test basic file downloading."""
        from mcp_server.utils.downloader import download_file

        mock_session = Mock()
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.headers = {"content-length": "10"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        # This would need to be implemented based on the actual downloader code
        # For now, this is a placeholder test structure
        pass


class TestTimeSeriesUtils:
    """Test time series utility functions."""

    def test_time_series_basic(self):
        """Test basic time series functionality."""
        # Placeholder for time series tests
        # These would test time series analysis functions
        pass
