"""Test script for enhanced ingestion system."""
import asyncio
import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the mcp_server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.utils.enhanced_ingestion import (
    IngestionConfig,
    EnhancedIngestionManager,
    GPUDataProcessor,
    DeduplicationManager
)
from mcp_server.utils.scheduler import IngestionScheduler, ScheduledJob
from mcp_server.utils.remote_execution import RemoteHost, RemoteExecutor

async def test_basic_ingestion():
    """Test basic ingestion functionality."""
    print("Testing basic ingestion functionality...")

    config = IngestionConfig(
        use_gpu=False,  # Disable GPU for testing
        use_parallel=False,
        enable_deduplication=False
    )

    manager = EnhancedIngestionManager(config)

    # Create a test job
    job_id = manager.create_job("congress", "test_collection", {"test": True})
    print(f"Created job: {job_id}")

    # Mock the execution methods
    with patch.object(manager, '_execute_congress_ingestion') as mock_execute:
        mock_execute.return_value = {"status": "completed", "records_processed": 100}

        result = await manager.execute_job_async(job_id)
        print(f"Job result: {result}")

        assert result["status"] == "completed"
        assert result["records_processed"] == 100

    print("✓ Basic ingestion test passed")

async def test_gpu_processor():
    """Test GPU processor functionality."""
    print("Testing GPU processor...")

    try:
        processor = GPUDataProcessor()

        # Test with CPU fallback
        import pandas as pd
        test_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        result_df = processor.process_dataframe(test_df)
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 3

        print("✓ GPU processor test passed")
    except ImportError as e:
        print(f"⚠ GPU processor test skipped: {e}")

async def test_deduplication():
    """Test deduplication functionality."""
    print("Testing deduplication...")

    dedup = DeduplicationManager()

    test_record = {"id": "test123", "data": "test"}

    # First time should not be duplicate
    is_dup = dedup.is_duplicate(test_record, "test_collection")
    assert not is_dup

    # Mark as processed
    dedup.mark_processed(test_record, "test_collection")

    # Second time should be duplicate
    is_dup = dedup.is_duplicate(test_record, "test_collection")
    assert is_dup

    print("✓ Deduplication test passed")

async def test_scheduler():
    """Test scheduler functionality."""
    print("Testing scheduler...")

    try:
        scheduler = IngestionScheduler(use_redis=False)

        # Create a test job
        job = ScheduledJob(
            job_id="test_job",
            name="Test Job",
            source="congress",
            collection="test",
            schedule_type="interval",
            schedule_config={"seconds": 60},
            parameters={}
        )
        # Mock the execution function
        async def mock_execute():
            return {"status": "completed"}

        job_id = scheduler.add_scheduled_job(job)
        assert job_id == "test_job"

        # Get jobs
        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_id == "test_job"

        # Remove job
        scheduler.remove_scheduled_job(job_id)
        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) == 0

        print("✓ Scheduler test passed")
    except ImportError as e:
        print(f"⚠ Scheduler test skipped: {e}")

def test_remote_execution():
    """Test remote execution setup (without actual connections)."""
    print("Testing remote execution setup...")

    try:
        # Test host configuration
        host = RemoteHost(
            host="test-host.com",
            user="testuser",
            port=22,
            remote_path="/tmp/test"
        )

        assert host.host == "test-host.com"
        assert host.user == "testuser"
        assert host.port == 22

        # Test executor initialization
        hosts = [host]
        executor = RemoteExecutor(hosts)

        assert len(executor.hosts) == 1
        assert executor.connections == {}

        print("✓ Remote execution setup test passed")
    except ImportError as e:
        print(f"⚠ Remote execution test skipped: {e}")

async def test_progress_tracking():
    """Test progress tracking."""
    print("Testing progress tracking...")

    from mcp_server.utils.enhanced_ingestion import ProgressTracker

    tracker = ProgressTracker()

    # Update progress
    tracker.update_progress("test_job", 50.0, 500, 1000)

    # Get progress (should return the stored data)
    progress = tracker.get_progress("test_job")
    assert 'progress' in progress
    assert progress['progress'] == 50.0
    assert progress['processed'] == 500
    assert progress['total'] == 1000

    print("✓ Progress tracking test passed")

async def run_all_tests():
    """Run all tests."""
    print("Running enhanced ingestion system tests...\n")

    try:
        await test_basic_ingestion()
        await test_gpu_processor()
        await test_deduplication()
        await test_scheduler()
        test_remote_execution()
        await test_progress_tracking()

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)