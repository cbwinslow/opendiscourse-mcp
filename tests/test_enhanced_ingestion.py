"""
Tests for enhanced ingestion system.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import asyncio
import pandas as pd
from mcp_server.utils.enhanced_ingestion import (
    IngestionJob,
    IngestionConfig,
    ProgressTracker,
    DeduplicationManager,
    GPUDataProcessor,
    ParallelProcessor,
    AsyncDataLoader,
    IngestionScheduler,
    RemoteExecutor,
    EnhancedIngestionManager,
    get_ingestion_manager
)


class TestIngestionJob:
    """Test IngestionJob dataclass."""

    def test_ingestion_job_creation(self):
        """Test creating an ingestion job."""
        job = IngestionJob(
            job_id="test_job_123",
            source="congress",
            collection="bills",
            parameters={"congress": 118}
        )

        assert job.job_id == "test_job_123"
        assert job.source == "congress"
        assert job.collection == "bills"
        assert job.status == "pending"
        assert job.progress == 0.0
        assert job.parameters == {"congress": 118}
        assert isinstance(job.created_at, datetime)


class TestIngestionConfig:
    """Test IngestionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = IngestionConfig()

        assert config.use_gpu is False
        assert config.use_parallel is True
        assert config.use_async is True
        assert config.max_workers is None
        assert config.batch_size == 1000
        assert config.enable_progress_tracking is True
        assert config.enable_deduplication is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = IngestionConfig(
            use_gpu=True,
            use_parallel=False,
            batch_size=500,
            enable_deduplication=False
        )

        assert config.use_gpu is True
        assert config.use_parallel is False
        assert config.batch_size == 500
        assert config.enable_deduplication is False


class TestProgressTracker:
    """Test progress tracking functionality."""

    def test_progress_tracker_local(self):
        """Test progress tracking without Redis."""
        tracker = ProgressTracker()

        tracker.update_progress("job_123", 50.0, 500, 1000)

        progress = tracker.get_progress("job_123")
        assert progress["progress"] == 50.0
        assert progress["processed"] == 500
        assert progress["total"] == 1000

    @patch('redis.from_url')
    def test_progress_tracker_redis(self, mock_redis_from_url):
        """Test progress tracking with Redis."""
        mock_redis = Mock()
        mock_redis_from_url.return_value = mock_redis

        tracker = ProgressTracker("redis://localhost:6379")

        tracker.update_progress("job_123", 75.0, 750, 1000)

        mock_redis.hset.assert_called_once_with(
            "ingestion:job_123",
            mapping={
                'progress': 75.0,
                'processed': 750,
                'total': 1000,
                'updated_at': pytest.any(str)
            }
        )

        tracker.get_progress("job_123")
        mock_redis.hgetall.assert_called_once_with("ingestion:job_123")


class TestDeduplicationManager:
    """Test deduplication functionality."""

    def test_deduplication_local(self):
        """Test deduplication without Redis."""
        dedup = DeduplicationManager()

        record = {"id": "test123", "data": "test"}

        # First time should not be duplicate
        assert not dedup.is_duplicate(record, "test_collection")

        # Mark as processed
        dedup.mark_processed(record, "test_collection")

        # Second time should be duplicate
        assert dedup.is_duplicate(record, "test_collection")

    @patch('redis.from_url')
    def test_deduplication_redis(self, mock_redis_from_url):
        """Test deduplication with Redis."""
        mock_redis = Mock()
        mock_redis.exists.return_value = False
        mock_redis_from_url.return_value = mock_redis

        dedup = DeduplicationManager("redis://localhost:6379")

        record = {"id": "test123", "data": "test"}

        # Check if duplicate
        is_dup = dedup.is_duplicate(record, "test_collection")
        assert not is_dup

        # Mark as processed
        dedup.mark_processed(record, "test_collection")

        # Verify Redis calls
        mock_redis.exists.assert_called()
        mock_redis.set.assert_called()

    def test_record_hash_generation(self):
        """Test record hash generation."""
        dedup = DeduplicationManager()

        record1 = {"id": "test123", "data": "test"}
        record2 = {"id": "test123", "data": "test"}
        record3 = {"id": "test456", "data": "test"}

        hash1 = dedup.get_record_hash(record1)
        hash2 = dedup.get_record_hash(record2)
        hash3 = dedup.get_record_hash(record3)

        assert hash1 == hash2  # Same record should have same hash
        assert hash1 != hash3  # Different records should have different hashes


