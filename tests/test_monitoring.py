"""
Tests for the monitoring and deduplication system.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from mcp_server.utils.monitoring import IngestionMonitor, DeduplicationManager, monitor, deduplicator


class TestIngestionMonitor:
    """Test the ingestion monitoring functionality."""

    def test_create_job(self):
        """Test creating a new ingestion job."""
        monitor = IngestionMonitor()

        job_id = monitor.create_job(
            source='test_source',
            collection='test_collection',
            test_param='test_value'
        )

        assert job_id.startswith('test_source_test_collection_')
        assert job_id in monitor.jobs

        job = monitor.jobs[job_id]
        assert job.source == 'test_source'
        assert job.collection == 'test_collection'
        assert job.status == 'pending'
        assert job.metadata['test_param'] == 'test_value'

    def test_monitor_job_context_manager(self):
        """Test the job monitoring context manager."""
        monitor = IngestionMonitor()

        job_id = monitor.create_job('test', 'test')

        with monitor.monitor_job(job_id):
            job = monitor.jobs[job_id]
            assert job.status == 'running'

        job = monitor.jobs[job_id]
        assert job.status == 'completed'
        assert job.end_time is not None

    def test_monitor_job_with_exception(self):
        """Test job monitoring when an exception occurs."""
        monitor = IngestionMonitor()

        job_id = monitor.create_job('test', 'test')

        with pytest.raises(ValueError):
            with monitor.monitor_job(job_id):
                raise ValueError("Test error")

        job = monitor.jobs[job_id]
        assert job.status == 'failed'
        assert len(job.errors) == 1
        assert 'Test error' in job.errors[0]

    def test_update_progress(self):
        """Test updating job progress."""
        monitor = IngestionMonitor()

        job_id = monitor.create_job('test', 'test')
        monitor.update_progress(job_id, 100, 5)

        job = monitor.jobs[job_id]
        assert job.processed_records == 100
        assert job.duplicates_found == 5

    def test_get_job_status(self):
        """Test retrieving job status."""
        monitor = IngestionMonitor()

        job_id = monitor.create_job('test', 'test')
        status = monitor.get_job_status(job_id)

        assert status is not None
        assert status['job_id'] == job_id
        assert status['status'] == 'pending'

    def test_get_all_jobs(self):
        """Test retrieving all jobs."""
        monitor = IngestionMonitor()

        job1_id = monitor.create_job('source1', 'collection1')
        job2_id = monitor.create_job('source2', 'collection2')

        all_jobs = monitor.get_all_jobs()
        assert len(all_jobs) == 2

        running_jobs = monitor.get_all_jobs(status='pending')
        assert len(running_jobs) == 2

    def test_invalid_job_id(self):
        """Test handling of invalid job IDs."""
        monitor = IngestionMonitor()

        with pytest.raises(ValueError):
            with monitor.monitor_job('invalid_job_id'):
                pass

        status = monitor.get_job_status('invalid_job_id')
        assert status is None


class TestDeduplicationManager:
    """Test the deduplication functionality."""

    def test_content_hash_generation(self):
        """Test content hash generation."""
        deduplicator = DeduplicationManager()

        data1 = {'field1': 'value1', 'field2': 'value2'}
        data2 = {'field1': 'value1', 'field2': 'value2'}
        data3 = {'field1': 'value1', 'field2': 'different'}

        hash1 = deduplicator.get_content_hash(data1)
        hash2 = deduplicator.get_content_hash(data2)
        hash3 = deduplicator.get_content_hash(data3)

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex length

    def test_content_hash_with_exclusions(self):
        """Test content hash generation with field exclusions."""
        deduplicator = DeduplicationManager()

        data = {'field1': 'value1', 'field2': 'value2', 'exclude': 'this'}

        hash1 = deduplicator.get_content_hash(data)
        hash2 = deduplicator.get_content_hash(data, exclude_fields=['exclude'])

        assert hash1 != hash2

    @patch('psycopg2.connect')
    def test_duplicate_check_without_db(self, mock_connect):
        """Test duplicate checking when database is not available."""
        deduplicator = DeduplicationManager()

        # Without database URL, should return False (not duplicate)
        is_dup = deduplicator.is_duplicate('test_table', 'test_hash', 'test_id')
        assert is_dup is False

    @patch('psycopg2.connect')
    def test_duplicate_check_with_db(self, mock_connect):
        """Test duplicate checking with database connection."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # No existing hash
        mock_connect.return_value = mock_conn

        deduplicator = DeduplicationManager(db_url='postgresql://test')

        is_dup = deduplicator.is_duplicate('test_table', 'test_hash', 'test_id')

        assert is_dup is False
        # Verify database operations were called
        mock_cur.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_cur.close.assert_called()
        mock_conn.close.assert_called()

    @patch('psycopg2.connect')
    def test_duplicate_found(self, mock_connect):
        """Test when a duplicate is found."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = (1,)  # Hash exists
        mock_connect.return_value = mock_conn

        deduplicator = DeduplicationManager(db_url='postgresql://test')

        is_dup = deduplicator.is_duplicate('test_table', 'test_hash', 'test_id')

        assert is_dup is True

    @patch('psycopg2.connect')
    def test_cleanup_old_hashes(self, mock_connect):
        """Test cleanup of old hash records."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.rowcount = 5  # 5 records deleted
        mock_connect.return_value = mock_conn

        deduplicator = DeduplicationManager(db_url='postgresql://test')

        deduplicator.cleanup_old_hashes(days=30)

        # Verify cleanup query was executed
        mock_cur.execute.assert_called_with(
            "DELETE FROM record_hashes\n                WHERE created_at < NOW() - INTERVAL '%s days'",
            (30,)
        )


class TestGlobalInstances:
    """Test the global monitor and deduplicator instances."""

    def test_global_instances_exist(self):
        """Test that global instances are properly initialized."""
        assert isinstance(monitor, IngestionMonitor)
        assert isinstance(deduplicator, DeduplicationManager)

    def test_global_monitor_functionality(self):
        """Test that the global monitor works."""
        job_id = monitor.create_job('test', 'test')
        assert job_id in monitor.jobs

        status = monitor.get_job_status(job_id)
        assert status is not None
        assert status['status'] == 'pending'


if __name__ == '__main__':
    pytest.main([__file__])
