"""Enhanced ingestion framework with GPU, parallel, and async capabilities."""
import asyncio
import concurrent.futures
import multiprocessing
import os
import hashlib
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import pandas as pd

# Optional imports with fallbacks
try:
    from tqdm.asyncio import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import fabric
    from fabric import Connection
    FABRIC_AVAILABLE = True
except ImportError:
    FABRIC_AVAILABLE = False

try:
    import cudf
    CUDF_AVAILABLE = True
except ImportError:
    CUDF_AVAILABLE = False

try:
    import dask
    import dask.dataframe as dd
    from dask.distributed import Client, LocalCluster
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import aiomultiprocess
    AIOMULTIPROCESS_AVAILABLE = True
except ImportError:
    AIOMULTIPROCESS_AVAILABLE = False

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    CONCURRENT_LOG_HANDLER_AVAILABLE = True
except ImportError:
    CONCURRENT_LOG_HANDLER_AVAILABLE = False
    ConcurrentRotatingFileHandler = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IngestionJob:
    """Represents an ingestion job with metadata."""
    job_id: str
    source: str
    collection: str
    parameters: Dict[str, Any]
    status: str = "pending"
    progress: float = 0.0
    total_records: int = 0
    processed_records: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class IngestionConfig:
    """Configuration for enhanced ingestion."""
    use_gpu: bool = False
    use_parallel: bool = True
    use_async: bool = True
    max_workers: int = None
    batch_size: int = 1000
    chunk_size: int = 10000
    enable_progress_tracking: bool = True
    enable_deduplication: bool = True
    enable_compression: bool = True
    redis_url: Optional[str] = None
    scheduler_enabled: bool = False
    remote_execution: bool = False
    ssh_config: Optional[Dict[str, Any]] = None

class ProgressTracker:
    """Tracks ingestion progress with Redis backend."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url else None
        self.local_progress = {}

    def update_progress(self, job_id: str, progress: float, processed: int, total: int):
        """Update progress for a job."""
        data = {
            'progress': progress,
            'processed': processed,
            'total': total,
            'updated_at': datetime.now().isoformat()
        }

        if self.redis_client:
            self.redis_client.hset(f"ingestion:{job_id}", mapping=data)
        else:
            self.local_progress[job_id] = data

    def get_progress(self, job_id: str) -> Dict[str, Any]:
        """Get progress for a job."""
        if self.redis_client:
            return self.redis_client.hgetall(f"ingestion:{job_id}")
        return self.local_progress.get(job_id, {})

class DeduplicationManager:
    """Manages deduplication using hash-based approach."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url else None
        self.local_hashes = set()

    def get_record_hash(self, record: Dict[str, Any]) -> str:
        """Generate hash for a record."""
        # Create a normalized version for hashing
        normalized = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def is_duplicate(self, record: Dict[str, Any], collection: str) -> bool:
        """Check if record is a duplicate."""
        record_hash = self.get_record_hash(record)

        if self.redis_client:
            key = f"dedup:{collection}:{record_hash}"
            return bool(self.redis_client.exists(key))
        else:
            return record_hash in self.local_hashes

    def mark_processed(self, record: Dict[str, Any], collection: str):
        """Mark record as processed."""
        record_hash = self.get_record_hash(record)

        if self.redis_client:
            key = f"dedup:{collection}:{record_hash}"
            self.redis_client.set(key, "1", ex=86400*30)  # Expire after 30 days
        else:
            self.local_hashes.add(record_hash)