class TestGPUDataProcessor:
    """Test GPU data processing."""

    @patch('mcp_server.utils.enhanced_ingestion.CUDF_AVAILABLE', False)
    def test_gpu_processor_no_cudf(self):
        """Test GPU processor when CuDF is not available."""
        processor = GPUDataProcessor()

        assert not processor.gpu_available

        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = processor.process_dataframe(df)

        assert result is df  # Should return original dataframe

    @patch('mcp_server.utils.enhanced_ingestion.CUDF_AVAILABLE', True)
    @patch('cudf.DataFrame.from_pandas')
    def test_gpu_processor_with_cudf(self, mock_from_pandas):
        """Test GPU processor when CuDF is available."""
        mock_cudf_df = Mock()
        mock_cudf_df.to_pandas.return_value = pd.DataFrame({"processed": [True]})
        mock_from_pandas.return_value = mock_cudf_df

        processor = GPUDataProcessor()

        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = processor.process_dataframe(df)

        assert isinstance(result, pd.DataFrame)
        mock_from_pandas.assert_called_once_with(df)


class TestParallelProcessor:
    """Test parallel processing functionality."""

    def test_parallel_processor_init(self):
        """Test parallel processor initialization."""
        processor = ParallelProcessor(max_workers=4)

        assert processor.max_workers == 4
        assert processor.executor is not None

    @pytest.mark.asyncio
    async def test_process_batch_async(self):
        """Test asynchronous batch processing."""
        processor = ParallelProcessor(max_workers=2)

        def test_func(x):
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = await processor.process_batch_async(items, test_func, batch_size=2)

        assert len(results) == 5
        assert results == [2, 4, 6, 8, 10]

    def test_process_batch_sync(self):
        """Test synchronous batch processing."""
        processor = ParallelProcessor(max_workers=2)

        def test_func(x):
            return x * 3

        items = [1, 2, 3, 4]
        results = processor.process_batch_sync(items, test_func, batch_size=2)

        assert len(results) == 4
        assert results == [3, 6, 9, 12]


class TestAsyncDataLoader:
    """Test asynchronous data loading."""

    def test_async_data_loader_init(self):
        """Test async data loader initialization."""
        config = IngestionConfig(use_gpu=True, use_parallel=True)
        loader = AsyncDataLoader(config)

        assert loader.config == config
        assert loader.gpu_processor is not None
        assert loader.parallel_processor is not None

    def test_async_data_loader_no_gpu(self):
        """Test async data loader without GPU."""
        config = IngestionConfig(use_gpu=False, use_parallel=False)
        loader = AsyncDataLoader(config)

        assert loader.gpu_processor is None
        assert loader.parallel_processor is None

    @pytest.mark.asyncio
    async def test_load_and_process_data(self):
        """Test data loading and processing."""
        config = IngestionConfig()
        loader = AsyncDataLoader(config)

        def dummy_processor(data):
            return {"processed": True}

        result = await loader.load_and_process_data("test_source", dummy_processor)

        assert isinstance(result, list)


class TestIngestionScheduler:
    """Test ingestion scheduler."""

    @patch('mcp_server.utils.enhanced_ingestion.APSCHEDULER_AVAILABLE', True)
    def test_scheduler_init(self):
        """Test scheduler initialization."""
        scheduler = IngestionScheduler()

        assert scheduler.scheduler is not None

    @patch('mcp_server.utils.enhanced_ingestion.APSCHEDULER_AVAILABLE', False)
    def test_scheduler_no_apscheduler(self):
        """Test scheduler when APScheduler is not available."""
        with pytest.raises(ImportError):
            IngestionScheduler()

    @patch('mcp_server.utils.enhanced_ingestion.APSCHEDULER_AVAILABLE', True)
    def test_add_cron_job(self):
        """Test adding cron job."""
        scheduler = IngestionScheduler()

        def dummy_func():
            pass

        scheduler.add_cron_job(dummy_func, "0 2 * * *", "test_job")

        # Verify job was added (this is a basic check)
        assert scheduler.scheduler is not None


class TestRemoteExecutor:
    """Test remote execution functionality."""

    @patch('mcp_server.utils.enhanced_ingestion.PARAMIKO_AVAILABLE', True)
    @patch('mcp_server.utils.enhanced_ingestion.FABRIC_AVAILABLE', True)
    def test_remote_executor_init(self):
        """Test remote executor initialization."""
        ssh_config = {
            "host": "testhost",
            "user": "testuser",
            "key_file": "/path/to/key"
        }

        executor = RemoteExecutor(ssh_config)

        assert executor.ssh_config == ssh_config
        assert executor.connection is None

    @patch('mcp_server.utils.enhanced_ingestion.PARAMIKO_AVAILABLE', False)
    def test_remote_executor_no_paramiko(self):
        """Test remote executor when Paramiko is not available."""
        with pytest.raises(ImportError):
            RemoteExecutor({})

    @patch('mcp_server.utils.enhanced_ingestion.PARAMIKO_AVAILABLE', True)
    @patch('mcp_server.utils.enhanced_ingestion.FABRIC_AVAILABLE', True)
    @patch('fabric.Connection')
    def test_connect(self, mock_connection_class):
        """Test SSH connection establishment."""
        mock_connection = Mock()
        mock_connection.run.return_value = Mock()
        mock_connection_class.return_value = mock_connection

        ssh_config = {
            "host": "testhost",
            "user": "testuser"
        }

        executor = RemoteExecutor(ssh_config)
        executor.connect()

        assert executor.connection == mock_connection
        mock_connection.run.assert_called_once_with("echo 'Connection test'", hide=True)


class TestEnhancedIngestionManager:
    """Test enhanced ingestion manager."""

    def test_manager_init(self):
        """Test manager initialization."""
        config = IngestionConfig()
        manager = EnhancedIngestionManager(config)

        assert manager.config == config
        assert manager.progress_tracker is not None
        assert manager.deduplication_manager is not None
        assert manager.async_loader is not None
        assert len(manager.jobs) == 0

    def test_manager_init_no_deduplication(self):
        """Test manager initialization without deduplication."""
        config = IngestionConfig(enable_deduplication=False)
        manager = EnhancedIngestionManager(config)

        assert manager.deduplication_manager is None

    def test_create_job(self):
        """Test job creation."""
        config = IngestionConfig()
        manager = EnhancedIngestionManager(config)

        job_id = manager.create_job("congress", "bills", {"congress": 118})

        assert job_id in manager.jobs
        job = manager.jobs[job_id]
        assert job.source == "congress"
        assert job.collection == "bills"
        assert job.parameters == {"congress": 118}
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_execute_job_async_congress(self):
        """Test executing Congress job."""
        config = IngestionConfig()
        manager = EnhancedIngestionManager(config)

        job_id = manager.create_job("congress", "bills", {"congress": 118})

        result = await manager.execute_job_async(job_id)

        assert result["status"] == "completed"
        assert result["records_processed"] == 0
        assert manager.jobs[job_id].status == "completed"

    @pytest.mark.asyncio
    async def test_execute_job_async_unknown_source(self):
        """Test executing job with unknown source."""
        config = IngestionConfig()
        manager = EnhancedIngestionManager(config)

        job_id = manager.create_job("unknown", "data", {})

        with pytest.raises(ValueError, match="Unknown source"):
            await manager.execute_job_async(job_id)

    @pytest.mark.asyncio
    async def test_execute_job_async_not_found(self):
        """Test executing non-existent job."""
        config = IngestionConfig()
        manager = EnhancedIngestionManager(config)

        with pytest.raises(ValueError, match="Job .* not found"):
            await manager.execute_job_async("nonexistent_job")

    def test_schedule_job_no_scheduler(self):
        """Test scheduling job when scheduler is not enabled."""
        config = IngestionConfig(scheduler_enabled=False)
        manager = EnhancedIngestionManager(config)

        job_id = manager.create_job("congress", "bills", {})

        with pytest.raises(RuntimeError, match="Scheduler not enabled"):
            manager.schedule_job(job_id, "0 2 * * *")


class TestGlobalFunctions:
    """Test global utility functions."""

    @patch('mcp_server.utils.enhanced_ingestion.ingestion_manager', None)
    def test_get_ingestion_manager_new(self):
        """Test getting new ingestion manager."""
        config = IngestionConfig()
        manager = get_ingestion_manager(config)

        assert isinstance(manager, EnhancedIngestionManager)
        assert manager.config == config

    @patch('mcp_server.utils.enhanced_ingestion.ingestion_manager', Mock())
    def test_get_ingestion_manager_cached(self):
        """Test getting cached ingestion manager."""
        mock_manager = Mock()
        import mcp_server.utils.enhanced_ingestion
        mcp_server.utils.enhanced_ingestion.ingestion_manager = mock_manager

        manager = get_ingestion_manager()

        assert manager == mock_manager