class GPUDataProcessor:
    """GPU-accelerated data processing using CuDF."""

    def __init__(self):
        self.gpu_available = self._check_gpu_availability()

    def _check_gpu_availability(self) -> bool:
        """Check if GPU is available."""
        return CUDF_AVAILABLE

    def process_dataframe(self, df: pd.DataFrame) -> Union[pd.DataFrame, Any]:
        """Process dataframe with GPU acceleration if available."""
        if not self.gpu_available:
            return df

        try:
            import cudf
            # Convert to CuDF for GPU processing
            cudf_df = cudf.DataFrame.from_pandas(df)

            # Perform GPU-accelerated operations here
            # For example: filtering, sorting, aggregations
            if 'date' in cudf_df.columns:
                cudf_df['date'] = cudf.to_datetime(cudf_df['date'])

            return cudf_df.to_pandas()
        except Exception as e:
            logger.warning(f"GPU processing failed, falling back to CPU: {e}")
            return df

class ParallelProcessor:
    """Parallel processing manager."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(32, multiprocessing.cpu_count() * 2)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

    async def process_batch_async(self, items: List[Any], processor_func: Callable,
                                batch_size: int = 100) -> List[Any]:
        """Process items in parallel batches asynchronously."""
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = []

            for item in batch:
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor, processor_func, item
                )
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        return results

    def process_batch_sync(self, items: List[Any], processor_func: Callable,
                          batch_size: int = 100) -> List[Any]:
        """Process items in parallel batches synchronously."""
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_results = list(executor.map(processor_func, batch))
                results.extend(batch_results)

        return results

class AsyncDataLoader:
    """Asynchronous data loading and processing."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.gpu_processor = GPUDataProcessor() if config.use_gpu else None
        self.parallel_processor = ParallelProcessor(config.max_workers) if config.use_parallel else None

    async def load_and_process_data(self, data_source: str, processor_func: Callable,
                                  **kwargs) -> List[Dict[str, Any]]:
        """Load and process data asynchronously."""
        # This would be implemented for each specific data source
        # For now, return empty list as placeholder
        return []

class IngestionScheduler:
    """Scheduler for automated ingestion jobs."""

    def __init__(self):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler not available. Install with: pip install apscheduler")
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), "default")
        self.scheduler.add_executor(AsyncIOExecutor())

    def add_cron_job(self, func: Callable, cron_expression: str, job_id: str, **kwargs):
        """Add a cron-scheduled job."""
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, **kwargs)

    def add_interval_job(self, func: Callable, interval_seconds: int, job_id: str, **kwargs):
        """Add an interval-based job."""
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = IntervalTrigger(seconds=interval_seconds)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, **kwargs)

    async def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            self.scheduler.shutdown()

class RemoteExecutor:
    """SSH-based remote execution for database operations."""

    def __init__(self, ssh_config: Dict[str, Any]):
        if not PARAMIKO_AVAILABLE or not FABRIC_AVAILABLE:
            raise ImportError("Paramiko and Fabric required for remote execution. Install with: pip install paramiko fabric")
        self.ssh_config = ssh_config
        self.connection = None

    def connect(self):
        """Establish SSH connection."""
        try:
            from fabric import Config
            config = Config(
                overrides={
                    'connect_kwargs': {
                        'key_filename': self.ssh_config.get('key_file'),
                        'password': self.ssh_config.get('password')
                    }
                }
            )

            self.connection = Connection(
                host=f"{self.ssh_config['user']}@{self.ssh_config['host']}:{self.ssh_config.get('port', 22)}",
                config=config
            )

            # Test connection
            self.connection.run("echo 'Connection test'", hide=True)
        except Exception as e:
            logger.error(f"Failed to connect via SSH: {e}")
            raise

    def execute_db_command(self, command: str, database_url: str) -> str:
        """Execute database command on remote server."""
        if not self.connection:
            self.connect()

        # Set environment variable and execute command
        full_command = f"DATABASE_URL='{database_url}' {command}"
        result = self.connection.run(full_command, hide=True)

        return result.stdout

    async def execute_async_db_command(self, command: str, database_url: str) -> str:
        """Execute database command asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.execute_db_command, command, database_url
        )

    def close(self):
        """Close SSH connection."""
        if self.connection:
            self.connection.close()

class EnhancedIngestionManager:
    """Main manager for enhanced ingestion operations."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.progress_tracker = ProgressTracker(config.redis_url)
        self.deduplication_manager = DeduplicationManager(config.redis_url) if config.enable_deduplication else None
        self.async_loader = AsyncDataLoader(config)
        self.scheduler = IngestionScheduler() if config.scheduler_enabled else None
        self.remote_executor = RemoteExecutor(config.ssh_config) if config.remote_execution and config.ssh_config else None
        self.jobs: Dict[str, IngestionJob] = {}

    def create_job(self, source: str, collection: str, parameters: Dict[str, Any]) -> str:
        """Create a new ingestion job."""
        job_id = f"{source}_{collection}_{int(time.time())}"
        job = IngestionJob(
            job_id=job_id,
            source=source,
            collection=collection,
            parameters=parameters
        )
        self.jobs[job_id] = job
        return job_id

    async def execute_job_async(self, job_id: str) -> Dict[str, Any]:
        """Execute a job asynchronously."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]
        job.status = "running"
        job.start_time = datetime.now()

        try:
            # Execute based on source
            if job.source == "congress":
                result = await self._execute_congress_ingestion(job)
            elif job.source == "openstates":
                result = await self._execute_openstates_ingestion(job)
            elif job.source == "govinfo":
                result = await self._execute_govinfo_ingestion(job)
            else:
                raise ValueError(f"Unknown source: {job.source}")

            job.status = "completed"
            job.end_time = datetime.now()
            return result

        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))
            job.end_time = datetime.now()
            raise

    async def _execute_congress_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute Congress data ingestion."""
        # Implementation would go here
        # This is a placeholder for the actual implementation
        return {"status": "completed", "records_processed": 0}

    async def _execute_openstates_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute OpenStates data ingestion."""
        # Implementation would go here
        return {"status": "completed", "records_processed": 0}

    async def _execute_govinfo_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute GovInfo data ingestion."""
        # Implementation would go here
        return {"status": "completed", "records_processed": 0}

    def schedule_job(self, job_id: str, cron_expression: str):
        """Schedule a job using cron expression."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not enabled")

        async def scheduled_execution():
            await self.execute_job_async(job_id)

        self.scheduler.add_cron_job(
            scheduled_execution,
            cron_expression,
            f"scheduled_{job_id}"
        )

    async def execute_remote_ingestion(self, job_id: str, remote_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ingestion on remote server via SSH."""
        if not self.remote_executor:
            raise RuntimeError("Remote execution not configured")

        job = self.jobs[job_id]

        # Generate command for remote execution
        command = self._generate_remote_command(job, remote_config)

        # Execute on remote server
        result = await self.remote_executor.execute_async_db_command(
            command,
            remote_config['database_url']
        )

        return {"status": "completed", "remote_output": result}

    def _generate_remote_command(self, job: IngestionJob, remote_config: Dict[str, Any]) -> str:
        """Generate command for remote execution."""
        base_cmd = f"cd {remote_config.get('remote_path', '/app')} && python"

        if job.source == "congress":
            script = "mcp_server/scripts/congress_ingest.py"
            params = f"--congress {job.parameters.get('congress', '')}"
        elif job.source == "openstates":
            script = "mcp_server/scripts/openstates_ingest.py"
            params = f"--jurisdiction {job.parameters.get('jurisdiction', '')}"
        elif job.source == "govinfo":
            script = "mcp_server/scripts/govinfo_ingest.py"
            params = f"--collection {job.parameters.get('collection', '')}"
        else:
            raise ValueError(f"Unknown source: {job.source}")

        return f"{base_cmd} {script} {params}"

# Global instance for easy access
ingestion_manager = None

def get_ingestion_manager(config: Optional[IngestionConfig] = None) -> EnhancedIngestionManager:
    """Get or create the global ingestion manager."""
    global ingestion_manager
    if ingestion_manager is None:
        if config is None:
            config = IngestionConfig()
        ingestion_manager = EnhancedIngestionManager(config)
    return ingestion_manager